"""pytest 共通 fixture。

- beads: 各テストで独立した bd DB（tmp_path 配下）を初期化した BdClient。
- run_bdw: bdw.main(argv) を実行し (exit_code, parsed_json) を返す。
- run_ghw: ghw.main(argv) を dry-run モードで実行し (exit_code, parsed_json) を返す。
- run_sc: sc_story.main(argv) を mock モードで実行する。story= で事前設置できる。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def beads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """init 済みの BdClient と、それを指す BEADS_DIR 環境変数を用意する。"""
    monkeypatch.setenv("BEADS_DIR", str(tmp_path / ".beads"))
    monkeypatch.setenv("BD_NON_INTERACTIVE", "1")
    from ai_workflow.cli import bd_setup
    from ai_workflow.cli.bd_client import BdClient

    bd = BdClient(directory=str(tmp_path / ".beads"))
    bd_setup.run(bd)
    bd.disable_auto_export()  # git 連携の警告を消す
    return bd


def _run_cli(main_fn, argv: list[str], capsys) -> tuple[int, object]:
    try:
        rc = main_fn(list(argv))
    except SystemExit as e:  # die() による終了
        rc = int(e.code) if isinstance(e.code, int) else 1
    out = capsys.readouterr().out
    parsed = None
    if out.strip():
        try:
            parsed = json.loads(out)
        except json.JSONDecodeError:
            parsed = out.strip()
    return rc, parsed


@pytest.fixture
def run_bdw(capsys):
    """bdw.main(argv) を実行し (exit_code, parsed_json_or_none) を返す。
    BEADS_DIR は各テストで beads fixture と組み合わせて設定する。
    """
    from ai_workflow.cli import bdw

    return lambda argv: _run_cli(bdw.main, argv, capsys)


@pytest.fixture
def run_ghw(monkeypatch: pytest.MonkeyPatch, capsys):
    """ghw.main(argv) を dry-run モードで実行し (exit_code, parsed_json) を返す。"""
    monkeypatch.setenv("GHW_DRY_RUN", "1")
    from ai_workflow.cli import ghw

    return lambda argv: _run_cli(ghw.main, argv, capsys)


@pytest.fixture
def run_sc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    """sc_story.main(argv) を mock モードで実行する。story= を渡すと事前に設置する。"""
    mock_dir = tmp_path / "shortcut"
    mock_dir.mkdir()
    monkeypatch.setenv("SC_MOCK_DIR", str(mock_dir))
    monkeypatch.setenv("SC_STORY_MODE", "mock")
    from ai_workflow.cli import sc_story

    def _run(argv: list[str], story: dict | None = None):
        if story:
            (mock_dir / f"{story['id']}.json").write_text(
                json.dumps(story, ensure_ascii=False), encoding="utf-8"
            )
        return _run_cli(sc_story.main, argv, capsys)

    return _run
