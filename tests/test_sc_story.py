"""bin/sc-story のテスト（mock モードで検証）。

real Shortcut API 連携はフェーズA（token 発行）後まで後回し。
mock store（SC_MOCK_DIR）で get/comment/set-state/link を検証し、
Done 遷移のガードが効くことを確認する。
"""

from __future__ import annotations

from pathlib import Path

STORY = {
    "id": "sc-1",
    "name": "Test story",
    "state": "Ready",
    "acceptance_criteria": ["AC-1: 保存したフィルタが復元される"],
    "comments": [],
}


def test_get(run_sc):
    rc, data = run_sc(["get", "sc-1"], story=STORY)
    assert rc == 0
    assert data["id"] == "sc-1"
    assert data["state"] == "Ready"


def test_get_missing(run_sc):
    rc, _ = run_sc(["get", "sc-999"])  # story 未設置
    assert rc == 1


def test_comment(run_sc, tmp_path: Path):
    body = tmp_path / "comment.md"
    body.write_text("planning summary")
    rc, data = run_sc(["comment", "sc-1", "--file", str(body)], story=STORY)
    assert rc == 0
    assert data["commented"] is True
    rc, after = run_sc(["get", "sc-1"])
    assert any("planning summary" in c["body"] for c in after["comments"])


def test_set_state(run_sc):
    rc, data = run_sc(["set-state", "sc-1", "Doing"], story=STORY)
    assert rc == 0
    assert data["state"] == "Doing"
    rc, after = run_sc(["get", "sc-1"])
    assert after["state"] == "Doing"


def test_set_state_done_blocked(run_sc):
    """Shortcut Story の Done 遷移は AI に許さない（不変ルール3）。"""
    rc, _ = run_sc(["set-state", "sc-1", "Done"], story=STORY)
    assert rc == 1


def test_link(run_sc):
    rc, data = run_sc(["link", "sc-1", "--beads-story", "bd-story-001"], story=STORY)
    assert rc == 0
    rc, after = run_sc(["get", "sc-1"])
    assert after["metadata"]["beads_story_id"] == "bd-story-001"
