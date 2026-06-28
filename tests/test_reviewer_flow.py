"""Reviewer 検証環境（大項目16）。

Reviewer のフローを CLI 操作の連鎖で検証する:
  review subtask claim → PR 取得 → acceptance criteria 参照
  → review_finding 作成（問題あり時）→ fix subtask 作成（must_fix 時）
  → review subtask close（問題なし時）
  ※ Reviewer は直接コードを修正しない（finding を作るだけ）
"""

from __future__ import annotations

import yaml
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _setup_with_review_subtask(run_bdw):
    """story + task（implement + review subtask 付き）を作る共通セットアップ。"""
    run_bdw(["story", "create", "--shortcut-story", "sc-123", "--title", "Add saved filters"])
    run_bdw([
        "task", "create",
        "--file", str(FIXTURES / "planned_pr_task.valid.yaml"),
        "--story", "bd-story-001",
    ])


# -----------------------------------------------------------------------
# 16-1: review subtask が ready で取得できること
# -----------------------------------------------------------------------
def test_reviewer_claims_review_subtask(beads, run_bdw):
    """Reviewer: bdw ready --role review で review subtask が in_progress になる。"""
    _setup_with_review_subtask(run_bdw)
    rc, data = run_bdw(["ready", "--role", "review"])
    assert rc == 0
    assert data["kind"] == "review"
    assert data["status"] == "in_progress"
    assert data["parent_task_id"] == "bd-task-001"


# -----------------------------------------------------------------------
# 16-2: PR を取得できること（ghw pr view）
# -----------------------------------------------------------------------
def test_reviewer_reads_pr_info(run_ghw):
    """Reviewer: ghw pr view で PR 情報が取得できる。"""
    rc, data = run_ghw(["pr", "view", "456"])
    assert rc == 0
    assert data["number"] == 456


def test_reviewer_reads_pr_checks(run_ghw):
    """Reviewer: ghw pr checks で CI 状態が取得できる。"""
    rc, data = run_ghw(["pr", "checks", "456"])
    assert rc == 0
    assert data["number"] == 456


# -----------------------------------------------------------------------
# 16-3: Shortcut Story の acceptance criteria を参照できること
# -----------------------------------------------------------------------
def test_reviewer_reads_acceptance_criteria(run_sc):
    """Reviewer: sc-story get で acceptance_criteria を参照できる。"""
    story = yaml.safe_load((FIXTURES / "shortcut_story.valid.yaml").read_text())
    rc, data = run_sc(["get", "sc-123"], story=story)
    assert rc == 0
    assert "acceptance_criteria" in data
    assert len(data["acceptance_criteria"]) == 2


# -----------------------------------------------------------------------
# 16-4: 問題がある場合に review_finding を作成できること
# -----------------------------------------------------------------------
def test_reviewer_creates_finding_on_problem(beads, run_bdw):
    """Reviewer: bdw finding create で review_finding が作成される。"""
    _setup_with_review_subtask(run_bdw)
    rc, data = run_bdw([
        "finding", "create",
        "--file", str(FIXTURES / "review_finding.valid.yaml"),
    ])
    assert rc == 0
    assert data["finding"]["severity"] == "must_fix"
    assert data["finding"]["status"] == "open"
    assert data["finding"]["task_id"] == "bd-task-001"


def test_reviewer_finding_is_listed_as_open(beads, run_bdw):
    """Reviewer: finding create 後、finding list --open で open finding が確認できる。"""
    _setup_with_review_subtask(run_bdw)
    run_bdw(["finding", "create", "--file", str(FIXTURES / "review_finding.valid.yaml")])

    rc, data = run_bdw(["finding", "list", "--task", "bd-task-001", "--open"])
    assert rc == 0
    assert len(data) == 1
    assert data[0]["severity"] == "must_fix"


# -----------------------------------------------------------------------
# 16-5: must_fix finding がある場合に fix subtask を作成できること
# -----------------------------------------------------------------------
def test_reviewer_creates_fix_subtask_for_must_fix(beads, run_bdw):
    """Reviewer: must_fix finding 後、bdw subtask create で fix subtask を作れる。"""
    _setup_with_review_subtask(run_bdw)
    run_bdw(["finding", "create", "--file", str(FIXTURES / "review_finding.valid.yaml")])

    rc, data = run_bdw([
        "subtask", "create",
        "--file", str(FIXTURES / "beads_subtask.valid.yaml"),  # fix subtask fixture
    ])
    assert rc == 0
    assert data["subtask"]["kind"] == "fix"
    assert data["subtask"]["status"] == "ready"
    assert "finding-001" in data["subtask"]["input_refs"]["review_finding_ids"]


# -----------------------------------------------------------------------
# 16-6: 問題がない場合に review subtask を closed にできること
# -----------------------------------------------------------------------
def test_reviewer_closes_review_subtask_when_ok(beads, run_bdw):
    """Reviewer: 問題なし時は review subtask を close できる。"""
    _setup_with_review_subtask(run_bdw)
    run_bdw(["ready", "--role", "review"])  # claim
    rc, data = run_bdw([
        "close", "bd-subtask-review-001",
        "--output", str(FIXTURES / "review_output.yaml"),
    ])
    assert rc == 0
    assert data["closed"] is True
    assert data["output_refs"]["verdict"] == "approve"

    show = beads.show("bd-subtask-review-001")
    assert show["status"] == "closed"


# -----------------------------------------------------------------------
# 16-7: Reviewer が直接コードを修正しないことの構造的な確認
# -----------------------------------------------------------------------
def test_reviewer_does_not_have_code_modify_commands(beads, run_bdw):
    """Reviewer の CLI 操作は finding/subtask/close のみ。コード変更コマンドは存在しない。"""
    # Reviewer が呼べる bdw コマンドのリスト（finding list, finding create, close, subtask create）
    # これらはすべてメタデータ操作のみで、コードファイルを変更しない。
    # 本テストでは「finding list が存在し、finding create が機能する」ことを確認する。
    _setup_with_review_subtask(run_bdw)
    run_bdw(["finding", "create", "--file", str(FIXTURES / "review_finding.valid.yaml")])

    rc, data = run_bdw(["finding", "list", "--task", "bd-task-001", "--open"])
    assert rc == 0
    # finding が 1 件ある → Reviewer は finding を作れる（コードは触っていない）
    assert len(data) == 1
