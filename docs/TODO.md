# AI Development Workflow
## 仕様書
- [仕様書](docs/SPECIFICATION.md)

## 環境セットアップタスク

### 0. 前提確認

- [ ] 対象リポジトリを決める
- [ ] Shortcut の Workspace / Project / Workflow / State 名を確認する
- [ ] GitHub repository の URL と default branch を確認する
- [ ] main branch への merge 権限と branch protection rule を確認する
- [ ] Story branch 方式を採用することを決める
- [ ] AI agent が main に直接 merge しない運用ルールを決める
- [ ] Shortcut Story を Done にできるのは人間だけ、というルールを決める

### 1. ローカル開発環境の準備

- [ ] Python 3.11 以上をインストールする
- [ ] `uv` または `poetry` をインストールする
- [ ] Node.js / npm を必要に応じてインストールする
- [ ] GitHub CLI `gh` をインストールする
- [ ] `gh auth login` を実行して GitHub 認証を完了する
- [ ] Claude Code をインストールする
- [ ] Claude Code が対象リポジトリで動作することを確認する
- [ ] beads CLI をインストールする
- [ ] `bd --version` で beads CLI の動作を確認する

### 2. Shortcut 連携の準備

- [ ] Shortcut API token を発行する
- [ ] Shortcut API token をローカル環境変数に設定する
- [ ] `.env.example` に必要な環境変数を定義する
- [ ] `.env` を `.gitignore` に追加する
- [ ] Shortcut Story を取得するための最小 API 呼び出しを確認する
- [ ] Shortcut Story にコメントを追加できることを確認する
- [ ] Shortcut Story の State を更新できることを確認する
- [ ] Shortcut の State 名と内部 ID の対応をメモする

```env
SHORTCUT_API_TOKEN=
SHORTCUT_WORKSPACE_ID=
SHORTCUT_READY_STATE=
SHORTCUT_PLANNING_STATE=
SHORTCUT_DOING_STATE=
SHORTCUT_IN_REVIEW_STATE=
SHORTCUT_BLOCKED_STATE=
```

### 3. GitHub 連携の準備

- [ ] `gh repo view` が対象リポジトリで成功することを確認する
- [ ] PR 作成権限があることを確認する
- [ ] branch 作成権限があることを確認する
- [ ] story branch 命名規則を決める
- [ ] task branch 命名規則を決める
- [ ] final PR の作成ルールを決める
- [ ] AI agent が main に直接 PR を出さないようにルール化する
- [ ] main branch protection rule を確認する
- [ ] story branch に対する PR merge を自動化するか、人間承認にするか決める

```text
story branch: story/sc-123-saved-filters
task branch: agent/sc-123-saved-filters-api
final PR: story/sc-123-saved-filters -> main
task PR: agent/sc-123-saved-filters-api -> story/sc-123-saved-filters
```

### 4. beads 初期化

- [ ] 対象リポジトリで beads を初期化する
- [ ] embedded mode / server mode のどちらを使うか決める
- [ ] 個人検証では embedded mode を使う
- [ ] 複数 agent / 複数人運用では server mode を検討する
- [ ] beads のデータ保存先を確認する
- [ ] beads の backup / export 方針を決める
- [ ] beads の JSON 出力が Claude Code から扱えることを確認する
- [ ] beads task / subtask / finding 相当の表現方法を確認する
- [ ] 独自 metadata をどこに保持するか決める

### 5. リポジトリ構成を追加する

- [ ] `.claude/` ディレクトリを作成する
- [ ] `.claude/agents/` ディレクトリを作成する
- [ ] `.claude/commands/` ディレクトリを作成する
- [ ] `.ai-workflow/` ディレクトリを作成する
- [ ] `.ai-workflow/schemas/` ディレクトリを作成する
- [ ] `bin/` ディレクトリを作成する
- [ ] `CLAUDE.md` を作成する
- [ ] workflow 全体の不変ルールを `CLAUDE.md` に記述する

