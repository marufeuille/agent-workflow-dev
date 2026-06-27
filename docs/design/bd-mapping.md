# 5スキーマ → beads(bd) issue マッピング設計

フェーズC（`bin/bdw`）で、5つの論理データスキーマを beads CLI（bd v1.0.4）の
issue モデルへどうマッピングするかを定義する。実装は `ai_workflow/cli/bd_mapping.py`。
工程0（実物確認）で判明した bd の挙動に基づく。

## 1. 前提: bd はフラット issue モデル

bd は階層コマンド（task/subtask/finding）を持たない。1つの issue に
`type` / `status` / `labels` / `metadata` / `parent` / `deps` / `external-ref` を
付与して表現する。5スキーマ（beads_story / beads_task / beads_subtask /
review_finding）をこのモデルへ、**状態概念を責務ごとに別スロットへ分離**して格納する。

## 2. スロットの役割分担

| bd スロット | 役割 | 格納するもの |
|---|---|---|
| `--type`（custom） | エンティティ種別（不変） | `beads_story` / `beads_task` / `beads_subtask` / `review_finding` |
| `--status`（組み込み） | ライフサイクル | subtask: ready→`open` / `in_progress` / `closed`。finding: open→`open` / fixed→`closed` |
| `-l labels` | 恒久タグ（queryable） | `kind:<kind>` / `severity:<sev>` / `phase:<phase>` / `story`/`task`/`subtask`/`finding` |
| `set-state dim=val` | 推移状態（監査付き event bead） | `phase=<current_phase>`（label `phase:<val>` を付与） |
| `--metadata`（JSON） | 構造化データ | scope / files / refs / instructions / input_refs / output_refs / pr_numbers 等。schema 準拠の正も保持 |
| `--parent` | 階層 | task→story, subtask→task, finding→task |
| `--external-ref` | 外部ID | `sc-<id>`（story の Shortcut 紐付け） |
| `--deps 'type:id'` | 依存 | beads_task.depends_on を `blocks:<id>` で表現 |

## 3. 各エンティティのマッピング

### beads_story
| bd スロット | 値 |
|---|---|
| type | `beads_story` |
| id | `bd-story-<seq>`（採番） |
| title | `--title` |
| status | `open`（人間が close） |
| external-ref | `sc-<shortcut-id>` |
| labels | `story` |
| metadata | `beads_story_id`, `shortcut_story_id`, `title` |
| parent | なし（root） |

### beads_task
| bd スロット | 値 |
|---|---|
| type | `beads_task` |
| id | `bd-task-<seq>` |
| parent | `bd-story-<id>` |
| labels | `task` |
| set-state | `phase=planning`（作成直後） |
| deps | depends_on 各 id を `blocks:<id>` |
| metadata | `shortcut_story_id`, `planned_pr_scope`, `acceptance_refs[]`, `expected_files[]`, `branch_name`, `pr_numbers[]`, `current_phase`, `depends_on[]` |

### beads_subtask
| bd スロット | 値 |
|---|---|
| type | `beads_subtask` |
| id | `bd-subtask-<kind>-<seq>` |
| parent | `bd-task-<id>` |
| status | `ready`→`open`, `in_progress`→`in_progress`, `closed`→`closed` |
| labels | `kind:<kind>`（implement/review/fix/verify/summarize）, `subtask` |
| metadata | `kind`, `parent_task_id`, `instructions`, `input_refs{}`, `output_refs{}`, `status`（schema 準拠の正） |

### review_finding
| bd スロット | 値 |
|---|---|
| type | `review_finding` |
| id | `finding-<seq>` |
| parent | `bd-task-<id>`（task_id） |
| status | `open`→`open`, `fixed`→`closed` |
| labels | `severity:<sev>`（must_fix/should_fix/nit/question）, `finding` |
| metadata | `task_id`, `severity`, `category`, `file`, `line`, `description`, `suggested_fix`, `status`（schema 準拠の正） |

## 4. 状態概念の表現まとめ

| スキーマ概念 | 値 | bd 表現 | 理由 |
|---|---|---|---|
| subtask.status | ready | `status=open`（blocker 無しで `--ready` 成立） | bd の ready セマンティクスに一致 |
| subtask.status | in_progress / closed | `status=in_progress` / `closed` | 1:1 |
| finding.status | open / fixed | `status=open` / `closed` | bd に fixed は無い。正は metadata.status |
| task.current_phase | planning…done | `set-state phase=<val>`（label `phase:<val>`） | 推移的状態。監査ログが残り query 可能 |
| subtask.kind | implement…summarize | label `kind:<val>`（不変） | 恒久タグ。`bd list --label kind:fix` で検索 |
| finding.severity | must_fix… | label `severity:<val>`（不変） | 恒久タグ。query 可能 |

