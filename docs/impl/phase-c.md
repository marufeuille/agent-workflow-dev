# フェーズC 実装ログ: wrapper CLI 3種 + 5スキーマ→bd マッピング

- 完了日: 2026-06-28
- 対象: TODO.md 大項目 8・9・10
- 計画: `~/.claude/plans/proud-wondering-tiger.md`
- マッピング設計: [docs/design/bd-mapping.md](../design/bd-mapping.md)

## 概要
5つの AI agent（フェーズDで作成）が外部システムを直接触らず、3つの wrapper CLI
（`bin/sc-story` / `bin/bdw` / `bin/ghw`）を経由して操作できるようにした。セーフティ
（main 操作禁止・Shortcut Done 禁止・schema 違反データの永続化禁止）を CLI 層に集約。

最大の設計ポイントだった「5スキーマ → bd issue のマッピング」は、工程0で bd v1.0.4 の
実物 JSON 構造を確認して確定した（後述）。

## 工程0: bd 実物確認（設計の前提）
`tmp_path` に `bd init` → `create`（各 type）→ `show --json` で実物を捕捉。判明した制約:
- `create` で `--id` と `--parent` は**排他** → 親は create 後に `update --parent` で後付け。
- `create` に `--status` は**無い**（デフォルト open）→ 変更は `update --status` / `close`。
- bd に `fixed` status は**無い** → `closed` で代用、schema 準拠の正は metadata.status に保持。
- `set-state dim=val` は label `dim:val` を付与し event bead を記録（phase 表現に使用）。
- `list --label kind:X --status open --ready` で ready な role 別 subtask を取得可能。
- custom type は `bd config set types.custom "..."` で登録（警告は出るが反映される）。

## 成果物

### `bin/bdw`（大項目9）— 核心
- `ai_workflow/cli/bd_client.py`: bd CLI の subprocess ラッパ（create/update/set_state/
  close/show/list/types/init/config_set/next_id）。JSON parse・エラー抽出（auto-export 警告は無視）。
- `ai_workflow/cli/bd_mapping.py`: 5スキーマ ↔ bd issue の双方向変換（[bd-mapping.md](../design/bd-mapping.md)）。
- `ai_workflow/cli/bd_setup.py`: `bdw init`（bd init + custom type 登録、冪等）。
- `ai_workflow/cli/bdw.py`: 全コマンドの main。
- **TODO9 拡張2件**（設計書 12/13 が必須とする操作。TODO コードブロックに追記）:
  - `finding update <id> --status fixed`（finding.status の open→fixed 更新）
  - `task set-phase <id> <phase>`（current_phase の更新、set-state phase + metadata 同期）

### `bin/ghw`（大項目10）
- `ai_workflow/cli/gh_client.py`: gh/git の subprocess ラッパ + dry-run 合成応答。
- `ai_workflow/cli/ghw.py`: branch 作成・PR 操作の main。task PR の `base=main` を拒否、
  merge コマンドは実装しない（final PR の `base=main` は正当・人間 merge）。

### `bin/sc-story`（大項目8）
- `ai_workflow/cli/sc_client.py`: mock store（file-backed）+ real スタブ（後回し）。
- `ai_workflow/cli/sc_story.py`: get/comment/set-state/link の main。Done 遷移を拒否。

### 共通
- `ai_workflow/cli/common.py`: load_config / emit_json / die / read_yaml_file / slugify / beads_dir / drop_none
- `ai_workflow/cli/guards.py`: block_shortcut_done / block_pr_base / block_ai_merge / require_valid

## 検証結果
- `uv run pytest tests/ -v`: **37 passed**（フェーズB既存8 + フェーズC新規29）
  - test_bdw.py: 17件（bd 実物で統合テスト: init/story/task/ready/close/finding/link-pr/set-phase/guard/mapping）
  - test_ghw.py: 6件（dry-run: branch 命名・base=main 拒否・create-final 許可）
  - test_sc_story.py: 6件（mock: get/comment/set-state/Done拒否/link）
  - test_guards.py: 8件（各ガードの境界）
- bdw 統合テストは各テストで `bd init`（Dolt embedded 起動）を走るため ~3.5min。
  実 repo 連携・CI での最適化（DB 共有等）は後課題。

## 主要な決定事項
1. **状態概念を責務別スロットへ分離**: type=種別(不変), status=ライフサイクル, labels=恒久タグ(kind/severity/phase), set-state=推移状態(phase), metadata=構造化データ。kind/severity を set-state でなく label にした（不変属性は label が適切）。
2. **スキーマ ID と bd ID を一致**: `create --id <id> --force` で明示指定。親は `--id` と排他のため update で後付け。
3. **schema 準拠の正は metadata に二重保持**: status（finding の fixed 等）を bd status と metadata の両方に持ち、逆変換で metadata を優先して復元。
4. **実連携は mock/dry-run で完結**: sc-story は mock store、ghw は dry-run + safe 呼出。実 token・実 repo PR はフェーズA（人間作業）後。`requests` 依存は追加していない。
5. **`bin/*` は sh シム**: `exec uv run python -m ai_workflow.cli.<name>`。`[project.scripts]` は追加せず TODO の `bin/` 配置を維持。
6. **ready は原子的 claim**: `ready --role` は先頭1件を `in_progress` 化して返す（race 回避）。`--list` で非破壊一覧。

## フェーズDへの引き継ぎ
- 各 agent（`.claude/agents/*.md`）と command（`.claude/commands/*.md`）は、本フェーズの3 CLI を呼び出す形で実装する。
- 各 CLI のコマンド仕様: TODO.md 大項目8-10（+ 大項目9 拡張2件）と [bd-mapping.md](../design/bd-mapping.md) §6 を参照。
- 実連携切替: sc-story は `SC_STORY_MODE=real` + `SHORTCUT_API_TOKEN`（RealShortcutClient の実装をフェーズA後に完成）。ghw は `GHW_DRY_RUN` を外せば実 gh/git 呼出。
- bd DB は `bdw init`（`bd init --stealth` 相当）でリポジトリルートに `.beads/`（.gitignore 済）。

## ファイル一覧
- `ai_workflow/cli/{__init__,common,guards,bd_client,bd_mapping,bd_setup,bdw,gh_client,ghw,sc_client,sc_story}.py`
- `bin/{sc-story,bdw,ghw}`（sh シム、実行権限付き）
- `tests/{conftest,test_bdw,test_ghw,test_sc_story,test_guards}.py`
- `tests/fixtures/{fixer_output.yaml,review_finding.invalid.yaml}`
- `docs/design/bd-mapping.md`, `docs/impl/phase-c.md`
- `.gitignore`（`.beads/` 追加）