```text
repo/
  CLAUDE.md
  .claude/
    agents/
      story-planner.md
      implementer.md
      reviewer.md
      fixer.md
      story-reviewer.md
    commands/
      story-plan.md
      work-next.md
      review-pr.md
      fix-findings.md
      story-review.md
  .ai-workflow/
    config.yaml
    schemas/
      planned_pr_task.schema.json
      beads_task.schema.json
      beads_subtask.schema.json
      review_finding.schema.json
      story_review_summary.schema.json
  bin/
    sc-story
    bdw
    ghw
```

### 6. workflow 設定ファイルを作成する

- [ ] `.ai-workflow/config.yaml` を作成する
- [ ] Shortcut の State 対応を設定する
- [ ] GitHub の default branch を設定する
- [ ] story branch / task branch の命名規則を設定する
- [ ] PR 粒度の基本方針を設定する
- [ ] AI agent に許可する操作を設定する
- [ ] AI agent に禁止する操作を設定する

```yaml
shortcut:
  states:
    backlog: "Backlog"
    ready: "Ready"
    planning: "Planning"
    doing: "Doing"
    in_review: "In Review"
    blocked: "Blocked"
    done: "Done"

github:
  default_branch: "main"
  story_branch_prefix: "story"
  task_branch_prefix: "agent"
  allow_ai_merge_to_main: false
  allow_ai_mark_shortcut_done: false

planning_policy:
  pr_granularity: "reviewable_change_set"
  branch_strategy: "story_branch"
  max_expected_prs: 5
  prefer_separate_refactor_pr: true
  require_tests_per_pr: true
```

### 7. データスキーマを定義する

- [ ] `planned_pr_task` の schema を定義する
- [ ] `beads_task` の schema を定義する
- [ ] `beads_subtask` の schema を定義する
- [ ] `review_finding` の schema を定義する
- [ ] `story_review_summary` の schema を定義する
- [ ] schema validation 用のテストデータを作成する
- [ ] Claude Code が出力した YAML / JSON を schema validation できるようにする

```text
Shortcut Story
  - 人間が合意する成果単位

planned_pr_task
  - StoryPlanner が作る beads_task の下書き
  - 永続化するかは任意

beads_task
  - PR 粒度の作業単位
  - 作成時点では planned PR
  - PR 作成後は pr_number と紐づく

beads_subtask
  - agent が実行する単位
  - implement / review / fix / verify / summarize

review_finding
  - review subtask から生まれる構造化された指摘
```

### 8. Shortcut wrapper CLI を作成する

- [ ] `bin/sc-story` を作成する
- [ ] Shortcut Story を JSON で取得するコマンドを実装する
- [ ] Shortcut Story にコメントするコマンドを実装する
- [ ] Shortcut Story の State を更新するコマンドを実装する
- [ ] Shortcut Story に beads_story_id を記録するコマンドを実装する
- [ ] Shortcut API のエラー処理を実装する
- [ ] API token 未設定時に分かりやすいエラーを出す

```text
bin/sc-story get <story-id> --json
bin/sc-story comment <story-id> --file <path>
bin/sc-story set-state <story-id> <state>
bin/sc-story link <story-id> --beads-story <beads-story-id>
```

### 9. beads wrapper CLI を作成する

- [ ] `bin/bdw` を作成する
- [ ] beads story root を作成するコマンドを実装する
- [ ] beads task を作成するコマンドを実装する
- [ ] beads subtask を作成するコマンドを実装する
- [ ] role ごとの ready subtask を取得するコマンドを実装する
- [ ] subtask を close するコマンドを実装する
- [ ] review_finding を作成するコマンドを実装する
- [ ] open finding を一覧するコマンドを実装する
- [ ] beads task に pr_number を記録するコマンドを実装する
- [ ] beads task / subtask / finding の schema validation を実装する

```text
bin/bdw story create --shortcut-story <id> --title <title> --json
bin/bdw task create --file <planned-task.yaml> --json
bin/bdw subtask create --file <subtask.yaml> --json
bin/bdw ready --role <role> --json
bin/bdw close <subtask-id> --output <file>
bin/bdw finding create --file <finding.yaml> --json
bin/bdw finding list --task <task-id> --open --json
bin/bdw task link-pr <task-id> --pr <number>
```

### 10. GitHub wrapper CLI を作成する

