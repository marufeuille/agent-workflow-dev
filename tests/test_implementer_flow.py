"""Implementer 検証環境（大項目15）。

Implementer のフローを CLI 操作の連鎖で検証する:
  ready implement subtask 取得 → parent task 読み取り
  → task branch 作成 → story branch 宛 PR 作成（main 直接 PR 禁止）
  → pr_number 記録 → implement subtask close → review subtask ready 化
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _setup_story_and_task(run_bdw):
    """story + task（initial_subtasks 付き）を作る共通セットアップ。"""
    run_bdw(["story", "create", "--shortcut-story", "sc-123", "--title", "Add saved filters"])
    run_bdw([
        "task", "create",
        "--file", str(FIXTURES / "planned_pr_task.valid.yaml"),
        "--story", "bd-story-001",
    ])


# -----------------------------------------------------------------------
# 15-1: parent beads_task の planned_pr_scope を読めること
# -----------------------------------------------------------------------
def test_implementer_reads_parent_task_scope(beads, run_bdw):
    """Implementer: parent beads_task から planned_pr_scope / expected_files を読める。"""
    _setup_story_and_task(run_bdw)
    task = beads.show("bd-task-001")
    md = task.get("metadata", {})
    assert md["planned_pr_scope"]  # scope が存在する
    assert md["expected_files"]    # expected_files が存在する
    assert md["acceptance_refs"]   # acceptance_refs が存在する


# -----------------------------------------------------------------------
# 15-2: ready な implement subtask を claim できること
# -----------------------------------------------------------------------
def test_implementer_claims_implement_subtask(beads, run_bdw):
    """Implementer: bdw ready --role implement で implement subtask が in_progress になる。"""
    _setup_story_and_task(run_bdw)
    rc, data = run_bdw(["ready", "--role", "implement"])
    assert rc == 0
    assert data["kind"] == "implement"
    assert data["status"] == "in_progress"
    assert data["parent_task_id"] == "bd-task-001"


# -----------------------------------------------------------------------
# 15-3: task branch が story branch から作成されること
# -----------------------------------------------------------------------
def test_implementer_creates_task_branch(run_ghw):
    """Implementer: ghw branch create-task で agent/sc-123-... branch が作成される。"""
    rc, data = run_ghw([
        "branch", "create-task", "123", "saved-filters-api",
        "--from", "story/sc-123-saved-filters",
    ])
    assert rc == 0
    assert data["branch"] == "agent/sc-123-saved-filters-api"
    assert data["from"] == "story/sc-123-saved-filters"


# -----------------------------------------------------------------------
# 15-4: story branch 宛てに PR が作成されること
# -----------------------------------------------------------------------
def test_implementer_creates_pr_for_story_branch(run_ghw, tmp_path):
    """Implementer: ghw pr create --base story/... で story branch 宛 PR が作成される。"""
    body = tmp_path / "body.md"
    body.write_text(
        "## PR\n\n"
        "Shortcut Story: sc-123\n"
        "beads_task: bd-task-001\n"
        "acceptance_refs: AC-1, AC-2\n"
        "scope: Migration and model layer for saved filters.\n"
    )
    rc, data = run_ghw([
        "pr", "create",
        "--base", "story/sc-123-saved-filters",
        "--head", "agent/sc-123-saved-filters-api",
        "--body", str(body),
    ])
    assert rc == 0
    assert data["base"] == "story/sc-123-saved-filters"
    assert data["head"] == "agent/sc-123-saved-filters-api"


# -----------------------------------------------------------------------
# 15-5: task PR の base が main だと拒否されること
# -----------------------------------------------------------------------
def test_implementer_pr_blocked_if_base_is_main(run_ghw, tmp_path):
    """Implementer: task PR の base==main は禁止（不変ルール2）。"""
    body = tmp_path / "body.md"
    body.write_text("PR body")
    rc, _ = run_ghw([
        "pr", "create",
        "--base", "main",
        "--head", "agent/sc-123-x",
        "--body", str(body),
    ])
    assert rc == 1


# -----------------------------------------------------------------------
# 15-6: beads_task に pr_number が記録されること
# -----------------------------------------------------------------------
def test_implementer_records_pr_number(beads, run_bdw):
    """Implementer: bdw task link-pr で pr_numbers が beads_task に記録される。"""
    _setup_story_and_task(run_bdw)
    rc, data = run_bdw(["task", "link-pr", "bd-task-001", "--pr", "456"])
    assert rc == 0
    assert 456 in data["pr_numbers"]

    task = beads.show("bd-task-001")
    assert 456 in task["metadata"]["pr_numbers"]


# -----------------------------------------------------------------------
# 15-7: implement subtask が closed になること
# -----------------------------------------------------------------------
def test_implementer_closes_implement_subtask(beads, run_bdw):
    """Implementer: bdw close で implement subtask が closed になる。"""
    _setup_story_and_task(run_bdw)
    run_bdw(["ready", "--role", "implement"])  # claim → in_progress
    rc, data = run_bdw([
        "close", "bd-subtask-implement-001",
        "--output", str(FIXTURES / "implement_output.yaml"),
    ])
    assert rc == 0
    assert data["closed"] is True
    assert data["output_refs"]["status"] == "implemented"

    show = beads.show("bd-subtask-implement-001")
    assert show["status"] == "closed"


# -----------------------------------------------------------------------
# 15-8: review subtask が ready になること
# -----------------------------------------------------------------------
def test_implementer_creates_review_subtask_ready(beads, run_bdw):
    """Implementer: implement close 後、review subtask が ready で存在する。"""
    _setup_story_and_task(run_bdw)
    run_bdw(["ready", "--role", "implement"])
    run_bdw(["close", "bd-subtask-implement-001", "--output", str(FIXTURES / "implement_output.yaml")])

    # 初期 subtask として review-001 が ready で作られている（task create 時点で）
    rc, data = run_bdw(["ready", "--role", "review", "--list"])
    assert rc == 0
    assert len(data) >= 1
    assert data[0]["kind"] == "review"
    assert data[0]["status"] == "ready"


def test_implementer_can_create_additional_review_subtask(beads, run_bdw):
    """Implementer: bdw subtask create で追加の review subtask を作れる。"""
    _setup_story_and_task(run_bdw)
    rc, data = run_bdw([
        "subtask", "create",
        "--file", str(FIXTURES / "beads_subtask_review.valid.yaml"),
    ])
    assert rc == 0
    assert data["subtask"]["kind"] == "review"
    assert data["subtask"]["status"] == "ready"
    assert data["subtask"]["id"] == "bd-subtask-review-002"
