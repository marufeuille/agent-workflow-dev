"""bdw init: bd DB の初期化と custom type 登録。

`bd init`（embedded Dolt）でリポジトリルートに .beads/ を作成し、
5スキーマのエンティティ種別を custom type として登録する。
"""

from __future__ import annotations

from .bd_client import BdClient
from .bd_mapping import TYPE_FINDING, TYPE_STORY, TYPE_SUBTASK, TYPE_TASK

REQUIRED_TYPES = [TYPE_STORY, TYPE_TASK, TYPE_SUBTASK, TYPE_FINDING]


def run(bd: BdClient, *, prefix: str = "bd") -> dict:
    """bd を初期化し、custom type を登録して検証結果を返す（冪等）。"""
    bd.init(prefix=prefix)
    bd.config_set("types.custom", ",".join(REQUIRED_TYPES))
    types_info = bd.types()
    custom = set(types_info.get("custom_types", []))
    registered = [t for t in REQUIRED_TYPES if t in custom]
    missing = [t for t in REQUIRED_TYPES if t not in custom]
    return {
        "initialized": True,
        "prefix": prefix,
        "registered_types": registered,
        "missing_types": missing,
    }