- [ ] `bin/ghw` を作成する
- [ ] story branch を作成するコマンドを実装する
- [ ] task branch を作成するコマンドを実装する
- [ ] story branch 宛てに PR を作るコマンドを実装する
- [ ] PR 情報を JSON で取得するコマンドを実装する
- [ ] PR にコメントするコマンドを実装する
- [ ] PR の CI 状態を取得するコマンドを実装する
- [ ] final PR を作成するコマンドを実装する
- [ ] main への merge は実装しない、または明示的に禁止する

```text
bin/ghw branch create-story <story-id> --from main
bin/ghw branch create-task <story-id> <task-slug> --from <story-branch>
bin/ghw pr create --base <story-branch> --head <task-branch> --body <file>
bin/ghw pr view <number> --json
bin/ghw pr comment <number> --file <file>
bin/ghw pr checks <number> --json
bin/ghw pr create-final --story-branch <branch> --base main
```

### 11. Claude Code 共通ルールを作成する

- [ ] `CLAUDE.md` に workflow の基本ルールを書く
- [ ] Shortcut Story は人間の受け入れ単位であると明記する
- [ ] beads_task は PR 粒度であると明記する
- [ ] beads_subtask は agent 実行単位であると明記する
- [ ] PR は原則 story branch 宛てに作ると明記する
- [ ] AI agent は Shortcut Story を Done にしてはいけないと明記する
- [ ] AI agent は main に merge してはいけないと明記する
- [ ] Reviewer は直接修正せず、review_finding を作ると明記する
- [ ] Fixer は open finding の範囲だけ修正すると明記する

### 12. Claude Code subagent を作成する

- [ ] `story-planner.md` を作成する
- [ ] `implementer.md` を作成する
- [ ] `reviewer.md` を作成する
- [ ] `fixer.md` を作成する
- [ ] `story-reviewer.md` を作成する
- [ ] 各 subagent に read/write してよい対象を書く
- [ ] 各 subagent に禁止事項を書く
- [ ] 各 subagent が使う wrapper CLI を明記する

### 13. Claude Code command を作成する

- [ ] `/story-plan` 相当の command を作成する
- [ ] `/work-next` 相当の command を作成する
- [ ] `/review-pr` 相当の command を作成する
- [ ] `/fix-findings` 相当の command を作成する
- [ ] `/story-review` 相当の command を作成する

```text
/story-plan <shortcut-story-id>
/work-next
/review-pr <pr-number>
/fix-findings <beads-task-id>
/story-review <shortcut-story-id>
```

### 14. StoryPlanner の検証環境を作る

- [ ] Shortcut Story の fixture YAML を作成する
- [ ] fixture から planned_pr_tasks を生成できることを確認する
- [ ] planned_pr_tasks が schema validation を通ることを確認する
- [ ] planned_pr_tasks から beads_task を作成できることを確認する
- [ ] 初期 subtask として implement / review が作成されることを確認する
- [ ] story branch が作成されることを確認する
- [ ] Shortcut に planning summary コメントが投稿されることを確認する

### 15. Implementer の検証環境を作る

- [ ] ready な implement subtask を用意する
- [ ] Implementer が parent beads_task を読めることを確認する
- [ ] Implementer が planned_pr_scope を守ることを確認する
- [ ] task branch が作成されることを確認する
- [ ] story branch 宛てに PR が作成されることを確認する
- [ ] PR description に Shortcut Story ID / beads_task ID / acceptance_refs が入ることを確認する
- [ ] beads_task に pr_number が記録されることを確認する
- [ ] implement subtask が closed になることを確認する
- [ ] review subtask が ready になることを確認する

### 16. Reviewer の検証環境を作る

- [ ] review subtask を用意する
- [ ] Reviewer が PR を取得できることを確認する
- [ ] Reviewer が Shortcut Story の acceptance criteria を参照できることを確認する
- [ ] Reviewer が planned_pr_scope に対して差分を確認できることを確認する
- [ ] 問題がない場合に review subtask を closed にできることを確認する
- [ ] 問題がある場合に review_finding を作成できることを確認する
- [ ] must_fix finding がある場合に fix subtask を作成できることを確認する
- [ ] Reviewer が直接コード修正しないことを確認する