kind/severity を set-state でなく label にする理由: これらは作成時に決まり不変。
set-state は状態遷移の監査用で、不変属性には過剰かつ label 重複削除ロジックと衝突する恐れがある。

## 5. 工程0で判明した bd の制約と対策

| 制約 | 影響 | 対策 |
|---|---|---|
| `create` で `--id` と `--parent` が**排他** | スキーマ ID を指定しつつ親を設定できない | `create --id <id> --force` で作成後、`update --parent <parent>` で親を後付け（2段階） |
| `create` に `--status` が**無い**（デフォルト open） | 作成時に status を指定できない | ready/open はデフォルトで OK。in_progress/closed は `update --status` / `close` で別途 |
| bd に `fixed` status が**無い** | finding.status=fixed を表現できない | `closed` で代用し、schema 準拠の正は metadata.status に保持。逆変換で復元 |
| `--set-metadata` で配列/ネストが文字列化される恐れ | pr_numbers 等の配列更新 | read-modify-write で `update --metadata '<JSON全体>'` で上書き（`_merge_metadata`） |
| custom type 登録で警告が出る | `types.custom` が非公認キー扱い | 警告は出るが `bd types --json` の `custom_types` に反映されるため実用上問題なし |
| auto-export が git add を試みる（git 無し環境で警告） | テスト環境で stderr がうるさい | テストの init 後に `bd config set export.auto false`（`disable_auto_export`）で無効化 |

## 6. bdw コマンド ↔ bd 操作の対応表

| bdw コマンド | bd 操作 |
|---|---|
| `story create` | `create --type beads_story --id <id> --force --external-ref sc-<id> --labels story --metadata {...}` |
| `task create` | `create --type beads_task --id <id> --force --labels task --metadata {...}` → `update <id> --parent <story>` → `set-state <id> phase=planning`（+ initial_subtasks を同様に作成） |
| `subtask create` | `create --type beads_subtask --id <id> --force --labels kind:<kind>,subtask --metadata {...}` → `update <id> --parent <task>` |
| `finding create` | `create --type review_finding --id <id> --force --labels severity:<sev>,finding --metadata {...}` → `update <id> --parent <task>` |
| `ready --role <r>` | `list --type beads_subtask --label kind:<r> --status open --ready --json`（claim するなら先頭を `update --status in_progress`） |
| `close <id>` | `_merge_metadata` で output_refs を反映 → `close <id>` |
| `finding list --task <t> --open` | `list --type review_finding --parent <t> --status open --json` |
| `finding update --status fixed` | `_merge_metadata` status=fixed → `set-state finding=fixed` → `close <id>` |
| `task link-pr` | `show` で pr_numbers 取得 → read-modify-write で `_merge_metadata` |
| `task set-phase` | `set-state <id> phase=<phase>` + `_merge_metadata` current_phase |

## 7. 逆変換（bd show --json → schema dict）のルール

`bd_to_task` / `bd_to_subtask` / `bd_to_finding` は `show --json` の1件（配列の先頭）から
schema 準拠の dict を復元する:

- `issue_type` でエンティティ種別を判定
- `status`: bd status を逆マップ（open→ready/open, closed→closed/fixed）。ただし **metadata.status が schema 値ならそちらを優先**（fixed 等の正）
- `kind` / `severity`: label `kind:*` / `severity:*` から抽出（fallback で metadata）
- `current_phase`: label `phase:*` を優先、無ければ metadata.current_phase
- `parent_task_id` / `task_id`: `parent` フィールドを優先、無ければ metadata
- 任意フィールドは、metadata に存在するときのみ dict に含める（schema の additionalProperties: false に合致）

## 8. ID 採番

`BdClient.next_id(id_prefix, issue_type=...)` が同 prefix の既存 ID の最大連番 + 1 を採番する。
- story: `bd-story` → `bd-story-001`
- task: `bd-task` → `bd-task-001`
- subtask: `bd-subtask-<kind>` → `bd-subtask-implement-001`
- finding: `finding` → `finding-001`

採番は `bd list --type <type> --all` の既存 ID から正規表現で最大連番を探す。
スキーマ ID と bd ID を一致させるため `create --id <id> --force` で明示指定する。
