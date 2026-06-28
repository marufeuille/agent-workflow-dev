"""Fixer 検証環境（大項目17）。

Fixer のフローを CLI 操作の連鎖で検証する:
  open finding + fix subtask ready → fix subtask claim
  → finding を fixed に更新 → fix subtask close
  → 再 review subtask ready 化
  ※ finding の範囲外の大きな変更を行わない（finding を fixed にするだけ）
"""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _setup_with_finding_and_fix_subtask(run_bdw):
    """story + task + finding + fix subtask を用意する共通セットアップ。"""
    run_bdw(["story", "create", "--shortcut-story", "sc-123", "--title", "Add saved filters"])
    run_bdw([
        "task", "create",
        "--file", str(FIXTURES / "planned_pr_task.valid.yaml"),
        "--story", "bd-story-001",
    ])
    run_bdw(["finding", "create", "--file", str(FIXTURES / "review_finding.valid.yaml")])
    run_bdw(["subtask", "create", "--file", str(FIXTURES / "beads_subtask.valid.yaml")])


# -----------------------------------------------------------------------
# 17-1: fix subtask が ready で取得できること
# -----------------------------------------------------------------------
def test_fixer_claims_fix_subtask(beads, run_bdw):
    """Fixer: bdw ready --role fix で fix subtask が in_progress になる。"""
    _setup_with_finding_and_fix_subtask(run_bdw)
    rc, data = run_bdw(["ready", "--role", "fix"])
    assert rc == 0
    assert data["kind"] == "fix"
    assert data["status"] == "in_progress"
    assert data["input_refs"]["review_finding_ids"] == ["finding-001"]


# -----------------------------------------------------------------------
# 17-2: open finding を一覧できること
# -----------------------------------------------------------------------
def test_fixer_reads_open_findings(beads, run_bdw):
    """Fixer: bdw finding list --open で open finding を確認できる。"""
    _setup_with_finding_and_fix_subtask(run_bdw)
    rc, data = run_bdw(["finding", "list", "--task", "bd-task-001", "--open"])
    assert rc == 0
    assert len(data) == 1
    assert data[0]["severity"] == "must_fix"
    assert data[0]["status"] == "open"
    assert data[0]["file"] == "app/api/saved_filters.py"


# -----------------------------------------------------------------------
# 17-3: finding が fixed になること
# -----------------------------------------------------------------------
def test_fixer_marks_finding_fixed(beads, run_bdw):
    """Fixer: bdw finding update --status fixed で finding が fixed になる。"""
    _setup_with_finding_and_fix_subtask(run_bdw)
    rc, data = run_bdw(["finding", "update", "finding-001", "--status", "fixed"])
    assert rc == 0
    assert data["status"] == "fixed"

    show = beads.show("finding-001")
    assert show["metadata"]["status"] == "fixed"


def test_fixer_finding_removed_from_open_list_after_fix(beads, run_bdw):
    """Fixer: finding fixed 後、finding list --open から消える。"""
    _setup_with_finding_and_fix_subtask(run_bdw)
    run_bdw(["finding", "update", "finding-001", "--status", "fixed"])

    rc, data = run_bdw(["finding", "list", "--task", "bd-task-001", "--open"])
    assert rc == 0
    assert data == []


# -----------------------------------------------------------------------
# 17-4: fix subtask が closed になること
# -----------------------------------------------------------------------
def test_fixer_closes_fix_subtask(beads, run_bdw):
    """Fixer: bdw close fix-subtask で fix subtask が closed になる。"""
    _setup_with_finding_and_fix_subtask(run_bdw)
    run_bdw(["ready", "--role", "fix"])  # claim
    rc, data = run_bdw([
        "close", "bd-subtask-fix-001",
        "--output", str(FIXTURES / "fixer_output.yaml"),
    ])
    assert rc == 0
    assert data["closed"] is True

    show = beads.show("bd-subtask-fix-001")
    assert show["status"] == "closed"


# -----------------------------------------------------------------------
# 17-5: 再 review subtask が ready になること
# -----------------------------------------------------------------------
def test_fixer_creates_re_review_subtask_ready(beads, run_bdw):
    """Fixer: fix close 後、bdw subtask create で再 review subtask が ready で作れる。"""
    _setup_with_finding_and_fix_subtask(run_bdw)
    run_bdw(["ready", "--role", "fix"])
    run_bdw(["close", "bd-subtask-fix-001", "--output", str(FIXTURES / "fixer_output.yaml")])

    rc, data = run_bdw([
        "subtask", "create",
        "--file", str(FIXTURES / "beads_subtask_review2.valid.yaml"),
    ])
    assert rc == 0
    assert data["subtask"]["kind"] == "review"
    assert data["subtask"]["status"] == "ready"
    assert data["subtask"]["id"] == "bd-subtask-review-003"
    assert "finding-001" in data["subtask"]["input_refs"]["review_finding_ids"]


# -----------------------------------------------------------------------
# 17-6: Fixer の end-to-end フロー（finding → fixed → fix subtask closed → re-review ready）
# -----------------------------------------------------------------------
def test_fixer_full_flow(beads, run_bdw):
    """Fixer: finding → fixed → fix subtask closed → re-review ready の全フローが通る。"""
    _setup_with_finding_and_fix_subtask(run_bdw)

    # 1. fix subtask を claim
    rc, fix_st = run_bdw(["ready", "--role", "fix"])
    assert rc == 0
    assert fix_st["status"] == "in_progress"

    # 2. finding を fixed に
    rc, _ = run_bdw(["finding", "update", "finding-001", "--status", "fixed"])
    assert rc == 0

    # 3. fix subtask を close
    rc, _ = run_bdw(["close", "bd-subtask-fix-001", "--output", str(FIXTURES / "fixer_output.yaml")])
    assert rc == 0

    # 4. open finding が 0 件
    rc, open_findings = run_bdw(["finding", "list", "--task", "bd-task-001", "--open"])
    assert rc == 0
    assert open_findings == []

    # 5. 再 review subtask を作成
    rc, re_review = run_bdw([
        "subtask", "create",
        "--file", str(FIXTURES / "beads_subtask_review2.valid.yaml"),
    ])
    assert rc == 0
    assert re_review["subtask"]["kind"] == "review"
    assert re_review["subtask"]["status"] == "ready"

    # 6. re-review subtask が ready で claim できる
    rc, claimed = run_bdw(["ready", "--role", "review"])
    assert rc == 0
    assert claimed["kind"] == "review"
