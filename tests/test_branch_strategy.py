"""branch 戦略の検証（大項目19）。

Git branch の2層構造（story branch / task branch）と
PR の base 制約を CLI 操作で検証する:
  story branch が main から作成される
  task branch が story branch から作成される
  task PR の base は story branch（main 直接 PR 禁止）
  story branch に複数の task PR を集約できる
  final PR が story branch から main に向かう
  final PR の merge は人間のみ（merge コマンドは存在しない）
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


# -----------------------------------------------------------------------
# 19-1: story branch が main から作成されること
# -----------------------------------------------------------------------
def test_story_branch_created_from_main(run_ghw):
    """StoryPlanner: story/sc-123-saved-filters が main から作成される。"""
    rc, data = run_ghw([
        "branch", "create-story", "123",
        "--from", "main",
        "--slug", "saved-filters",
    ])
    assert rc == 0
    assert data["branch"] == "story/sc-123-saved-filters"
    assert data["from"] == "main"


def test_story_branch_naming_convention(run_ghw):
    """story branch の命名規則が story/sc-{id}-{slug} であること。"""
    rc, data = run_ghw([
        "branch", "create-story", "456",
        "--from", "main",
        "--slug", "user-auth",
    ])
    assert rc == 0
    assert data["branch"].startswith("story/sc-456-")
    assert "user-auth" in data["branch"]


# -----------------------------------------------------------------------
# 19-2: task branch が story branch から作成されること
# -----------------------------------------------------------------------
def test_task_branch_created_from_story_branch(run_ghw):
    """Implementer: agent/sc-123-... が story branch から作成される。"""
    rc, data = run_ghw([
        "branch", "create-task", "123", "saved-filters-api",
        "--from", "story/sc-123-saved-filters",
    ])
    assert rc == 0
    assert data["branch"] == "agent/sc-123-saved-filters-api"
    assert data["from"] == "story/sc-123-saved-filters"


def test_task_branch_naming_convention(run_ghw):
    """task branch の命名規則が agent/sc-{id}-{slug} であること。"""
    rc, data = run_ghw([
        "branch", "create-task", "123", "my-feature",
        "--from", "story/sc-123-x",
    ])
    assert rc == 0
    assert data["branch"].startswith("agent/sc-123-")
    assert "my-feature" in data["branch"]


# -----------------------------------------------------------------------
# 19-3: task PR の base が story branch になること
# -----------------------------------------------------------------------
def test_task_pr_base_is_story_branch(run_ghw, tmp_path):
    """Implementer: task PR の base が story branch になる。"""
    body = tmp_path / "body.md"
    body.write_text("PR body")
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
# 19-4: task PR が main に直接向かないこと
# -----------------------------------------------------------------------
def test_task_pr_base_main_is_blocked(run_ghw, tmp_path):
    """不変ルール2: task PR の base==main は拒否される。"""
    body = tmp_path / "body.md"
    body.write_text("PR body")
    rc, _ = run_ghw([
        "pr", "create",
        "--base", "main",
        "--head", "agent/sc-123-saved-filters-api",
        "--body", str(body),
    ])
    assert rc == 1


# -----------------------------------------------------------------------
# 19-5: story branch に複数の task PR を集約できること
# -----------------------------------------------------------------------
def test_multiple_task_prs_target_same_story_branch(run_ghw, tmp_path):
    """story branch に複数の task PR を向けられる（複数 task の集約）。"""
    body1 = tmp_path / "body1.md"
    body1.write_text("Task 1: API layer")
    body2 = tmp_path / "body2.md"
    body2.write_text("Task 2: UI layer")

    rc1, data1 = run_ghw([
        "pr", "create",
        "--base", "story/sc-123-saved-filters",
        "--head", "agent/sc-123-saved-filters-api",
        "--body", str(body1),
    ])
    rc2, data2 = run_ghw([
        "pr", "create",
        "--base", "story/sc-123-saved-filters",
        "--head", "agent/sc-123-saved-filters-ui",
        "--body", str(body2),
    ])

    assert rc1 == 0
    assert rc2 == 0
    assert data1["base"] == "story/sc-123-saved-filters"
    assert data2["base"] == "story/sc-123-saved-filters"
    assert data1["head"] != data2["head"]  # 異なる task branch


# -----------------------------------------------------------------------
# 19-6: final PR が story branch から main に向かうこと
# -----------------------------------------------------------------------
def test_final_pr_base_is_main(run_ghw):
    """StoryReviewer: final PR の base は main（story branch → main）。"""
    rc, data = run_ghw([
        "pr", "create-final",
        "--story-branch", "story/sc-123-saved-filters",
        "--base", "main",
    ])
    assert rc == 0
    assert data["base"] == "main"
    assert data["head"] == "story/sc-123-saved-filters"


# -----------------------------------------------------------------------
# 19-7: final PR の merge は人間のみであること
# -----------------------------------------------------------------------
def test_final_pr_merge_is_human_only(run_ghw):
    """不変ルール1: final PR の merge は人間のみ（merge コマンドは実装しない）。"""
    rc, data = run_ghw([
        "pr", "create-final",
        "--story-branch", "story/sc-123-saved-filters",
        "--base", "main",
    ])
    assert rc == 0
    assert data["merge"] == "human-only"


def test_ai_merge_is_not_implemented():
    """不変ルール1: block_ai_merge() は常に GuardError を raise する。"""
    from ai_workflow.cli.guards import GuardError, block_ai_merge
    with pytest.raises(GuardError):
        block_ai_merge()


# -----------------------------------------------------------------------
# 19-8: StoryReviewer が story branch の状態を確認できること
# -----------------------------------------------------------------------
def test_story_reviewer_can_view_pr_for_story_branch(run_ghw):
    """StoryReviewer: ghw pr view で PR 情報（base が story branch かどうかなど）を確認できる。"""
    rc, data = run_ghw(["pr", "view", "456"])
    assert rc == 0
    assert data["number"] == 456
