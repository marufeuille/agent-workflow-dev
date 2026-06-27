# Reviewer 設計仕様

## 概要・責務

Reviewer は、Implementer が作成した PR（task branch → story branch）を、**コードを直接修正せずに**検証する Claude Code subagent である。主な責務は以下の4つ。

1. review 対象の PR と関連データを取得する
2. PR を `planned_pr_scope` と `acceptance_refs` に対してレビューする
3. 問題があれば構造化された `review_finding` を作成する
4. 次の状態（fix subtask 生成 / review subtask close / phase 進行）を決める

Reviewer は **判断と指摘のみ**を行い、修正は Fixer に委ねる。これにより「レビューする者が修正しない」という役割分担を担保する（TODO大項目11・16より）。

## 入力（読み取るもの）

- **review subtask**: `status=ready` かつ `kind=review` の `beads_subtask`（画像より）
- **parent beads_task**: その subtask の親タスク。ここから PR 番号（`pr_number`）と PR 差分を取得する（画像より）
- **PR 差分**: parent beads_task に紐づく PR の files-changed / diff（画像より）
- **Shortcut Story の acceptance criteria**: 受け入れ基準。`beads_task.acceptance_refs` と照合する（画像より）
- **planned_pr_scope**: その PR で変更されるべきファイル範囲。差分が scope 内に収まっているか確認する（画像より）

## 出力・成果物

Reviewer は **直接コード修正を行わない**。成果物は以下のいずれか。

- **review_finding の作成**: 問題があれば `severity / category / file / line / description / suggested_fix` を持つ finding を作成（画像より）
  - severity は `must_fix / should_fix / nit / question` を区別する（画像より）
- **PR コメントの投稿**: 必要なら PR にコメントを投稿する（画像より）
- **review subtask の close**: 問題がなければ review subtask を closed にする（画像より）
- **fix subtask の生成**: `must_fix` がある場合、`kind=fix` の subtask を作成して ready にする（画像より）
- **beads_task.current_phase の進行**: 全 finding が解消済みなら `verified` へ進める（画像より）

### reviewer_output の構造（画像より）

```yaml
decision: "changes_requested"  # approved | changes_requested | comment_only | blocked
findings:
  - id: finding-001
    severity: "must_fix"
    category: "test"
    file: "app/api/saved_filters.py"
    line: 82
    description: "Missing validation for empty filter name."
    suggested_fix: "Return 400 when name is empty."
    status: "open"
next_subtasks:
  - kind: "fix"
    input_refs:
      review_finding_ids:
        - finding-001
```

`decision` は `approved / changes_requested / comment_only / blocked` のいずれか（画像より）。

## 利用コマンド（wrapper CLI）

> 画像内にコマンド名の明記は無し（画像から不明）。以下は TODO.md の wrapper CLI 仕様（大項目9・10）から補完。

- `bin/bdw ready --role reviewer --json` — ready な review subtask を取得（TODO.mdより）
- `bin/bdw finding create --file <finding.yaml> --json` — review_finding を作成（TODO.mdより）
- `bin/bdw finding list --task <task-id> --open --json` — open finding を一覧（TODO.mdより）
- `bin/bdw close <subtask-id> --output <file>` — review subtask を close（TODO.mdより）
- `bin/bdw subtask create --file <subtask.yaml> --json` — fix subtask を生成（TODO.mdより）
- `bin/ghw pr view <number> --json` — PR 情報と差分を取得（TODO.mdより）
- `bin/ghw pr comment <number> --file <file>` — PR にコメント投稿（TODO.mdより）
- `bin/ghw pr checks <number> --json` — PR の CI 状態を取得（TODO.mdより）
- `bin/sc-story get <story-id> --json` — Shortcut Story の acceptance criteria を参照（TODO.mdより）

## データモデルの動き

```
beads_task (PR粒度, pr_number 紐付き)
  └─ beads_subtask (kind=review, status=ready)  ← Reviewer が取得
        │
        ▼  PR差分 / acceptance_refs / planned_pr_scope を照合
  ┌─────────────┴─────────────┐
  │ 問題あり                    │ 問題なし
  ▼                            ▼
review_finding (status=open)    review subtask → closed
  severity: must_fix 等         beads_task.current_phase → verified
  ▼ (must_fix の場合)
beads_subtask (kind=fix, status=ready)  ← Fixer へ引き継ぎ
```

