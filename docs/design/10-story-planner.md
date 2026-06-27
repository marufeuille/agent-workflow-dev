# StoryPlanner 設計仕様

## 概要・責務

StoryPlanner は、人間が合意した成果単位である **Shortcut Story** を受け取り、それを「人間がレビューしやすい PR 粒度」の計画（`planned_pr_tasks`）へ分解した上で、実行グラフである **beads** に展開（materialize）し、最後に story branch を作成して Shortcut へ結果を提示する、ワークフローの起点エージェント。

本エージェントは実装・レビュー・修正そのものは行わず、後続エージェント（Implementer / Reviewer / Fixer）が作業可能な状態を整備することのみを責務とする。

画像（`docs/images/story_planner.excalidraw.png`）に記載された StoryPlanner の5つの責務:

1. **Shortcut Story を読む** — title / description / 完了条件 / 優先度 / state / Epic / コメントを取得し、計画可能な状態か確認する。不明点や矛盾がある場合は beads に展開せず、Shortcut 側に確認事項を提示する。
2. **Story を PR 粒度に分解する** — Story の完了条件を満たすのに必要な変更を洗い出し、人間がレビューしやすい PR 粒度に分割する。各 PR 粒度 task について scope / out of scope / 依存関係 / `acceptance_refs` を決める。
3. **`planned_pr_tasks` を作る** — `planned_pr_tasks` は beads_task の下書きであり、永続的なタスクではなく StoryPlanner の計画出力物。各 planned_pr_task は原則として 1 つの beads_task に materialize される。
4. **beads に materialize する** — beads_story root を作り、planned_pr_task ごとに beads_task を作り、beads_task の下に implement / review の初期 subtask を作り、task / subtask 間の依存関係を設定する。
5. **Shortcut に結果を提示する** — Story state を Planning または Doing に更新し、`beads_story_id` / 生成した task 一覧 / 想定 PR 粒度 / 未解決事項をコメントする。

## 入力（読み取るもの）

画像に記載された入力スキーマ `story_planner_input`:

- **Shortcut Story**（`bin/sc-story get` で取得）（TODO.md 大項目8より）
  - `id`（例: `sc-123`）、`title`、`description`
  - `acceptance_criteria`（例: `AC-1`「User can save a filter condition.」`AC-2`「User can list saved filters.」）
  - `priority`（例: `high`）、`state`（例: `Ready`）、`epic_id`（例: `epic-456`）
  - `comments`（例: 「Avoid changing the current search API response format.」など制約事項のメモ）
- **repository_context**
  - `repo`（例: `org/repo`）、`default_branch`（例: `main`）
  - `relevant_paths`（例: `app/api`, `app/models`, `tests/api`, `tests/models`）
- **`.ai-workflow/config.yaml` の `planning_policy`**（TODO.md 大項目6より）
  - `pr_granularity`: `reviewable_change_set`
  - `max_expected_prs`: `5`
  - `prefer_separate_refactor_pr`: `true`
  - `require_tests_per_pr`: `true`
  - `branch_strategy`: `story_branch`（TODO.md 大項目6より）

> 補足: 画像の `story_planner_input` には `branch_strategy` は含まれないが、`config.yaml` 上は planning_policy の一部として定義される（TODO.mdより）。

## 出力・成果物

画像に記載された出力スキーマ `story_planner_output`:

- **`decision`** — `materialize` / `needs_clarification` / `blocked` / `reject` のいずれか。`materialize` の場合のみ beads 展開・branch 作成を行う。
- **`planned_pr_tasks`**（`planned_pr_task.schema.json` に準拠 / TODO.md 大項目7より）
  - 各 task のフィールド: `title`, `planning_reason`, `planned_pr_scope`, `out_of_scope[]`, `acceptance_refs[]`, `expected_files[]`, `depends_on[]`, `initial_subtasks[]`
  - `initial_subtasks` は各 task につき `implement` / `review` を初期生成し、それぞれに `instructions` を持たせる
- **beads 成果物**（`bin/bdw` で生成 / TODO.md 大項目9より）
  - `beads_story`（title, shortcut_story_id, summary）
  - `planned_pr_task` ごとの `beads_task`
  - 各 beads_task 配下の初期 `beads_subtask`（implement / review）
