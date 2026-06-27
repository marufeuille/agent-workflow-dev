# フェーズB 実装ログ: 基盤・スキーマ・設定

- 完了日: 2026-06-28
- 対象: TODO.md 大項目 5・6・7
- 計画: `~/.claude/plans/magical-mapping-hartmanis.md`

## 概要
後続フェーズ（C: wrapper CLI / D: Claude Code 設定 / E: 検証）が依存する
データスキーマ・設定ファイル・ディレクトリ骨格・Python 基盤・validation 仕組みを固めた。

## 成果物

### ディレクトリ骨格（大項目5）
- `.claude/agents/`, `.claude/commands/`, `bin/`（`.gitkeep` のみ。中身は後フェーズ）
- `CLAUDE.md`: 不変ルール6条・データモデル・branch命名規則・wrapper CLI/設定の参照

### workflow 設定（大項目6）
- `.ai-workflow/config.yaml`: `shortcut.states` / `github`(default_branch, branch_prefix, allow_ai_*) / `planning_policy` / `schemas.dir`

### データスキーマ（大項目7）
- `.ai-workflow/schemas/` に5つの JSON Schema (draft-07, `additionalProperties: false`)
  - `planned_pr_task` / `beads_task` / `beads_subtask` / `review_finding` / `story_review_summary`

### Python 基盤 + validation
- `pyproject.toml`（uv 管理。deps: jsonschema/pyyaml, dev: pytest）
- `ai_workflow/config.py`: `load_config()` が config.yaml を型付き dataclass で返す
- `ai_workflow/schema_validator.py`: `validate()` + CLI（`python -m ai_workflow.schema_validator <file> <schema>`）
- `tests/fixtures/*.valid.yaml`: sc-123 saved-filters シナリオの正常系サンプル
- `tests/test_schema_validation.py`: 正常系5 + 異常系2 + config読込

## 検証結果
- `uv sync`: 成功（ai-workflow パッケージ + 依存13件インストール）
- `uv run pytest tests/ -v`: **8 passed**（0.56s）
- CLI validator: 正常系 exit 0 / 異常系（必須プロパティ欠落）exit 1 を確認

## 主要な決定事項
1. **論理スキーマを先に定義、bd 物理マッピングは後送り**: `bd` は階層コマンド（task/subtask/finding）を持たず、issue+type+state+metadata+link モデル。5スキーマは論理データモデルとし、bd 物理構造へのマッピングはフェーズC の `bin/bdw` 実装時に決める。
2. **`additionalProperties: false` で厳格化**: 未知フィールドを弾き、agent の出力ぶれを検出する。
3. **`current_phase` / `category` の値は最小セット**: 設計書で確定値が無いため実用的な最小セットを定義し、フェーズE検証で固める。
4. **subtasks/findings は正規化**: `beads_task` に含めず、親参照で別エンティティ。集約は `story_review_summary` 層で扱う。
5. **依存ライブラリを最小化**: jsonschema, pyyaml のみ（フェーズCで requests 等を追加予定）。

## フェーズCへの引き継ぎ
- `bin/bdw`（大項目9）で、5スキーマを bd の issue モデルへマッピングする方針を決定:
  - type = `beads_story` / `beads_task` / `beads_subtask` / `review_finding`
  - `kind` / `status` / `current_phase` / `severity` を state / metadata / label のいずれで表現するか
  - `parent_task_id` / `depends_on` を `bd link`（dependency）で表現するか
- `bd create/show/list/close/link/set-state` の JSON 出力形式を フェーズC 冒頭で確認
- `bin/sc-story`（大項目8）で requests 追加、`bin/ghw`（大項目10）は gh CLI を subprocess でラップ

## ファイル一覧
- `pyproject.toml`, `.python-version`
- `CLAUDE.md`
- `.ai-workflow/config.yaml`
- `.ai-workflow/schemas/{planned_pr_task,beads_task,beads_subtask,review_finding,story_review_summary}.schema.json`
- `ai_workflow/{__init__,config,schema_validator}.py`
- `tests/fixtures/*.valid.yaml`, `tests/test_schema_validation.py`
- `.claude/{agents,commands}/.gitkeep`, `bin/.gitkeep`
