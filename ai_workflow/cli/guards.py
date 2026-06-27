"""wrapper CLI のセーフティガード。

外部システムへ作用する操作のうち、不変ルール（main merge 禁止・
Shortcut Done 禁止・schema 違反データの永続化禁止）を CLI 層で強制する。
各 handler は外部 API 呼出前に対応するガードを呼び、GuardError を
main で catch して stderr + exit 1 とする。
"""

from __future__ import annotations

import jsonschema

from ai_workflow.config import WorkflowConfig
from ai_workflow.schema_validator import validate


class GuardError(Exception):
    """ガード違反。main で catch して exit 1 にする。"""


def block_shortcut_done(state: str, cfg: WorkflowConfig) -> None:
    """Shortcut Story を Done にする操作をブロック（人間のみ）。"""
    if state == cfg.shortcut_states.done and not cfg.github.allow_ai_mark_shortcut_done:
        raise GuardError(
            f"AI agent は Shortcut Story を '{cfg.shortcut_states.done}' にできません"
            "（Done 判断は人間のみ）"
        )


def block_pr_base(base: str, cfg: WorkflowConfig) -> None:
    """PR の base が default branch（main）なのをブロック（task PR は story branch 宛て）。"""
    if base == cfg.github.default_branch and not cfg.github.allow_ai_merge_to_main:
        raise GuardError(
            f"PR の base に '{base}' は指定できません（story branch を指定してください）"
        )


def block_ai_merge() -> None:
    """merge コマンド自体が存在しないことを表明（main merge は人間のみ）。"""
    raise GuardError("merge は実装されていません（main merge は人間のみ）")


def require_valid(instance: dict, schema_name: str, schemas_dir: str) -> None:
    """instance が schema に適合することを要求。違反なら GuardError。"""
    try:
        validate(instance, schema_name, schemas_dir)
    except jsonschema.ValidationError as e:
        location = "/".join(str(p) for p in e.absolute_path) or "<root>"
        raise GuardError(
            f"schema validation 失敗 ({schema_name}): {e.message} at {location}"
        )
