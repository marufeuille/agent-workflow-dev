"""JSON Schema によるデータ検証。

Claude Code（agent / command）が出力した YAML/JSON が、
.ai-workflow/schemas/ 配下のスキーマに適合するかを検証する。
wrapper CLI も、永続化前にこの検証を通す。

CLI: uv run python -m ai_workflow.schema_validator <file> <schema-name>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import yaml

# スキーマ名 → ファイル名の対応。
# スキーマ名は planned_pr_task / beads_task / beads_subtask / review_finding / story_review_summary。
SCHEMA_NAME_TO_FILE = {
    "planned_pr_task": "planned_pr_task.schema.json",
    "beads_task": "beads_task.schema.json",
    "beads_subtask": "beads_subtask.schema.json",
    "review_finding": "review_finding.schema.json",
    "story_review_summary": "story_review_summary.schema.json",
}

DEFAULT_SCHEMAS_DIR = ".ai-workflow/schemas"


def load_schema(schema_name: str, schemas_dir: str | Path = DEFAULT_SCHEMAS_DIR) -> dict:
    """スキーマ名から JSON Schema を読み込む。"""
    if schema_name not in SCHEMA_NAME_TO_FILE:
        valid = ", ".join(sorted(SCHEMA_NAME_TO_FILE))
        raise ValueError(f"unknown schema '{schema_name}'. valid: {valid}")
    path = Path(schemas_dir) / SCHEMA_NAME_TO_FILE[schema_name]
    if not path.exists():
        raise FileNotFoundError(f"schema file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_instance(path: str | Path) -> dict:
    """検証対象の YAML/JSON ファイルを読み込む。"""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        return yaml.safe_load(text)
    return json.loads(text)


def validate(
    instance: dict,
    schema_name: str,
    schemas_dir: str | Path = DEFAULT_SCHEMAS_DIR,
) -> None:
    """instance を schema_name で検証。失敗時は jsonschema.ValidationError を raise する。"""
    schema = load_schema(schema_name, schemas_dir)
    jsonschema.validate(instance=instance, schema=schema)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        print(
            "usage: python -m ai_workflow.schema_validator <file> <schema-name>",
            file=sys.stderr,
        )
        return 2
    file_path, schema_name = argv
    try:
        instance = load_instance(file_path)
        validate(instance, schema_name)
    except jsonschema.ValidationError as e:
        location = "/".join(str(p) for p in e.absolute_path) or "<root>"
        print(
            f"INVALID ({schema_name}): {e.message}\n  at: {location}",
            file=sys.stderr,
        )
        return 1
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    print(f"OK: {file_path} is valid against {schema_name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
