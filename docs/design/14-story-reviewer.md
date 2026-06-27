# StoryReviewer 設計仕様

## 概要・責務
Shortcut Story に紐づく `beads_story` 配下の全 beads_task / beads_subtask / review_finding を集約し、各 PR の open/merged/CI 状態を取得して、acceptance criteria ごとの充足判定を行う。すべてのゲート条件（open must_fix finding がないこと・必要な PR が merge 済みであること・CI が通っていること）が揃った場合のみ、Shortcut Story の State を **In Review** に更新し、人間向けの summary コメントを投稿する。**Done には絶対にしない。** final PR（story branch → main）の merge も人間のみが行う。StoryReviewer は Story 全体の受け入れレビューに進めるかどうかの「門番」であり、最終的な Done 判断は人間が行う（TODO.md大項目0・11・18・23より）。

## 入力（読み取るもの）
画像では `story_reviewer_input` として、beads_story 配下の状態と PR/Shortcut 情報を集約したデータ構造が定義されている。

- `beads_story_id`: 対象となる beads_story（Shortcut Story と `bin/sc-story link` で紐付き済み）
- `shortcut_story_id`: 例 `sc-123`（`bin/sc-story get <story-id> --json` で取得）
- `acceptance_criteria`: Shortcut Story に人間が記述した受け入れ基準のリスト（例 `AC-1`, `AC-2`, …。各 beads_task の `acceptance_refs` がどの AC をカバーするかを示す）
- `tasks`: beads_story 直下の全 beads_task の配列。各 task は以下を持つ:
  - `id` / `title`
  - `pr_numbers`: 紐付く PR 番号（`bin/bdw task` より）
  - `subtasks`: 配下の beads_subtask（`kind`: implement / review / fix / verify / summarize、`status`: ready / in_progress / closed）
  - `findings`: 当該 task で発生した review_finding（`severity`: must_fix / should_fix、`status`: open / fixed）
- `prs`: 各 PR の状態（`bin/ghw pr view <number> --json`, `bin/ghw pr checks <number> --json` より）
  - `number`, `state`（open / merged / closed）
  - `ci_status`（success / failure / pending）
  - `base` / `head`（base が story branch であることの確認）

補足（TODO.mdより）:
- beads_task / beads_subtask / review_finding の集約は `bin/bdw finding list --task <task-id> --open --json` などを用いて行う（TODO大項目9・18）。
- acceptance criteria は Shortcut Story 本文に記述されたものを `bin/sc-story get` で取得する（TODO大項目2・8）。
- 画像に書かれた具体的なフィールド名の一部は（画像から不明）の箇所があり、上記は schema 名 `story_review_summary.schema.json`（TODO大項目7）と TODO大項目18 の検証項目から補完した。

## 出力・成果物
画像では `story_reviewer_output` として、acceptance criteria ごとの充足判定と Shortcut への反映結果が定義される。

- `story_review_summary`: schema（`story_review_summary.schema.json`）準拠の構造化サマリ。以下を含む（TODO大項目7・18より）:
  - acceptance criteria ごとの充足判定（`satisfied` true/false と根拠 `evidence`）
  - 全 beads_task / subtask の完了状況
  - open な review_finding の有無と件数
  - 各 PR の merge/CI 状態
  - Story 全体が In Review 可能かの総合判定 `ready_for_review`
- **Shortcut Story の State 更新**: ゲート条件を満たした場合のみ `In Review` にする（`bin/sc-story set-state <story-id> "In Review"`）。**Done にはしない。**
- **人間向け summary コメント**: `story_review_summary` を整形したものを Shortcut Story に投稿（`bin/sc-story comment <story-id> --file <path>`）。

TODO.md（大項目18・23）で確認すべき成果物:
- beads_task / beads_subtask / review_finding を集約できること
- PR の open / merged / CI 状態を取得できること
- acceptance criteria ごとの充足状況を判定できること
- 条件が揃った場合に Shortcut Story を In Review にできること
- 人間向け summary コメントが Shortcut に投稿されること

