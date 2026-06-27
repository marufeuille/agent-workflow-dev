# Implementer 設計仕様

## 概要・責務
ready な implement subtask を取り、planned_pr_scope 内で実装し、task branch から story branch 宛てに PR を作成する。実装後は beads_task に pr_number を記録し、implement subtask を closed にして、次の review subtask を ready 化する。本エージェントはコード変更の実行主体であり、スコープ外の変更・main 直接 PR・複数 task の混在を行わない。

## 入力（読み取るもの）
画像では `implementer_input` として以下が定義されている。

- `beads_subtask_id`: `bd-subtask-implement-001`（ready な kind=implement の beads_subtask。`bin/bdw ready --role implement` で取得）
- `parent_task`:
  - `id`: `bd-task-001`（parent beads_task。planned_pr_scope / acceptance_refs / expected_files / branch_name を持つ）
- `shortcut_story_id`: `sc-123`
- `planned_pr_scope`: `"Backend API and persistence only; UI changes are out of scope."`
- `acceptance_refs`: `["AC-1", "AC-2"]`
- `expected_files`:
  - `"app/api/*"`
  - `"app/models/*"`
  - `"tests/api/*"`
- `branch_name`: `"agent/sc-123-saved-filters-api"`

補足（TODO.mdより）:
- 入力取得は `bin/bdw ready --role implement` で行う（TODO大項目15・9）。
- parent beads_task は `planned_pr_scope`, `expected_files`, `acceptance_refs` を保持する（TODO大項目7・15）。

## 出力・成果物
画像では `implementer_output` として以下が定義されている。

- `status`: `"implemented"`
- `pr_number`: `456`
- `commit_shas`:
  - `abc123`
- `changed_files`:
  - `"app/saved_filters.py"`
  - `"tests/api/test_saved_filters.py"`
- `next_subtask`:
  - `kind`: `"review"`

TODO.md（大項目15）で確認すべき成果物:
- コード実装（planned_pr_scope 内）
- task branch（`bin/ghw branch create-task`）
- story branch 宛ての PR（`bin/ghw pr create`）
- PR description（Shortcut Story ID / beads_task ID / acceptance_refs / scope を記載）
- beads_task への pr_number 記録（`bin/bdw task link-pr`）
- implement subtask の close（`bin/bdw close`）
- review subtask の ready 化（または未作成なら作成）

## 利用コマンド（wrapper CLI）
画像に明示的なコマンド表記はないため、TODO.md（大項目9・10・15）より補完。

- `bin/bdw ready --role implement --json`
  - ready な implement subtask を取得
- `bin/ghw branch create-task <story-id> <task-slug> --from <story-branch>`
  - task branch を作成（画像の branch_name 例: `agent/sc-123-saved-filters-api`）
- `bin/ghw pr create --base <story-branch> --head <task-branch> --body <file>`
  - story branch 宛てに PR を作成
- `bin/bdw task link-pr <task-id> --pr <number>`
  - beads_task.pr_numbers に PR 番号を記録
- `bin/bdw close <subtask-id> --output <file>`
  - implement subtask を closed にする
- `bin/bdw subtask create --file <subtask.yaml> --json`（TODO.md大項目9より）
  - 次の review subtask が未作成の場合に作成

## データモデルの動き
- beads_subtask（kind=implement, status=ready）→（実装後）status=closed
- beads_task（parent）→ `pr_numbers` に PR 番号を追加
- beads_subtask（kind=review, 次工程）→ status=ready 化（未作成なら新規作成）
- Shortcut Story: Implementer は State を直接変更しない（TODO.md大項目11・20より）。`acceptance_refs` は PR description に記載するだけであり、State 遷移は行わない。
- PR: task branch（例: `agent/sc-123-saved-filters-api`）→ story branch を base に作成。main には直接向かない（TODO.md大項目19・20より）。

データ構造の概念（TODO.md大項目7より）:
- `beads_subtask`: agent 実行単位（implement / review / fix / verify / summarize）
- `beads_task`: PR 粒度の作業単位。作成時点では planned PR、PR 作成後に pr_number と紐付く
- `planned_pr_task`: StoryPlanner が作る beads_task の下書き