- **story branch**（`bin/ghw branch create-story` で生成 / TODO.md 大項目10より）
- **Shortcut への更新**（`bin/sc-story set-state` / `comment` / `link` / TODO.md 大項目8より）
  - `next_state`（`Planning` / `Doing` / `Blocked`）
  - `comment_summary`（`beads_story_id`, 生成した task 一覧, 想定 PR 粒度, 未解決事項を含む planning summary）

画像例（`story_planner_output` 抜粋）:

```json
{
  "decision": "materialize",
  "beads_story": {
    "title": "Add saved filters",
    "shortcut_story_id": "sc-123",
    "summary": "Execution graph for saved filters story."
  },
  "planned_pr_tasks": [
    {
      "title": "Add saved filters persistence",
      "planning_reason": "Storage changes can be reviewed independently from API behavior.",
      "planned_pr_scope": "Migration and model layer for saved filters.",
      "out_of_scope": ["API endpoint changes", "UI changes"],
      "acceptance_refs": ["AC-1", "AC-2"],
      "expected_files": ["db/migrations/*", "app/models/*"],
      "depends_on": [],
      "initial_subtasks": [
        { "kind": "implement", "instructions": "Add migration and model layer." },
        { "kind": "review", "instructions": "Review schema, model behavior, and tests." }
      ]
    },
    {
      "title": "Add saved filters API",
      "planning_reason": "API behavior should be reviewed after persistence exists.",
      "planned_pr_scope": "Backend API endpoints and API tests.",
      "out_of_scope": ["UI changes"],
      "acceptance_refs": ["AC-1", "AC-2"],
      "expected_files": ["app/api/*", "tests/api/*"],
      "depends_on": "Add saved filters persistence",
      "initial_subtasks": [
        { "kind": "implement", "instructions": "Add create/list/delete endpoints." },
        { "kind": "review", "instructions": "Review API behavior against acceptance criteria." }
      ]
    }
  ],
  "shortcut_update": {
    "next_state": "Doing",
    "comment_summary": "Planned 2 PR-sized beads tasks for this story."
  }
}
```

## 利用コマンド（wrapper CLI）

> **注意**: 画像の図中には具体的な CLI コマンド名は記載されていない（画像から不明）。下記は TODO.md 大項目8/9/10 に基づくマッピング（TODO.mdより）。

### Shortcut 連携 — `bin/sc-story`（TODO.md 大項目8より）

| コマンド | 用途 |
| --- | --- |
| `bin/sc-story get <story-id> --json` | Shortcut Story を JSON 取得（入力 `shortcut_story` の情報源） |
| `bin/sc-story set-state <story-id> <state>` | Story state を Planning / Doing / Blocked へ更新（**Done は禁止**） |
| `bin/sc-story comment <story-id> --file <path>` | planning summary コメントを投稿 |
| `bin/sc-story link <story-id> --beads-story <beads-story-id>` | Shortcut Story に `beads_story_id` を記録 |

### beads 連携 — `bin/bdw`（TODO.md 大項目9より）

| コマンド | 用途 |
| --- | --- |
| `bin/bdw story create --shortcut-story <id> --title <title> --json` | beads_story root を作成 |
| `bin/bdw task create --file <planned-task.yaml> --json` | planned_pr_task から beads_task を作成（schema validation を含む） |
| `bin/bdw subtask create --file <subtask.yaml> --json` | implement / review の初期 subtask を作成 |
| `bin/bdw task link-pr <task-id> --pr <number>` | beads_task に PR 番号を記録（※StoryPlanner 自身は PR を作らないので、これは後続エージェントが使用） |

### GitHub 連携 — `bin/ghw`（TODO.md 大項目10より）

| コマンド | 用途 |
| --- | --- |
| `bin/ghw branch create-story <story-id> --from main` | story branch を `main` から作成 |

> StoryPlanner は PR 作成・merge を行わないため、`bin/ghw pr create` や `pr create-final`、merge 系コマンドは使用しない（TODO.md 大項目10・20より）。

## データモデルの動き

データの流れ（画像に描かれた `story_planner_input` → `planned_pr_tasks` → `story_planner_output` の変換と、beads 上の構造化）:

1. **beads_story を1つ作成**
   - Shortcut Story 1件に対して beads_story 1件（root）。`shortcut_story_id` で双方向リンク（Shortcut 側にも `beads_story_id` を記録）。