## 利用コマンド（wrapper CLI）
画像に明示的なコマンド表記の一部は（画像から不明）。TODO.md（大項目8・9・10・18）より補完する。

- `bin/sc-story get <story-id> --json`
  - Shortcut Story を取得し、acceptance criteria と beads_story_id の紐付きを確認
- `bin/sc-story set-state <story-id> "In Review"`
  - ゲート通過時に State を In Review に更新（Done への更新は `bin/sc-story` がデフォルト禁止: TODO大項目20）
- `bin/sc-story comment <story-id> --file <path>`
  - 人間向け summary コメントを投稿
- `bin/bdw finding list --task <task-id> --open --json`
  - open な review_finding（must_fix 含む）を一覧し、ゲート判定に用いる
- `bin/bdw` 関連（TODO大項目9より）: beads_story 配下の task / subtask を再帰的に取得し、集約に用いる
- `bin/ghw pr view <number> --json`
  - PR の state（open/merged）と base/head を取得
- `bin/ghw pr checks <number> --json`
  - PR の CI 状態を取得

## データモデルの動き
- **beads_story**: 集約のルート。Shortcut Story と1:1に紐付く（TODO大項目7）。
- **beads_task**: PR 粒度の作業単位。StoryReviewer は各 task の `pr_numbers` を辿り、PR 状態を確認する。
- **beads_subtask**: agent 実行単位（implement / review / fix / verify / summarize）。すべての subtask が `closed` であることが、task 完了の前提。
- **review_finding**: review subtask から生まれる構造化された指摘。`severity=must_fix` かつ `status=open` の finding が1件でもあるとゲート不通過（TODO大項目18）。
- **PR**: task branch → story branch 宛て。StoryReviewer は各 PR の `state=merged` と `ci_status=success` を確認する。final PR（story branch → main）の存在・merge 可否も確認対象だが、**merge は人間のみ**（TODO大項目19）。
- **Shortcut Story**: ゲート通過時にのみ State が `In Review` に遷移する。`Done` への遷移は AI agent には禁止（TODO大項目0・11・20）。

データ構造の概念（TODO大項目7より）:
- `story_review_summary`: StoryReviewer が生成する、Story 全体の受け入れ状態を表す構造化成果物。`story_review_summary.schema.json` で検証する。

## シーケンス / 処理フロー
画像の「StoryReviewer の責務」は複数ステップの集約→判定→反映の流れで構成される。以下、画像の番号付けを忠実に再現する（一部の細かい表記は（画像から不明）のため TODO大項目18 で補完）。

1. **対象 Story を特定する**
   - Shortcut Story ID を受け取り、紐付く `beads_story_id` を確認する（`bin/sc-story get`）
   - Shortcut Story の acceptance criteria を取得する

2. **beads_story 配下を集約する**
   - beads_story 直下の全 beads_task を取得する
   - 各 task の beads_subtask（kind / status）と review_finding（severity / status）を再帰的に集約する（`bin/bdw finding list --open` 等）
   - すべての task が「全 subtask closed」であることを確認する

3. **PR 状態を取得する**
   - 各 task の `pr_numbers` から PR を特定し、`bin/ghw pr view` / `bin/ghw pr checks` で state（open/merged）と CI 状態を取得する
   - final PR（story branch → main）の有無と状態も確認する（merge は行わない）

4. **acceptance criteria ごとの充足判定を行う**
   - 各 acceptance criteria について、それをカバーする beads_task（`acceptance_refs`）が完了し、対応 PR が merge 済みかを判定する
   - 判定結果と根拠（evidence）を記録する

5. **ゲート条件を評価する（In Review にしてよいか）**
   - open な `must_fix` finding が1件でもあれば **ブロック**（TODO大項目18）
   - 必要な PR が未 merge であれば **ブロック**（TODO大項目18）
   - CI が失敗/pending であれば **ブロック**
   - いずれかの acceptance criteria が未充足であれば **ブロック**

6. **ゲート通過時のみ Shortcut に反映する**
   - Shortcut Story の State を `In Review` に更新する（`bin/sc-story set-state`）。**Done にはしない。**
   - `story_review_summary` を schema 準拠で生成し、人間向け summary コメントとして Shortcut に投稿する（`bin/sc-story comment`）