主なデータモデル（画像・TODO大項目7より）:
- **beads_task**: PR 粒度の作業単位。`pr_number` / `acceptance_refs` / `planned_pr_scope` / `current_phase` を持つ
- **beads_subtask**: agent 実行単位。`kind`（implement/review/fix/verify/summarize）と `status`（ready/closed）を持つ
- **review_finding**: review subtask から生まれる構造化された指摘。`severity / category / file / line / description / suggested_fix / status` を持つ
- **planned_pr_task / planned_pr_scope**: その PR で想定される変更ファイル群。scope 外の変更は finding 対象

## シーケンス / 処理フロー

画像に描かれた Reviewer の責務（左ボックス、番号付きステップ）を忠実に再現。

1. **review 対象を取得する**
   - `status=ready` かつ `kind=review` の `beads_subtask` を取得する
   - parent の `beads_task` で PR を読む
   - Shortcut Story の acceptance criteria と `beads_task.acceptance_refs` を確認する
2. **PR をレビューする**
   - `planned_pr_scope` に収まっているか確認する
   - `acceptance_refs` に対応する条件を満たしているか確認する
   - テスト、設計、セキュリティ、後方互換性、可読性を確認する
   - out of scope な指摘は `must_fix` にしない
3. **review_finding を作成する**
   - 問題があれば `severity / category / file / line / description / suggested_fix` を持つ finding を作る
   - `must_fix / should_fix / nit / question` を区別する
   - 必要なら PR コメントも投稿する
4. **次の状態を決める**
   - `must_fix` があれば fix subtask を作成し、ready にする
   - `must_fix` がなければ review subtask を closed にする
   - 全 finding が解消済みなら `beads_task.current_phase` を `verified` へ進める

処理の流れは **左から右** へ。左ボックス（Reviewer の責務・4ステップ）を実行した結果として、右ボックス（`reviewer_output`）が生成される（画像より）。

## 成功条件

TODO大項目16「Reviewer の検証環境」を反映。

- review subtask を用意できること
- Reviewer が PR を取得できること
- Reviewer が Shortcut Story の acceptance criteria を参照できること
- Reviewer が `planned_pr_scope` に対して差分を確認できること
- 問題がない場合に review subtask を closed にできること
- 問題がある場合に `review_finding` を作成できること
- `must_fix` finding がある場合に fix subtask を作成できること
- Reviewer が直接コード修正しないこと（TODO.mdより）

## 禁止事項・セーフティ

- **直接コード修正禁止**: Reviewer はコードを変更せず、指摘はすべて `review_finding` として記録する（画像・TODO大項目11・16より）
- **main への PR / merge 禁止**: PR は story branch 宛てのみ（TODO大項目3・11より）
- **Shortcut Story を Done にしない**: Done 判断は人間のみ（TODO大項目0・11より）
- **out of scope を must_fix にしない**: scope 外の指摘は `must_fix` にせず、より軽い severity で扱う（画像より）
- **expected_files 外の変更を検出したら finding を出す**: `planned_pr_scope` / expected_files に無い変更があれば指摘する（TODO大項目20より）
- **schema validation 失敗の出力は登録しない**: 不正な finding は破棄する（TODO大項目20より）

## TODO.md該当項目

- **大項目11「Claude Code 共通ルール」**: Reviewer は直接修正せず `review_finding` を作る（禁止事項の根拠）
- **大項目12「Claude Code subagent」**: `reviewer.md` を作成。read/write 対象・禁止事項・利用 wrapper CLI を明記
- **大項目16「Reviewer の検証環境」**: 本設計の成功条件の直接の根拠
- **大項目20「セーフティガード」**: expected_files 外の変更で finding を出す、schema validation の扱い
- **大項目9「beads wrapper CLI」**: `bin/bdw finding create/list`、`ready`、`close`、`subtask create`
- **大項目10「GitHub wrapper CLI」**: `bin/ghw pr view/comment/checks`
- **大項目8「Shortcut wrapper CLI」**: `bin/sc-story get`（acceptance criteria 参照）
- **大項目7「データスキーマ」**: `review_finding` schema の定義