2. **planned PR ごとに beads_task を作成**
   - `planned_pr_task.schema.json` に準拠した各要素を beads_task として materialize（TODO.md 大項目7より）。
   - 各 beads_task には以下を設定:
     - `planned_pr_scope`: 当該 PR で変更する範囲の記述
     - `expected_files`: 変更を想定するファイルパス群（例: `db/migrations/*`, `app/models/*`, `app/api/*`, `tests/api/*`）。後続 Reviewer がスコープ外変更を検出するための基準になる（TODO.md 大項目20より）
     - `acceptance_refs`: その task が対応する acceptance criteria の ID リスト（例: `["AC-1", "AC-2"]`）
     - `out_of_scope`: 明示的に外す範囲
     - `depends_on`: 別 task への依存（例: API task は persistence task に依存）。task / subtask 間の依存関係を設定

3. **各 beads_task 配下に初期 subtask を2つ作成**
   - `implement` subtask（kind: implement, instructions 付き）
   - `review` subtask（kind: review, instructions 付き）

4. **materialize 後の beads 構造**（画像右下の例）

```
beads_story: "Add saved filters" (shortcut_story_id: sc-123)
├── beads_task[0]: "Add saved filters persistence"
│   ├── subtask: implement
│   └── subtask: review
└── beads_task[1]: "Add saved filters API"  (depends_on: task[0])
    ├── subtask: implement
    └── subtask: review
```

## シーケンス / 処理フロー

画像に書かれた5ステップの責務を、wrapper CLI と組み合わせた実行フロー（TODO.md 大項目8/9/10の CLI 定義に基づき具体化）:

1. **Story 取得・評価**
   - `bin/sc-story get <story-id> --json` で Shortcut Story を取得。
   - title / description / acceptance_criteria / priority / state / epic_id / comments を読む。
   - state が計画可能か（例: `Ready`）を判定。`Ready` 以外は基本的に対象外。
   - **不明点・矛盾がある場合は beads に展開せず、Shortcut 側に確認事項をコメントして `decision: needs_clarification` で終了。**

2. **Story の PR 粒度分解**
   - 完了条件（acceptance_criteria）を満たすのに必要な変更を洗い出す。
   - `planning_policy`（`reviewable_change_set`, `max_expected_prs: 5`, `prefer_separate_refactor_pr`, `require_tests_per_pr`）に従い、人間がレビューしやすい PR 粒度に分割。
   - 各 task の `planned_pr_scope` / `out_of_scope` / `depends_on` / `acceptance_refs` / `expected_files` を決定。

3. **`planned_pr_tasks` を作成**
   - `planned_pr_task.schema.json` に準拠した形で計画出力を組み立て（永続化は任意）。
   - schema validation を通ることを確認（TODO.md 大項目7・20より）。

4. **beads への materialize**
   - `bin/bdw story create` で beads_story root を作成。
   - 各 planned_pr_task について `bin/bdw task create --file <planned-task.yaml>` で beads_task を作成。
   - 各 beads_task 配下に `bin/bdw subtask create` で `implement` / `review` の初期 subtask を作成。
   - `depends_on` に従い task / subtask 間の依存関係を設定（先行 task の implement が終わらないと後続 task の implement が ready にならない、など）。

5. **story branch 作成**
   - `bin/ghw branch create-story <story-id> --from main` で story branch を作成（TODO.md 大項目10・19より）。

6. **Shortcut への結果提示**
   - `bin/sc-story link <story-id> --beads-story <beads-story-id>` で `beads_story_id` を記録。
   - `bin/sc-story set-state <story-id> {Planning|Doing|Blocked}` で state を更新（**Done は禁止**）。
   - `bin/sc-story comment <story-id> --file <path>` で planning summary コメントを投稿:
     - beads_story_id
     - 生成した task 一覧（title と想定 PR 粒度）
     - 未解決事項 / 確認事項

## 成功条件

TODO.md 大項目14「StoryPlanner の検証環境」のチェック項目を、StoryPlanner の受け入れ基準として反映（TODO.mdより）:

