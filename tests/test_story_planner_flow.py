"""StoryPlanner 検証環境（大項目14）。

StoryPlanner のフローを CLI 操作の連鎖で検証する:
  fixture Story → schema 確認 → beads_story / beads_task / subtask 作成
  → story branch 作成 → planning summary コメント → Doing 状態遷移
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

FIXTURES = Path(__file__).parent / "fixtures"


# -----------------------------------------------------------------------
# 14-1: Shortcut Story フィクスチャが sc-story get で読めること
# -----------------------------------------------------------------------
def test_fixture_story_readable_via_sc_get(run_sc):
    """Shortcut Story フィクスチャが sc-story get で正しく取得できる。"""
    story = yaml.safe_load((FIXTURES / "shortcut_story.valid.yaml").read_text())
    rc, data = run_sc(["get", "sc-123"], story=story)
    assert rc == 0
    assert data["id"] == "sc-123"
    assert data["state"] == "Ready"
    assert len(data["acceptance_criteria"]) == 2


# -----------------------------------------------------------------------
# 14-2: planned_pr_tasks が schema validation を通ること
# -----------------------------------------------------------------------
def test_planned_pr_task_fixture_validates():
    """planned_pr_task fixture が schema validation を通る。"""
    from ai_workflow.cli.guards import require_valid

    planned = yaml.safe_load((FIXTURES / "planned_pr_task.valid.yaml").read_text())
    require_valid(planned, "planned_pr_task", ".ai-workflow/schemas")  # 例外なし


# -----------------------------------------------------------------------
# 14-3: planned_pr_tasks から beads_task / 初期 subtask が作成できること
# -----------------------------------------------------------------------
def test_story_planner_creates_story_and_task(beads, run_bdw):
    """StoryPlanner: story create → task create で beads_story と beads_task が作られる。"""
    rc, s_data = run_bdw(["story", "create", "--shortcut-story", "sc-123", "--title", "Add saved filters"])
    assert rc == 0
    assert s_data["beads_story_id"] == "bd-story-001"
    assert s_data["shortcut_story_id"] == "sc-123"

    rc, t_data = run_bdw([
        "task", "create",
        "--file", str(FIXTURES / "planned_pr_task.valid.yaml"),
        "--story", "bd-story-001",
    ])
    assert rc == 0
    assert t_data["task"]["id"] == "bd-task-001"
    assert t_data["task"]["shortcut_story_id"] == "sc-123"
    assert t_data["task"]["current_phase"] == "planning"


# -----------------------------------------------------------------------
# 14-4: 初期 subtask として implement / review が作成されること
# -----------------------------------------------------------------------
def test_story_planner_creates_initial_subtasks(beads, run_bdw):
    """StoryPlanner: task create で implement + review の初期 subtask が ready で作られる。"""
    run_bdw(["story", "create", "--shortcut-story", "sc-123", "--title", "S"])
    rc, data = run_bdw([
        "task", "create",
        "--file", str(FIXTURES / "planned_pr_task.valid.yaml"),
        "--story", "bd-story-001",
    ])
    assert rc == 0
    kinds = [s["kind"] for s in data["subtasks"]]
    assert "implement" in kinds
    assert "review" in kinds
    for st in data["subtasks"]:
        assert st["status"] == "ready"


# -----------------------------------------------------------------------
# 14-5: story branch が作成されること
# -----------------------------------------------------------------------
def test_story_planner_creates_story_branch(run_ghw):
    """StoryPlanner: ghw branch create-story で story/sc-123-... が作成される。"""
    rc, data = run_ghw([
        "branch", "create-story", "123",
        "--from", "main",
        "--slug", "saved-filters",
    ])
    assert rc == 0
    assert data["branch"] == "story/sc-123-saved-filters"
    assert data["from"] == "main"


# -----------------------------------------------------------------------
# 14-6: Shortcut に planning summary コメントが投稿されること
# -----------------------------------------------------------------------
def test_story_planner_posts_planning_comment(run_sc, tmp_path):
    """StoryPlanner: sc-story comment で planning summary が Shortcut に投稿される。"""
    story = yaml.safe_load((FIXTURES / "shortcut_story.valid.yaml").read_text())
    body = tmp_path / "summary.md"
    body.write_text(
        "## Planning Summary\n\n"
        "beads_story: bd-story-001\n"
        "tasks: 1 (API migration)\n"
        "story branch: story/sc-123-saved-filters\n"
    )
    rc, data = run_sc(["comment", "sc-123", "--file", str(body)], story=story)
    assert rc == 0
    assert data["commented"] is True

    rc, after = run_sc(["get", "sc-123"])
    assert any("Planning Summary" in c["body"] for c in after["comments"])


# -----------------------------------------------------------------------
# 14-7: Shortcut Story の State を Doing に変更できること（Done にはしない）
# -----------------------------------------------------------------------
def test_story_planner_sets_state_doing(run_sc):
    """StoryPlanner: sc-story set-state Doing で Story が Doing になる。Done にはならない。"""
    story = yaml.safe_load((FIXTURES / "shortcut_story.valid.yaml").read_text())
    rc, data = run_sc(["set-state", "sc-123", "Doing"], story=story)
    assert rc == 0
    assert data["state"] == "Doing"

    rc, after = run_sc(["get", "sc-123"])
    assert after["state"] == "Doing"


def test_story_planner_cannot_set_state_done(run_sc):
    """StoryPlanner: sc-story set-state Done は拒否される（不変ルール3）。"""
    story = yaml.safe_load((FIXTURES / "shortcut_story.valid.yaml").read_text())
    rc, _ = run_sc(["set-state", "sc-123", "Done"], story=story)
    assert rc == 1


# -----------------------------------------------------------------------
# 14-8: beads_task が schema validation を通ること
# -----------------------------------------------------------------------
def test_created_task_validates_against_schema(beads, run_bdw):
    """task create で生成された beads_task が schema validation を通る。"""
    from ai_workflow.cli.guards import require_valid

    run_bdw(["story", "create", "--shortcut-story", "sc-123", "--title", "S"])
    rc, data = run_bdw([
        "task", "create",
        "--file", str(FIXTURES / "planned_pr_task.valid.yaml"),
        "--story", "bd-story-001",
    ])
    assert rc == 0
    require_valid(data["task"], "beads_task", ".ai-workflow/schemas")  # 例外なし
