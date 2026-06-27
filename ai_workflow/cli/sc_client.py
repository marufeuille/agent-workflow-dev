"""Shortcut Story のクライアント。

mock モード（fixture/file-backed）と real モード（Shortcut REST API）を持つ。
real は token 発行（人間作業・フェーズA）後の実装までスタブとし、本フェーズでは
mock で完結する。モードは SC_STORY_MODE 環境変数（既定 mock）で切替。

mock store は <SC_MOCK_DIR>/<story-id>.json に Story を保持する
（既定: .ai-workflow/mock/shortcut/）。テストは SC_MOCK_DIR で tmp を指す。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ShortcutError(Exception):
    """Shortcut 操作の失敗。"""


def _mock_dir() -> Path:
    return Path(os.environ.get("SC_MOCK_DIR", ".ai-workflow/mock/shortcut"))


class MockShortcutClient:
    """ファイルベースの mock Shortcut store。"""

    def __init__(self, base: str | Path | None = None) -> None:
        self.base = Path(base) if base else _mock_dir()

    def _path(self, story_id: str) -> Path:
        return self.base / f"{story_id}.json"

    def _read(self, story_id: str) -> dict:
        p = self._path(story_id)
        if not p.exists():
            raise ShortcutError(f"story not found (mock): {story_id}")
        return json.loads(p.read_text(encoding="utf-8"))

    def _write(self, story_id: str, data: dict) -> None:
        p = self._path(story_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, story_id: str) -> dict:
        return self._read(story_id)

    def comment(self, story_id: str, text: str) -> dict:
        data = self._read(story_id)
        data.setdefault("comments", []).append({"body": text})
        self._write(story_id, data)
        return {"story_id": story_id, "commented": True}

    def set_state(self, story_id: str, state: str) -> dict:
        data = self._read(story_id)
        data["state"] = state
        self._write(story_id, data)
        return {"story_id": story_id, "state": state}

    def set_metadata(self, story_id: str, metadata: dict) -> dict:
        data = self._read(story_id)
        data.setdefault("metadata", {}).update(metadata)
        self._write(story_id, data)
        return data


class RealShortcutClient:
    """Shortcut REST API クライアント（フェーズA の token 発行後に実装）。"""

    def __init__(self) -> None:
        token = os.environ.get("SHORTCUT_API_TOKEN")
        if not token:
            raise ShortcutError("SHORTCUT_API_TOKEN 未設定（real モード）。mock を使うか token を発行してください")
        self.token = token
        self.workspace = os.environ.get("SHORTCUT_WORKSPACE_ID")

    def _unimplemented(self, op: str):
        raise ShortcutError(
            f"real Shortcut API の {op} は未実装です（mock モードを使うか、フェーズA で実装してください）"
        )

    def get(self, story_id: str) -> dict:
        self._unimplemented("get")

    def comment(self, story_id: str, text: str) -> dict:
        self._unimplemented("comment")

    def set_state(self, story_id: str, state: str) -> dict:
        self._unimplemented("set_state")

    def set_metadata(self, story_id: str, metadata: dict) -> dict:
        self._unimplemented("set_metadata")


def make_client() -> Any:
    """SC_STORY_MODE（既定 mock）でクライアントを生成。"""
    mode = os.environ.get("SC_STORY_MODE", "mock").lower()
    if mode == "real":
        return RealShortcutClient()
    return MockShortcutClient()
