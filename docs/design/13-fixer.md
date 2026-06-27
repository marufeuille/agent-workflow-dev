# Fixer 設計仕様

## 概要・責務

Fixer は、Reviewer が出した **open な `review_finding`（must_fix 等）の範囲だけを修正する** Claude Code subagent である。主な責務は以下の3つ。

1. fix 対象の finding と関連データを取得する
2. finding の `suggested_fix` と `planned_pr_scope` に沿って修正する
3. beads（finding / subtask / commit 参照）を更新し、再 review へ引き継ぐ

Fixer は finding の範囲を超えない最小限の修正を行い、既存 PR に commit を追加したあと、再 review subtask を ready にして Reviewer に差し戻す（TODO大項目11・17より）。

## 入力（読み取るもの）

- **fix subtask**: `status=ready` かつ `kind=fix` の `beads_subtask`（画像より）
- **open review_finding**: `input_refs.review_finding_ids` に列挙された open な finding を読む（画像より）
  - 各 finding の `suggested_fix` を修正方針として使う（画像より）
- **parent beads_task と PR**: 親タスクと、そこに紐づく既存 PR を確認する（画像より）
- **planned_pr_scope**: 修正が PR の想定スコープに収まっているか確認する（画像より）

## 出力・成果物

- **既存 PR への追加 commit**: 原則として新規 PR は作らず、既存 PR に commit を追加する（画像より）
- **finding の fixed 化**: 対応する `review_finding` を `fixed` にする（画像より）
- **fix subtask の close**: 処理完了後、fix subtask を `closed` にする（画像より）
- **再 review subtask の生成/ready**: `kind=review` の subtask を作成、または ready にする（画像より）
- **commit 参照の記録**: 修正 commit を `output_refs.commit_sha` に記録する（画像より）

### fixer_output の構造（画像より）

```yaml
status: "fixed"
fixed_findings:
  - finding-001
commit_shas:
  - def456
next_subtasks:
  - kind: 'review'
    instructions: "Re-review the PR after fixes for finding-001."
```

## 利用コマンド（wrapper CLI）

> 画像内にコマンド名の明記は無し（画像から不明）。以下は TODO.md の wrapper CLI 仕様（大項目9・10）から補完。

- `bin/bdw ready --role fixer --json` — ready な fix subtask を取得（TODO.mdより）
- `bin/bdw close <subtask-id> --output <file>` — fix subtask を close（TODO.mdより）
- `bin/bdw subtask create --file <subtask.yaml> --json` — 再 review subtask を生成（TODO.mdより）
- `bin/bdw finding list --task <task-id> --open --json` — open finding を参照（TODO.mdより）
- `bin/bdw finding update <finding-id> --status fixed` — finding を fixed 化（TODO.mdより。`bin/bdw finding` の更新操作）
- `bin/ghw pr comment <number> --file <file>` — 修正内容を PR コメントで通知（TODO.mdより）
- 既存 PR ブランチへの commit 追加は git 操作（task branch 上で commit → push）。新規 PR 作成は行わない（TODO大項目10・19より）

## データモデルの動き

```
beads_task (PR粒度, pr_number 紐付き)
  └─ beads_subtask (kind=fix, status=ready)  ← Fixer が取得
        │  input_refs.review_finding_ids → open findings を読む
        ▼  suggested_fix + planned_pr_scope に沿って修正
  既存 PR へ commit 追加 (output_refs.commit_sha に記録)
        │
        ▼  beads を更新
  review_finding  ─ status: open → fixed
  fix subtask     ─ status: ready → closed
  beads_subtask (kind=review, status=ready)  ← 再 review へ引き継ぎ（Reviewer に差し戻し）
```

主なデータモデル（画像・TODO大項目7より）:
- **beads_task**: PR 粒度の作業単位。`pr_number` / `planned_pr_scope` を持つ
- **beads_subtask**: agent 実行単位。fix subtask は `kind=fix`。`input_refs.review_finding_ids` で対象 finding を受渡し、`output_refs.commit_sha` で成果 commit を記録する
- **review_finding**: Reviewer が作成した指摘。Fixer は `status` を `open → fixed` に更新する。`suggested_fix` を修正方針として使う
- **PR**: 既存の task PR。新規作成せず commit を追加する

## シーケンス / 処理フロー

画像に描かれた Fixer の責務（左ボックス、番号付きステップ）を忠実に再現。

1. **fix 対象を取得する**
   - `status=ready` から `kind=fix` の `beads_subtask` を取得する
   - `input_refs.review_finding_ids` にある open finding を読む
   - parent の `beads_task` と PR を確認する
2. **指摘を修正する**
   - finding の `suggested_fix` と `planned_pr_scope` に沿って修正する
   - 原則として既存 PR に commit を追加する
   - finding の範囲を超える大きな変更は行わない
3. **beads を更新する**
   - 修正 commit を `output_refs.commit_sha` に記録する
   - 対応する `review_finding` を `fixed` にする
   - fix subtask を `closed` にする
   - 再 review subtask を作成または ready にする

処理の流れは **左から右** へ。左ボックス（Fixer の責務・3ステップ）を実行した結果として、右ボックス（`fixer_output`）が生成される（画像より）。画像に明示的な分岐（if/else）は無く、線形な3ステップ（画像より）。

## 成功条件

TODO大項目17「Fixer の検証環境」を反映。

- open な `review_finding` を用意できること
- fix subtask を ready にできること
- Fixer が finding の範囲だけ修正すること
- 既存 PR に commit を追加できること
- finding が `fixed` になること
- fix subtask が `closed` になること
- 再 review subtask が ready になること
- finding の範囲外の大きな変更を行わないこと（TODO.mdより）

## 禁止事項・セーフティ

- **finding 範囲外の大きな変更禁止**: `suggested_fix` と `planned_pr_scope` の範囲だけを修正する（画像より）
- **新規 PR 作成は原則行わない**: 既存 PR に commit を追加する（画像より）
- **main への PR / merge 禁止**: PR は story branch 宛てのみ（TODO大項目3・11より）
- **Shortcut Story を Done にしない**: Done 判断は人間のみ（TODO大項目0・11より）
- **planned_pr_scope 外への拡張禁止**: スコープを超える修正が必要な場合は、新たな finding / タスクとして切り出す（TODO大項目20より）
- **schema validation 失敗の出力は登録しない**: 不正な更新結果は破棄する（TODO大項目20より）

## TODO.md該当項目

- **大項目11「Claude Code 共通ルール」**: Fixer は open finding の範囲だけ修正する（責務の根拠）
- **大項目12「Claude Code subagent」**: `fixer.md` を作成。read/write 対象・禁止事項・利用 wrapper CLI を明記
- **大項目17「Fixer の検証環境」**: 本設計の成功条件の直接の根拠
- **大項目20「セーフティガード」**: planned_pr_scope 外の変更禁止、schema validation の扱い
- **大項目9「beads wrapper CLI」**: `bin/bdw ready`、`close`、`subtask create`、`finding list/update`
- **大項目10「GitHub wrapper CLI」**: `bin/ghw pr comment`（既存 PR への通知）
- **大項目7「データスキーマ」**: `review_finding` schema（status 遷移）、`beads_subtask` schema（input_refs / output_refs）
- **大項目19「branch 戦略の検証」**: task PR の base が story branch であることの確認
