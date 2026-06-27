"""bin/bdw のテスト（bd 実物で統合テスト + マッピング unit）。

各テストは独立した bd DB（beads fixture）を使う。
run_bdw は bdw.main(argv) を実行し (exit_code, parsed_json) を返す。
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _seed_task(run_bdw) -> None:
    """story + task（initial_subtasks 付き）を作る共通セットアップ。"""
    run_bdw(["story", "create", "--shortcut-story", "sc-1", "--title", "S"])
    run_bdw(
        [
            "task",
            "create",
            "--file",
            str(FIXTURES / "planned_pr_task.valid.yaml"),
            "--story",
            "bd-story-001",
        ]
    )


# ----------------------------------------------------------------------
# init / story / task
# ----------------------------------------------------------------------
def test_init_registers_custom_types(beads):
    types_info = beads.types()
    custom = set(types_info["custom_types"])
    assert {"beads_story", "beads_task", "beads_subtask", "review_finding"} <= custom


def test_story_create(beads, run_bdw):
    rc, data = run_bdw(["story", "create", "--shortcut-story", "sc-1", "--title", "Test"])
    assert rc == 0
    assert data == {"beads_story_id": "bd-story-001", "shortcut_story_id": "sc-1"}
    show = beads.show("bd-story-001")
    assert show["external_ref"] == "sc-1"
    assert show["issue_type"] == "beads_story"


def test_task_create_with_initial_subtasks(beads, run_bdw):
    run_bdw(["story", "create", "--shortcut-story", "sc-1", "--title", "S"])
    rc, data = run_bdw(
        [
            "task",
            "create",
            "--file",
            str(FIXTURES / "planned_pr_task.valid.yaml"),
            "--story",
            "bd-story-001",
        ]
    )
    assert rc == 0
    assert data["task"]["id"] == "bd-task-001"
    assert data["task"]["shortcut_story_id"] == "sc-1"
    assert data["task"]["current_phase"] == "planning"
    kinds = [s["kind"] for s in data["subtasks"]]
    assert kinds == ["implement", "review"]
    assert all(s["status"] == "ready" for s in data["subtasks"])
    # task に phase ラベルと parent が付いているか
    show = beads.show("bd-task-001")
    assert "phase:planning" in show["labels"]
    assert show["parent"] == "bd-story-001"


def test_task_create_no_initial_subtasks(beads, run_bdw):
    run_bdw(["story", "create", "--shortcut-story", "sc-1", "--title", "S"])
    rc, data = run_bdw(
        [
            "task",
            "create",
            "--file",
            str(FIXTURES / "planned_pr_task.valid.yaml"),
            "--story",
            "bd-story-001",
            "--no-initial-subtasks",
        ]
    )
    assert rc == 0
    assert data["subtasks"] == []


# ----------------------------------------------------------------------
# ready / close
# ----------------------------------------------------------------------
def test_ready_claims_one(beads, run_bdw):
    _seed_task(run_bdw)
    rc, data = run_bdw(["ready", "--role", "implement"])
    assert rc == 0
    assert data["kind"] == "implement"
    assert data["status"] == "in_progress"  # ready → in_progress に claim


def test_ready_list_non_destructive(beads, run_bdw):
    _seed_task(run_bdw)
    rc, data = run_bdw(["ready", "--role", "implement", "--list"])
    assert rc == 0
    assert len(data) == 1
    assert data[0]["status"] == "ready"  # claim されず ready のまま


def test_ready_empty(beads, run_bdw):
    rc, data = run_bdw(["ready", "--role", "fix"])
    assert rc == 0
    assert data == []


def test_close(beads, run_bdw):
    _seed_task(run_bdw)
    run_bdw(["ready", "--role", "implement"])  # claim → in_progress
    rc, data = run_bdw(
        ["close", "bd-subtask-implement-001", "--output", str(FIXTURES / "fixer_output.yaml")]
    )
    assert rc == 0
    assert data["closed"] is True
    assert data["output_refs"]["commit_shas"] == ["abc123"]
    show = beads.show("bd-subtask-implement-001")
    assert show["status"] == "closed"
    assert show["metadata"]["output_refs"]["commit_shas"] == ["abc123"]


# ----------------------------------------------------------------------
# finding
# ----------------------------------------------------------------------
def test_finding_create_and_list(beads, run_bdw):
    _seed_task(run_bdw)
    rc, data = run_bdw(["finding", "create", "--file", str(FIXTURES / "review_finding.valid.yaml")])
    assert rc == 0
    assert data["finding"]["id"] == "finding-001"
    rc, listed = run_bdw(["finding", "list", "--task", "bd-task-001", "--open"])
    assert rc == 0
    assert len(listed) == 1
    assert listed[0]["severity"] == "must_fix"
    assert listed[0]["status"] == "open"
    assert listed[0]["line"] == 82


def test_finding_update_fixed_removes_from_open(beads, run_bdw):
    _seed_task(run_bdw)
    run_bdw(["finding", "create", "--file", str(FIXTURES / "review_finding.valid.yaml")])
    rc, data = run_bdw(["finding", "update", "finding-001", "--status", "fixed"])
    assert rc == 0
    assert data["status"] == "fixed"
    show = beads.show("finding-001")
    assert show["status"] == "closed"
    assert show["metadata"]["status"] == "fixed"
    rc, listed = run_bdw(["finding", "list", "--task", "bd-task-001", "--open"])
    assert listed == []


# ----------------------------------------------------------------------
# task link-pr / set-phase
# ----------------------------------------------------------------------
def test_task_link_pr(beads, run_bdw):
    _seed_task(run_bdw)
    rc, data = run_bdw(["task", "link-pr", "bd-task-001", "--pr", "456"])
    assert rc == 0
    assert data["pr_numbers"] == [456]
    show = beads.show("bd-task-001")
    assert show["metadata"]["pr_numbers"] == [456]


def test_task_set_phase(beads, run_bdw):
    _seed_task(run_bdw)
    rc, data = run_bdw(["task", "set-phase", "bd-task-001", "verified"])
    assert rc == 0
    assert data["phase"] == "verified"
    show = beads.show("bd-task-001")
    assert "phase:verified" in show["labels"]
    assert show["metadata"]["current_phase"] == "verified"


# ----------------------------------------------------------------------
# guard
# ----------------------------------------------------------------------
def test_guard_invalid_finding_schema(beads, run_bdw):
    rc, data = run_bdw(["finding", "create", "--file", str(FIXTURES / "review_finding.invalid.yaml")])
    assert rc == 1  # task_id 欠落で拒否


def test_guard_invalid_task_schema(beads, run_bdw):
    # planned_pr_task に必須フィールドが無い YAML
    bad = FIXTURES / "planned_pr_task.valid.yaml"
    # 正常 fixture は通るので、ここは別の検証: 存在しない story を指定
    run_bdw(["story", "create", "--shortcut-story", "sc-1", "--title", "S"])
    rc, _ = run_bdw(
        [
            "task",
            "create",
            "--file",
            str(FIXTURES / "planned_pr_task.valid.yaml"),
            "--story",
            "bd-story-999",  # 存在しない
        ]
    )
    assert rc == 1


# ----------------------------------------------------------------------
# mapping unit
# ----------------------------------------------------------------------
def test_mapping_subtask_roundtrip():
    from ai_workflow.cli import bd_mapping as M

    st = {
        "id": "bd-subtask-fix-001",
        "kind": "fix",
        "status": "ready",
        "parent_task_id": "bd-task-001",
    }
    args = M.subtask_to_create_args(st)
    assert args["type"] == M.TYPE_SUBTASK
    assert "kind:fix" in args["labels"]
    assert args["metadata"]["status"] == "ready"

    show = {
        "id": "bd-subtask-fix-001",
        "status": "open",
        "parent": "bd-task-001",
        "labels": ["kind:fix", "subtask"],
        "metadata": {"kind": "fix", "status": "ready"},
    }
    back = M.bd_to_subtask(show)
    assert back["kind"] == "fix"
    assert back["status"] == "ready"
    assert back["parent_task_id"] == "bd-task-001"


def test_mapping_finding_fixed_roundtrip():
    from ai_workflow.cli import bd_mapping as M

    show = {
        "id": "finding-001",
        "status": "closed",
        "parent": "bd-task-001",
        "labels": ["severity:must_fix", "finding"],
        "metadata": {
            "severity": "must_fix",
            "category": "test",
            "file": "a.py",
            "description": "d",
            "status": "fixed",
        },
    }
    back = M.bd_to_finding(show)
    assert back["severity"] == "must_fix"
    assert back["status"] == "fixed"  # metadata.status を優先


def test_mapping_task_roundtrip():
    from ai_workflow.cli import bd_mapping as M

    show = {
        "id": "bd-task-001",
        "title": "T",
        "status": "open",
        "parent": "bd-story-001",
        "labels": ["phase:review", "task"],
        "metadata": {
            "shortcut_story_id": "sc-1",
            "planned_pr_scope": "scope",
            "acceptance_refs": ["AC-1"],
            "expected_files": ["a/*"],
            "pr_numbers": [10],
            "current_phase": "planning",
            "depends_on": [],
        },
    }
    back = M.bd_to_task(show)
    assert back["current_phase"] == "review"  # label phase: を優先
    assert back["pr_numbers"] == [10]
    assert back["shortcut_story_id"] == "sc-1"