7. **（ゲート不通過時）現状サマリを投稿して終了する**
   - State は更新せず、現在の阻害要因（open finding / 未 merge PR / 未達成 AC）を summary コメントとして投稿し、人間または他 agent の対応に委ねる

処理完了後、出力（`story_reviewer_output`）として `ready_for_review`, acceptance criteria ごとの充足判定, open finding 件数, PR 状態サマリを返す。

## 成功条件（＋In Review にするためのゲート条件）
TODO.md大項目18「StoryReviewer の検証環境」および大項目23「初期 MVP の完了条件」より。

検証項目（すべて満たすことをもって成功とする）:
- Shortcut Story に紐づく beads_story を用意できること
- beads_task / beads_subtask / review_finding を集約できること
- PR の open / merged / CI 状態を取得できること
- acceptance criteria ごとの充足状況を判定できること
- 条件が揃った場合に Shortcut Story を In Review にできること
- 人間向け summary コメントが Shortcut に投稿されること

**In Review にするためのゲート条件**（いずれかを満たさない場合は In Review にしない）:
- open な `must_fix` finding が0件であること（TODO大項目18）
- 必要な全 PR が merge 済みであること（TODO大項目18）
- CI がすべて success であること
- すべての acceptance criteria が充足判定されること
- すべての beads_subtask が closed であること

MVP 完了条件の関連項目（TODO大項目23）:
- Story 全体の状態を Shortcut に summary として戻せること
- AI agent が Shortcut Story を Done にしないこと
- AI agent が main に merge しないこと
- 人間が Shortcut 上で最終 Done 判断できること

## 禁止事項・セーフティ
画像に記載のゲート条件に加え、TODO.md（大項目0・11・19・20）より以下を禁止する。

- **Shortcut Done の禁止**: StoryReviewer は State を `In Review` までしか上げない。`Done` への更新は `bin/sc-story` がデフォルト禁止とし、AI agent が試みた場合はエラーにする（TODO大項目0・11・20）。Done 判断は人間のみ（TODO大項目23）。
- **final PR merge の禁止**: story branch → main の final PR の merge は人間のみが行う。AI agent は merge しない（TODO大項目19・20）。`bin/ghw` は main への merge を禁止する。
- **open must_fix finding 存在時の In Review 化禁止**: open な `must_fix` finding がある場合は State を更新しない（TODO大項目18）。
- **未 merge PR 存在時の In Review 化禁止**: 必要な PR が未 merge の場合は State を更新しない（TODO大項目18）。
- **main 直接操作の禁止**: main への直接 PR 作成・merge を行わない（TODO大項目19・20）。
- **schema validation 失敗時の扱い**: validation に失敗した `story_review_summary` は登録・投稿しない（TODO大項目20）。
- **コード修正の禁止**: StoryReviewer は実装・修正を行わず、状態集約と Shortcut 反映のみを行う（レビュー/門番の役割）。

## TODO.md該当項目
- 大項目12「Claude Code subagent を作成する」（`story-reviewer.md` の作成、read/write 対象・禁止事項・wrapper CLI の明記）
- 大項目18「StoryReviewer の検証環境を作る」（本設計の検証項目・ゲート条件の直接のソース）
- 大項目19「branch 戦略の検証」（story branch の状態確認・final PR が story branch から main・final PR merge は人間のみ）
- 大項目23「初期 MVP の完了条件」（Story 全体の状態を Shortcut に summary として戻す・Done にしない・main に merge しない・人間が最終 Done 判断）
- 関連: 大項目8「Shortcut wrapper CLI」・大項目9「beads wrapper CLI」・大項目10「GitHub wrapper CLI」（利用コマンドの定義元）
- 関連: 大項目7「データスキーマを定義する」（`story_review_summary.schema.json` の構造）
- 関連: 大項目11「Claude Code 共通ルール」・大項目20「セーフティガード」（禁止事項のソース）
- 関連: 大項目0「前提確認」（Done は人間のみ・AI は main に merge しないのルール）