## シーケンス / 処理フロー
画像の「Implementer の責務」は 4 ステップで構成される。以下、画像の番号付けを忠実に再現する。

1. **実行対象を取得する**
   - `status=ready` の `kind=implement` の beads_subtask を取得する（`bin/bdw ready --role implement`）
   - parent の beads_task を読み、`planned_pr_scope` / `acceptance_refs` / `expected_files` / `branch_name` を確認する
   - 依存する subtask / task が完了していることを確認する

2. **実装する**
   - beads_task の `planned_pr_scope` 内でコード・テスト・ドキュメントを変更する
   - out of scope に含まれる変更を行わない（画像では明確に「out of scope に含まれる変更を行わない」と記載）
   - 必要に応じて commit しながら作業する

3. **Pull Request を作成・更新する**
   - PR が未作成なら branch を作成し（`bin/ghw branch create-task`）、PR を作る（`bin/ghw pr create`）
   - PR description に Shortcut Story ID / beads_task ID / acceptance_refs / scope を記載する
   - 既存 PR がある場合は、その PR に commit を追加する（Fixer とは異なり、Implementer は新規 PR 作成が主だが既存 PR 更新も扱う）

4. **beads を更新する**
   - `beads_task.pr_numbers` に PR 番号を記録する（`bin/bdw task link-pr`）
   - implement subtask を closed にする（`bin/bdw close`）
   - 次の review subtask を ready にする、または未作成なら作成する（`bin/bdw subtask create`）

処理完了後、出力（`implementer_output`）として `status=implemented`, `pr_number`, `commit_shas`, `changed_files`, `next_subtask.kind=review` を返す。

## 成功条件
TODO.md大項目15「Implementer の検証環境」より。すべて満たすことをもって成功とする。

- ready な implement subtask を用意・取得できること
- Implementer が parent beads_task を読めること
- Implementer が `planned_pr_scope` を守ること（スコープ内に収まること）
- task branch が作成されること（`bin/ghw branch create-task`）
- story branch 宛てに PR が作成されること（task PR の base が story branch になること。TODO大項目19）
- PR description に Shortcut Story ID / beads_task ID / acceptance_refs が入ること
- beads_task に pr_number が記録されること（`bin/bdw task link-pr`）
- implement subtask が closed になること（`bin/bdw close`）
- review subtask が ready になること（次工程への引き継ぎ）

## 禁止事項・セーフティ
画像の「out of scope に含まれる変更を行わない」に加え、TODO.md（大項目11・19・20）より以下を禁止する。

- **scope 外変更の禁止**: `planned_pr_scope` と `expected_files` の範囲外に触れない（画像に明記）
- **main 直接 PR の禁止**: PR の base は必ず story branch とし、main に直接向かわない（TODO大項目19・20）。`bin/ghw` は main への直接 PR 作成をデフォルト禁止する。
- **main merge の禁止**: AI agent は main に merge しない（TODO大項目11・20）
- **複数 task の混在禁止**: 1つの task branch / PR には1つの beads_task の範囲のみを含める（PR 粒度 = beads_task。TODO大項目7・6）
- **Shortcut Story の Done 化禁止**: Implementer は Shortcut Story の State を変更しない（Done には特にしない）。人間のみが Done にできる（TODO大項目0・11・20）
- **依存未完了での実装禁止**: 依存する subtask / task が完了していることを確認してから実装する（画像ステップ1）
- **schema validation 失敗時の扱い**: validation に失敗した出力は beads に登録しない（TODO大項目20）

## TODO.md該当項目
- 大項目12「Claude Code subagent を作成する」（`implementer.md` の作成、read/write 対象・禁止事項・wrapper CLI の明記）
- 大項目15「Implementer の検証環境を作成する」（本設計の検証項目の直接のソース）
- 大項目19「branch 戦略の検証」（task branch 作成・task PR の base が story branch・main 直接 PR 禁止・story branch への集約）
- 関連: 大項目9「beads wrapper CLI」・大項目10「GitHub wrapper CLI」（利用コマンドの定義元）
- 関連: 大項目7「データスキーマを定義する」（beads_task / beads_subtask / planned_pr_task の構造）
- 関連: 大項目11「Claude Code 共通ルール」・大項目20「セーフティガード」（禁止事項のソース）