### 17. Fixer の検証環境を作る

- [ ] open review_finding を用意する
- [ ] fix subtask を ready にする
- [ ] Fixer が finding の範囲だけ修正することを確認する
- [ ] 既存 PR に commit を追加できることを確認する
- [ ] finding が fixed になることを確認する
- [ ] fix subtask が closed になることを確認する
- [ ] 再 review subtask が ready になることを確認する
- [ ] finding の範囲外の大きな変更を行わないことを確認する

### 18. StoryReviewer の検証環境を作る

- [ ] Shortcut Story に紐づく beads_story を用意する
- [ ] beads_task / beads_subtask / review_finding を集約できることを確認する
- [ ] PR の open / merged / CI 状態を取得できることを確認する
- [ ] acceptance criteria ごとの充足状況を判定できることを確認する
- [ ] open must_fix finding がある場合は In Review にしないことを確認する
- [ ] 必要な PR が未 merge の場合は In Review にしないことを確認する
- [ ] 条件が揃った場合に Shortcut Story を In Review にできることを確認する
- [ ] StoryReviewer が Shortcut Story を Done にしないことを確認する
- [ ] 人間向け summary コメントが Shortcut に投稿されることを確認する

### 19. branch 戦略の検証

- [ ] StoryPlanner が story branch を作成することを確認する
- [ ] Implementer が task branch を作成することを確認する
- [ ] task PR の base が story branch になることを確認する
- [ ] task PR が main に直接向かないことを確認する
- [ ] Story branch に複数 task PR を集約できることを確認する
- [ ] StoryReviewer が story branch の状態を確認できることを確認する
- [ ] final PR が story branch から main に向かうことを確認する
- [ ] final PR の merge は人間だけが行うことを確認する

### 20. セーフティガードを追加する

- [ ] `bin/ghw` で main への直接 PR 作成をデフォルト禁止する
- [ ] `bin/ghw` で main への merge を禁止する
- [ ] `bin/sc-story` で Done への state 更新をデフォルト禁止する
- [ ] AI agent が Done 更新を試みた場合にエラーにする
- [ ] schema validation に失敗した出力は登録しない
- [ ] planned_pr_scope 外の変更を検出する仕組みを検討する
- [ ] expected_files 外の変更がある場合に Reviewer が finding を出すようにする
- [ ] branch protection rule と AI workflow の制約が矛盾しないことを確認する

### 21. MVP 動作確認

- [ ] fixture の Shortcut Story で `/story-plan` を実行する
- [ ] beads_story / beads_task / subtask が作成されることを確認する
- [ ] story branch が作成されることを確認する
- [ ] `/work-next` で implement subtask を実行する
- [ ] story branch 宛てに PR が作成されることを確認する
- [ ] `/review-pr` で review_finding が作成できることを確認する
- [ ] `/fix-findings` で finding を修正できることを確認する
- [ ] `/story-review` で Shortcut に summary が戻ることを確認する
- [ ] Shortcut Story が In Review まで進み、Done にはならないことを確認する

### 22. 運用ドキュメントを作成する

- [ ] 人間が Shortcut Story を書くときのテンプレートを作る
- [ ] acceptance criteria の書き方を決める
- [ ] StoryPlanner を実行するタイミングを決める
- [ ] AI agent が作成した PR を人間が見る観点を決める
- [ ] StoryReviewer の summary を人間が確認する手順を決める
- [ ] Shortcut Story を Done にする条件を明文化する
- [ ] 失敗時に story branch を破棄する手順を決める
- [ ] story branch から main への final PR 手順を決める

### 23. 初期 MVP の完了条件

- [ ] Shortcut Story から beads_task / subtask を生成できる
- [ ] story branch を自動作成できる
- [ ] task branch から story branch 宛てに PR を作成できる
- [ ] PR 番号を beads_task に記録できる
- [ ] review_finding を beads に記録できる
- [ ] finding から fix subtask を生成できる
- [ ] Story 全体の状態を Shortcut に summary として戻せる
- [ ] AI agent が Shortcut Story を Done にしない
- [ ] AI agent が main に merge しない
- [ ] 人間が Shortcut 上で最終 Done 判断できる

