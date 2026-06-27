"""guards.py の unit テスト。

各セーフティガードが、違反時に GuardError を raise し、正当な場合は素通りすることを検証する。
"""

from __future__ import annotations

import pytest

from ai_workflow.config import WorkflowConfig
from ai_workflow.cli.guards import (
    GuardError,
    block_ai_merge,
    block_pr_base,
    block_shortcut_done,
    require_valid,
)

SCHEMAS = ".ai-workflow/schemas"
VALID_TASK = {
    "id": "bd-task-x",
    "shortcut_story_id": "sc-1",
    "title": "T",
    "planned_pr_scope": "scope",
    "acceptance_refs": ["AC-1"],
    "expected_files": ["a/*"],
}


def test_block_shortcut_done_rejects_done():
    with pytest.raises(GuardError):
        block_shortcut_done("Done", WorkflowConfig())


def test_block_shortcut_done_allows_in_review():
    block_shortcut_done("In Review", WorkflowConfig())  # 例外なし


def test_block_pr_base_rejects_main():
    with pytest.raises(GuardError):
        block_pr_base("main", WorkflowConfig())


def test_block_pr_base_allows_story_branch():
    block_pr_base("story/sc-1-x", WorkflowConfig())  # 例外なし


def test_block_ai_merge_always_raises():
    """merge コマンドは実装しない（main merge は人間のみ）。"""
    with pytest.raises(GuardError):
        block_ai_merge()


def test_require_valid_accepts_valid():
    require_valid(VALID_TASK, "beads_task", SCHEMAS)  # 例外なし


def test_require_valid_rejects_invalid():
    with pytest.raises(GuardError):
        require_valid({"id": "x"}, "beads_task", SCHEMAS)


def test_allow_flags_disable_guards():
    """allow_ai_merge_to_main / allow_ai_mark_shortcut_done が True ならガード無効。"""
    cfg = WorkflowConfig()
    cfg.github.allow_ai_merge_to_main = True
    cfg.github.allow_ai_mark_shortcut_done = True
    block_pr_base("main", cfg)  # 例外なし
    block_shortcut_done("Done", cfg)  # 例外なし
