"""wrapper CLI 共通ユーティリティ。

各 CLI（sc-story / bdw / ghw）で共通して使う、設定ロード・JSON 出力・
ファイル読込・slug 生成・終了処理・BEADS_DIR 解決を置く。
外部システム依存は持たない純粋なヘルパ集。
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import yaml

from ai_workflow.config import DEFAULT_CONFIG_PATH, WorkflowConfig, load_config as _load_config


def load_config() -> WorkflowConfig:
    """config.yaml を読む。AI_WORKFLOW_CONFIG 環境変数でパスを上書き可能（テスト用）。"""
    path = os.environ.get("AI_WORKFLOW_CONFIG", str(DEFAULT_CONFIG_PATH))
    return _load_config(path)


def emit_json(obj: object) -> None:
    """obj を整形済み JSON として stdout に出力（agent が parse しやすい形式）。"""
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def die(msg: str, code: int = 1) -> None:
    """stderr にメッセージを出力して終了。"""
    print(msg, file=sys.stderr)
    sys.exit(code)


def read_yaml_file(path: str | Path) -> dict:
    """YAML/JSON ファイルを読み込んで dict を返す。"""
    p = Path(path)
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def read_text_file(path: str | Path) -> str:
    """テキストファイルを読み込む（PR 本文やコメント本文等）。"""
    return Path(path).read_text(encoding="utf-8")


def slugify(text: str) -> str:
    """text を branch 名に使える slug に変換（小文字・英数字・ハイフン）。"""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "task"


def beads_dir() -> str:
    """bd の DB ディレクトリを解決。BEADS_DIR 環境変数 or '<cwd>/.beads'。"""
    return os.environ.get("BEADS_DIR", str(Path.cwd() / ".beads"))


def drop_none(d: dict) -> dict:
    """値が None のキーを除外した dict を返す（bd metadata に null を入れないため）。"""
    return {k: v for k, v in d.items() if v is not None}
