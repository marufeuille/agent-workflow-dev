"""スキーマ検証のテスト。

正常系: 各 fixture が対応スキーマで valid になること。
異常系: validator が機能することを確認するための最小のケース（enum 違反・必須欠落）。
"""

from __future__ import annotations

from pathlib import Path

import jsonschema
import pytest
import yaml

from ai_workflow.config import load_config
from ai_workflow.schema_validator import validate

FIXTURES = Path(__file__).parent / "fixtures"
SCHEMAS_DIR = Path(__file__).parent.parent / ".ai-workflow" / "schemas"
CONFIG_PATH = Path(__file__).parent.parent / ".ai-workflow" / "config.yaml"

VALID_CASES = [
    ("planned_pr_task.valid.yaml", "planned_pr_task"),
    ("beads_task.valid.yaml", "beads_task"),
    ("beads_subtask.valid.yaml", "beads_subtask"),
    ("review_finding.valid.yaml", "review_finding"),
    ("story_review_summary.valid.yaml", "story_review_summary"),
]


def _load(name: str) -> dict:
    return yaml.safe_load((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("fixture_name,schema_name", VALID_CASES)
def test_valid_fixtures_pass(fixture_name: str, schema_name: str) -> None:
    """各 fixture は対応スキーマで valid になる。"""
    validate(_load(fixture_name), schema_name, schemas_dir=SCHEMAS_DIR)


def test_subtask_kind_enum_violation() -> None:
    """beads_subtask の kind に不正値を入れると ValidationError。"""
    instance = {
        "id": "bd-subtask-x",
        "kind": "INVALID_KIND",
        "status": "ready",
        "parent_task_id": "bd-task-001",
    }
    with pytest.raises(jsonschema.ValidationError):
        validate(instance, "beads_subtask", schemas_dir=SCHEMAS_DIR)


def test_beads_task_missing_required() -> None:
    """beads_task の必須フィールドが欠けると ValidationError。"""
    instance = {"id": "bd-task-x"}  # shortcut_story_id / title / scope ... が無い
    with pytest.raises(jsonschema.ValidationError):
        validate(instance, "beads_task", schemas_dir=SCHEMAS_DIR)


def test_config_loads() -> None:
    """config.yaml が load_config で正しく読める。"""
    cfg = load_config(CONFIG_PATH)
    assert cfg.github.default_branch == "main"
    assert cfg.github.allow_ai_merge_to_main is False
    assert cfg.github.allow_ai_mark_shortcut_done is False
    assert cfg.shortcut_states.done == "Done"
    assert cfg.planning_policy.branch_strategy == "story_branch"
    assert cfg.schemas_dir == ".ai-workflow/schemas"