- [ ] Shortcut Story の fixture YAML を用意できること
- [ ] fixture から `planned_pr_tasks` を生成できること
- [ ] 生成した `planned_pr_tasks` が `planned_pr_task.schema.json` の schema validation を通ること
- [ ] `planned_pr_tasks` から beads_task を作成できること
- [ ] 初期 subtask として `implement` / `review` が各 task に作成されること
- [ ] story branch が `main` から作成されること
- [ ] Shortcut に planning summary コメントが投稿されること
- [ ] Story state が Planning / Doing へ遷移し、**Done にはならない**こと（TODO.md 大項目20・23より）
- [ ] MVP として `/story-plan <shortcut-story-id>`（TODO.md 大項目13より）で上記一連が実行できること（TODO.md 大項目21より）

## 禁止事項・セーフティ

画像の「その他」欄に明示された StoryPlanner のスコープ境界:

### StoryPlanner が write するもの（許可）

- Shortcut Story の state 遷移: `Ready` → `Planning` / `Doing` / `Blocked` のみ
- Shortcut Story への planning summary コメント
- beads_story
- 初期 beads_subtask（`implement` / `review`）
- task 間の依存関係
- story branch の作成

### StoryPlanner が write しないもの（禁止）

- **GitHub Pull Request**（PR 作成は Implementer / StoryReviewer の領域）
- **実装 commit**（Implementer の領域）
- **review commit / review_finding**（Reviewer の領域）
- **fix subtask**（Fixer の領域）
- **Shortcut Story の Done 判定**（人間のみ / TODO.md 大項目0・11・20より）
- **PR merge 判定**（人間のみ / TODO.md 大項目0・3・20より）

### セーフティガード（TODO.md 大項目20より）

- `bin/sc-story` で Done への state 更新はデフォルト禁止。AI agent が Done 更新を試みた場合はエラーにする。
- `bin/ghw` で main への直接 PR 作成・merge はデフォルト禁止。
- schema validation に失敗した `planned_pr_tasks` 出力は beads に登録しない。
- AI agent は main に直接 merge しない運用ルール（TODO.md 大項目0より）。
- Story branch 方式により、AI agent は Shortcut Story を Done にできない（人間だけが Done 判断 / TODO.md 大項目0・23より）。
- 入力 Shortcut Story の `comments` に含まれる制約（例: 「Avoid changing the current search API response format.」）を計画に反映し、`out_of_scope` 等で明示する。
- `planning_policy.max_expected_prs` を超える分解は避け、超える場合は確認事項として Shortcut に戻す。

## TODO.md該当項目

- **大項目6「workflow 設定ファイルを作る」** — `planning_policy`（pr_granularity, branch_strategy, max_expected_prs, prefer_separate_refactor_pr, require_tests_per_pr）の読み取り元
- **大項目7「データスキーマを定義する」** — `planned_pr_task.schema.json` への準拠、`beads_task` / `beads_subtask` schema、schema validation
- **大項目8「Shortcut wrapper CLI を作る」** — `bin/sc-story` の get / set-state / comment / link
- **大項目9「beads wrapper CLI を作る」** — `bin/bdw` の story create / task create / subtask create
- **大項目10「GitHub wrapper CLI を作る」** — `bin/ghw branch create-story` のみ使用（PR 作成・merge 系は不使用）
- **大項目11「Claude Code 共通ルールを作る」** — beads_task は PR 粒度、beads_subtask は agent 実行単位、AI は Done にしない / main に merge しない、等の不変ルール
- **大項目12「Claude Code subagent を作る」** — `.claude/agents/story-planner.md` の作成、read/write 対象と禁止事項の明記、使用 wrapper CLI の明記
- **大項目13「Claude Code command を作る」** — `/story-plan <shortcut-story-id>`
- **大項目14「StoryPlanner の検証環境を作る」** — fixture YAML、planned_pr_tasks 生成、schema validation、beads_task 作成、初期 subtask 作成、story branch 作成、planning summary コメント投稿（＝成功条件の直接対応）
- **大項目19「branch 戦略の検証」** — StoryPlanner が story branch を作成すること、final PR は story branch → main であること
- **大項目20「セーフティガードを追加する」** — Done 更新禁止、main 直接 PR / merge 禁止、schema validation 失敗時の登録拒否
- **大項目21「MVP 動作確認」** — fixture の Shortcut Story で `/story-plan` を実行し beads_story / beads_task / subtask が作成されること
- **大項目23「初期 MVP の完了条件」** — Shortcut Story から beads_task / subtask を生成できる、story branch を自動作成できる、AI agent が Done にしない / main に merge しない、人間が最終 Done 判断できる
