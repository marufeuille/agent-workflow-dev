"""StoryReviewer 検証環境（大項目18）。

StoryReviewer のフローを CLI 操作の連鎖で検証する:
  beads_story 配下の task/subtask/finding 集約
  → open must_fix finding があれば In Review をブロック（ガード）
  → 必要な PR が未 merge なら In Review をブロック（ガード）
  → 条件が揃えば Shortcut Story を In Review に遷移
  → Done にはしない（不変ルール3）
  → story_review_summary schema validation
"""

from __future__ import annotations

import yaml
from pathlib import Path

import pytest

from ai_workflow.cli.guards import GuardError, block_story_review_if_not_ready

FIXTURES = Path(__file__).parent / "fixtures"


def _setup_full_story(run_bdw):
    """story + task + finding + fix subtask を全て用意する。"""
    run_bdw(["story", "create", "--shortcut-story", "sc-123", "--title", "Add saved filters"])
    run_bdw([
        "task", "create",
        "--file", str(FIXTURES / "planned_pr_task.valid.yaml"),
        "--story", "bd-story-001",
    ])
    run_bdw(["task", "link-pr", "bd-task-001", "--pr", "456"])


# -----------------------------------------------------------------------
# 18-1: beads_task / beads_subtask / review_finding を集約できること
# -----------------------------------------------------------------------
def test_story_reviewer_aggregates_tasks_and_subtasks(beads, run_bdw):
    """StoryReviewer: beads_task と beads_subtask をリストで集約できる。"""
    _setup_full_story(run_bdw)

    # task が存在し pr_numbers が記録されていること
    task = beads.show("bd-task-001")
    assert task is not None
    assert 456 in task["metadata"]["pr_numbers"]

    # subtask が ready で存在すること
    rc, subtasks = run_bdw(["ready", "--role", "implement", "--list"])
    assert rc == 0
    assert len(subtasks) == 1


def test_story_reviewer_aggregates_open_findings(beads, run_bdw):
    """StoryReviewer: finding list --open で open finding を集約できる。"""
    _setup_full_story(run_bdw)
    run_bdw(["finding", "create", "--file", str(FIXTURES / "review_finding.valid.yaml")])

    rc, data = run_bdw(["finding", "list", "--task", "bd-task-001", "--open"])
    assert rc == 0
    assert len(data) == 1
    assert data[0]["severity"] == "must_fix"


# -----------------------------------------------------------------------
# 18-2: open must_fix finding がある場合は In Review にしないこと
# -----------------------------------------------------------------------
def test_story_reviewer_blocks_in_review_on_open_must_fix():
    """StoryReviewer: open must_fix finding がある場合は In Review ガードが発動する。"""
    with pytest.raises(GuardError, match="must_fix"):
        block_story_review_if_not_ready(open_must_fix_count=2, unmerged_pr_count=0)


def test_story_reviewer_blocks_in_review_on_single_must_fix():
    """StoryReviewer: must_fix 1 件でも In Review ガードが発動する。"""
    with pytest.raises(GuardError):
        block_story_review_if_not_ready(open_must_fix_count=1, unmerged_pr_count=0)


# -----------------------------------------------------------------------
# 18-3: 必要な PR が未 merge の場合は In Review にしないこと
# -----------------------------------------------------------------------
def test_story_reviewer_blocks_in_review_on_unmerged_pr():
    """StoryReviewer: 未 merge の PR がある場合は In Review ガードが発動する。"""
    with pytest.raises(GuardError, match="未 merge"):
        block_story_review_if_not_ready(open_must_fix_count=0, unmerged_pr_count=1)


def test_story_reviewer_blocks_in_review_on_both_conditions():
    """StoryReviewer: must_fix + 未 merge が両方ある場合もガードが発動する（must_fix 優先）。"""
    with pytest.raises(GuardError, match="must_fix"):
        block_story_review_if_not_ready(open_must_fix_count=1, unmerged_pr_count=1)


# -----------------------------------------------------------------------
# 18-4: 条件が揃った場合に Shortcut Story を In Review にできること
# -----------------------------------------------------------------------
def test_story_reviewer_allows_in_review_when_ready():
    """StoryReviewer: open must_fix=0 かつ 未 merge=0 の場合はガードが通る。"""
    block_story_review_if_not_ready(open_must_fix_count=0, unmerged_pr_count=0)  # 例外なし


def test_story_reviewer_sets_in_review_state(run_sc):
    """StoryReviewer: 条件が揃えば sc-story set-state で In Review に遷移できる。"""
    story = yaml.safe_load((FIXTURES / "shortcut_story.valid.yaml").read_text())
    rc, data = run_sc(["set-state", "sc-123", "In Review"], story=story)
    assert rc == 0
    assert data["state"] == "In Review"


# -----------------------------------------------------------------------
# 18-5: StoryReviewer が Shortcut Story を Done にしないこと
# -----------------------------------------------------------------------
def test_story_reviewer_does_not_set_done_state(run_sc):
    """StoryReviewer: sc-story set-state Done は拒否される（不変ルール3）。"""
    story = yaml.safe_load((FIXTURES / "shortcut_story.valid.yaml").read_text())
    rc, _ = run_sc(["set-state", "sc-123", "Done"], story=story)
    assert rc == 1


# -----------------------------------------------------------------------
# 18-6: 人間向け summary コメントが Shortcut に投稿されること
# -----------------------------------------------------------------------
def test_story_reviewer_posts_summary_comment(run_sc, tmp_path):
    """StoryReviewer: sc-story comment で story_review_summary コメントが投稿される。"""
    story = yaml.safe_load((FIXTURES / "shortcut_story.valid.yaml").read_text())
    summary_body = tmp_path / "summary.md"
    summary_body.write_text(
        "## Story Review Summary\n\n"
        "beads_story: bd-story-001\n"
        "ready_for_review: true\n"
        "AC-1: ✅ satisfied\n"
        "AC-2: ✅ satisfied\n"
    )
    rc, data = run_sc(["comment", "sc-123", "--file", str(summary_body)], story=story)
    assert rc == 0
    assert data["commented"] is True

    rc, after = run_sc(["get", "sc-123"])
    assert any("Story Review Summary" in c["body"] for c in after["comments"])


# -----------------------------------------------------------------------
# 18-7: story_review_summary スキーマが valid fixture で通ること
# -----------------------------------------------------------------------
def test_story_review_summary_schema_validates():
    """StoryReviewer: story_review_summary fixture が schema validation を通る。"""
    from ai_workflow.cli.guards import require_valid

    summary = yaml.safe_load((FIXTURES / "story_review_summary.valid.yaml").read_text())
    require_valid(summary, "story_review_summary", ".ai-workflow/schemas")  # 例外なし


# -----------------------------------------------------------------------
# 18-8: PR の CI 状態を取得できること
# -----------------------------------------------------------------------
def test_story_reviewer_reads_pr_checks(run_ghw):
    """StoryReviewer: ghw pr checks で PR の CI 状態を取得できる。"""
    rc, data = run_ghw(["pr", "checks", "456"])
    assert rc == 0
    assert data["number"] == 456
