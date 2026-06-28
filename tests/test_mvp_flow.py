"""MVP 動作確認（フェーズF / 大項目21-23）。

fixture Story を使い、slash command 相当の全行程を wrapper CLI の連鎖で検証する。
外部 Shortcut / GitHub には接続せず、Shortcut は mock、GitHub は dry-run、beads は
tmp_path 配下の一時 DB を使う。
"""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_workflow.cli.guards import block_story_review_if_not_ready, require_valid

FIXTURES = Path(__file__).parent / "fixtures"


def _write_text(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _write_yaml(path: Path, data: dict) -> Path:
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    return path


def test_mvp_fixture_story_runs_end_to_end_without_done_or_main_merge(
    beads,
    run_bdw,
    run_ghw,
    run_sc,
    tmp_path: Path,
):
    """/story-plan から /story-review までの MVP 全行程が連鎖する。"""
    story = yaml.safe_load((FIXTURES / "shortcut_story.valid.yaml").read_text())

    # /story-plan: Story 取得、beads 階層作成、story branch 作成、summary 投稿、Doing 化。
    rc, fetched = run_sc(["get", "sc-123"], story=story)
    assert rc == 0
    assert fetched["state"] == "Ready"

    rc, beads_story = run_bdw([
        "story",
        "create",
        "--shortcut-story",
        "sc-123",
        "--title",
        fetched["name"],
    ])
    assert rc == 0
    assert beads_story["beads_story_id"] == "bd-story-001"

    rc, task_data = run_bdw([
        "task",
        "create",
        "--file",
        str(FIXTURES / "planned_pr_task.valid.yaml"),
        "--story",
        "bd-story-001",
    ])
    assert rc == 0
    assert task_data["task"]["id"] == "bd-task-001"
    assert {s["kind"] for s in task_data["subtasks"]} == {"implement", "review"}

    rc, linked = run_sc(["link", "sc-123", "--beads-story", "bd-story-001"])
    assert rc == 0
    assert linked["metadata"]["beads_story_id"] == "bd-story-001"

    rc, story_branch = run_ghw([
        "branch",
        "create-story",
        "123",
        "--from",
        "main",
        "--slug",
        "saved-filters",
    ])
    assert rc == 0
    assert story_branch["branch"] == "story/sc-123-saved-filters"

    planning_summary = _write_text(
        tmp_path / "planning-summary.md",
        "## Planning Summary\n\n"
        "beads_story: bd-story-001\n"
        "task: bd-task-001\n"
        "story branch: story/sc-123-saved-filters\n",
    )
    rc, commented = run_sc(["comment", "sc-123", "--file", str(planning_summary)])
    assert rc == 0
    assert commented["commented"] is True

    rc, doing = run_sc(["set-state", "sc-123", "Doing"])
    assert rc == 0
    assert doing["state"] == "Doing"

    # /work-next: implement subtask claim、task branch / PR 作成、pr_number 記録、close。
    rc, implement_subtask = run_bdw(["ready", "--role", "implement"])
    assert rc == 0
    assert implement_subtask["id"] == "bd-subtask-implement-001"
    assert implement_subtask["status"] == "in_progress"

    rc, task_branch = run_ghw([
        "branch",
        "create-task",
        "123",
        "saved-filters-api",
        "--from",
        "story/sc-123-saved-filters",
    ])
    assert rc == 0
    assert task_branch["branch"] == "agent/sc-123-saved-filters-api"

    pr_body = _write_text(
        tmp_path / "task-pr.md",
        "## PR\n\n"
        "Shortcut Story: sc-123\n"
        "beads_task: bd-task-001\n"
        "acceptance_refs: AC-1, AC-2\n"
        "scope: Migration and model layer for saved filters.\n",
    )
    rc, pr = run_ghw([
        "pr",
        "create",
        "--base",
        "story/sc-123-saved-filters",
        "--head",
        "agent/sc-123-saved-filters-api",
        "--body",
        str(pr_body),
        "--title",
        "Add saved filters persistence",
    ])
    assert rc == 0
    assert pr["base"] == "story/sc-123-saved-filters"
    assert pr["head"] == "agent/sc-123-saved-filters-api"

    rc, linked_pr = run_bdw(["task", "link-pr", "bd-task-001", "--pr", "456"])
    assert rc == 0
    assert linked_pr["pr_numbers"] == [456]

    rc, phase = run_bdw(["task", "set-phase", "bd-task-001", "implementation"])
    assert rc == 0
    assert phase["phase"] == "implementation"

    rc, closed_impl = run_bdw([
        "close",
        "bd-subtask-implement-001",
        "--output",
        str(FIXTURES / "implement_output.yaml"),
    ])
    assert rc == 0
    assert closed_impl["closed"] is True

    # /review-pr: review subtask claim、PR/CI 参照、finding と fix subtask 作成。
    rc, review_subtask = run_bdw(["ready", "--role", "review"])
    assert rc == 0
    assert review_subtask["id"] == "bd-subtask-review-001"

    rc, viewed_pr = run_ghw(["pr", "view", "456"])
    assert rc == 0
    assert viewed_pr["number"] == 456

    rc, checks = run_ghw(["pr", "checks", "456"])
    assert rc == 0
    assert checks["number"] == 456

    rc, finding = run_bdw([
        "finding",
        "create",
        "--file",
        str(FIXTURES / "review_finding.valid.yaml"),
    ])
    assert rc == 0
    assert finding["finding"]["id"] == "finding-001"

    rc, fix_subtask = run_bdw([
        "subtask",
        "create",
        "--file",
        str(FIXTURES / "beads_subtask.valid.yaml"),
    ])
    assert rc == 0
    assert fix_subtask["subtask"]["kind"] == "fix"

    review_changes = _write_yaml(
        tmp_path / "review-output.yaml",
        {
            "status": "reviewed",
            "verdict": "changes_requested",
            "finding_ids": ["finding-001"],
        },
    )
    rc, closed_review = run_bdw([
        "close",
        "bd-subtask-review-001",
        "--output",
        str(review_changes),
    ])
    assert rc == 0
    assert closed_review["closed"] is True

    rc, open_findings = run_bdw(["finding", "list", "--task", "bd-task-001", "--open"])
    assert rc == 0
    assert [f["id"] for f in open_findings] == ["finding-001"]

    # /fix-findings: finding 範囲の修正、fixed 化、fix close、再 review ready。
    rc, claimed_fix = run_bdw(["ready", "--role", "fix"])
    assert rc == 0
    assert claimed_fix["id"] == "bd-subtask-fix-001"

    rc, fixed = run_bdw(["finding", "update", "finding-001", "--status", "fixed"])
    assert rc == 0
    assert fixed["status"] == "fixed"

    rc, closed_fix = run_bdw([
        "close",
        "bd-subtask-fix-001",
        "--output",
        str(FIXTURES / "fixer_output.yaml"),
    ])
    assert rc == 0
    assert closed_fix["closed"] is True

    rc, rereview_subtask = run_bdw([
        "subtask",
        "create",
        "--file",
        str(FIXTURES / "beads_subtask_review2.valid.yaml"),
    ])
    assert rc == 0
    assert rereview_subtask["subtask"]["id"] == "bd-subtask-review-003"

    rc, claimed_rereview = run_bdw(["ready", "--role", "review"])
    assert rc == 0
    assert claimed_rereview["id"] == "bd-subtask-review-003"

    rc, closed_rereview = run_bdw([
        "close",
        "bd-subtask-review-003",
        "--output",
        str(FIXTURES / "review_output.yaml"),
    ])
    assert rc == 0
    assert closed_rereview["closed"] is True

    rc, phase = run_bdw(["task", "set-phase", "bd-task-001", "verified"])
    assert rc == 0
    assert phase["phase"] == "verified"

    rc, open_findings_after_fix = run_bdw([
        "finding",
        "list",
        "--task",
        "bd-task-001",
        "--open",
    ])
    assert rc == 0
    assert open_findings_after_fix == []

    # /story-review: summary を Shortcut へ戻し、In Review まで進める。Done にはしない。
    summary = yaml.safe_load((FIXTURES / "story_review_summary.valid.yaml").read_text())
    require_valid(summary, "story_review_summary", ".ai-workflow/schemas")
    block_story_review_if_not_ready(open_must_fix_count=0, unmerged_pr_count=0)

    story_summary = _write_text(
        tmp_path / "story-review-summary.md",
        "## Story Review Summary\n\n"
        "beads_story: bd-story-001\n"
        "ready_for_review: true\n"
        "AC-1: satisfied\n"
        "AC-2: satisfied\n",
    )
    rc, summary_comment = run_sc(["comment", "sc-123", "--file", str(story_summary)])
    assert rc == 0
    assert summary_comment["commented"] is True

    rc, in_review = run_sc(["set-state", "sc-123", "In Review"])
    assert rc == 0
    assert in_review["state"] == "In Review"

    final_pr_body = _write_text(
        tmp_path / "final-pr.md",
        "Final PR for story/sc-123-saved-filters.\n\nmerge は人間のみ。\n",
    )
    rc, final_pr = run_ghw([
        "pr",
        "create-final",
        "--story-branch",
        "story/sc-123-saved-filters",
        "--base",
        "main",
        "--body",
        str(final_pr_body),
    ])
    assert rc == 0
    assert final_pr["base"] == "main"
    assert final_pr["head"] == "story/sc-123-saved-filters"
    assert final_pr["merge"] == "human-only"

    # MVP の安全条件: Done 化と main 直接 task PR は拒否され、Story は In Review のまま。
    rc, _ = run_sc(["set-state", "sc-123", "Done"])
    assert rc == 1

    main_pr_body = _write_text(tmp_path / "main-pr.md", "Task PR to main must fail.\n")
    rc, _ = run_ghw([
        "pr",
        "create",
        "--base",
        "main",
        "--head",
        "agent/sc-123-saved-filters-api",
        "--body",
        str(main_pr_body),
    ])
    assert rc == 1

    rc, final_story = run_sc(["get", "sc-123"])
    assert rc == 0
    assert final_story["state"] == "In Review"
    assert any("Planning Summary" in c["body"] for c in final_story["comments"])
    assert any("Story Review Summary" in c["body"] for c in final_story["comments"])

    task = beads.show("bd-task-001")
    assert task["metadata"]["pr_numbers"] == [456]
    assert task["metadata"]["current_phase"] == "verified"

    fixed_finding = beads.show("finding-001")
    assert fixed_finding["status"] == "closed"
    assert fixed_finding["metadata"]["status"] == "fixed"
