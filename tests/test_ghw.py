"""bin/ghw のテスト（dry-run モードで検証）。

実 repo への branch/PR 作成はフェーズCのスコープ外。GHW_DRY_RUN=1 で
合成応答を返し、branch 命名規則・ガード（main 宛て PR 拒否・merge 無）を検証する。
"""

from __future__ import annotations

from pathlib import Path


def test_branch_create_story(run_ghw):
    rc, data = run_ghw(["branch", "create-story", "123", "--from", "main", "--slug", "saved-filters"])
    assert rc == 0
    assert data["branch"] == "story/sc-123-saved-filters"
    assert data["from"] == "main"
    assert data["dry_run"] is True


def test_branch_create_task(run_ghw):
    rc, data = run_ghw(
        [
            "branch", "create-task", "123", "saved-filters-api",
            "--from", "story/sc-123-saved-filters",
        ]
    )
    assert rc == 0
    assert data["branch"] == "agent/sc-123-saved-filters-api"


def test_pr_create_dry_run(tmp_path: Path, run_ghw):
    body = tmp_path / "body.md"
    body.write_text("PR body")
    rc, data = run_ghw(
        [
            "pr", "create",
            "--base", "story/sc-123-x",
            "--head", "agent/sc-123-x-api",
            "--body", str(body),
        ]
    )
    assert rc == 0
    assert data["base"] == "story/sc-123-x"
    assert data["head"] == "agent/sc-123-x-api"
    assert data["dry_run"] is True


def test_pr_create_blocks_main(tmp_path: Path, run_ghw):
    """task PR の base==main は拒否される（不変ルール2）。"""
    body = tmp_path / "body.md"
    body.write_text("x")
    rc, _ = run_ghw(
        ["pr", "create", "--base", "main", "--head", "agent/x", "--body", str(body)]
    )
    assert rc == 1


def test_pr_view_comment_checks_dry_run(tmp_path: Path, run_ghw):
    rc, data = run_ghw(["pr", "view", "456"])
    assert rc == 0
    assert data["number"] == 456

    c = tmp_path / "c.md"
    c.write_text("comment text")
    rc, data = run_ghw(["pr", "comment", "456", "--file", str(c)])
    assert rc == 0
    assert data["commented"] is True

    rc, data = run_ghw(["pr", "checks", "456"])
    assert rc == 0
    assert data["number"] == 456


def test_pr_create_final_allows_main(run_ghw):
    """final PR の base==main は正当（人間が merge）。merge は実装しない。"""
    rc, data = run_ghw(["pr", "create-final", "--story-branch", "story/sc-123-x", "--base", "main"])
    assert rc == 0
    assert data["base"] == "main"
    assert data["head"] == "story/sc-123-x"
    assert data["merge"] == "human-only"
