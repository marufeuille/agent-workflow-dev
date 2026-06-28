# AI Development Workflow

Shortcut × beads × GitHub × Claude Code を連携させた AI 開発ワークフロー基盤。
人間は Shortcut Story（受け入れ単位）と最終判断を担い、AI agent は計画〜実装〜レビュー〜修正を担う。

## 関連資料
- 全体設計: [docs/design/00-overview.md](docs/design/00-overview.md)
- 各 Agent 詳細: [docs/design/10-story-planner.md](docs/design/10-story-planner.md) / [11-implementer.md](docs/design/11-implementer.md) / [12-reviewer.md](docs/design/12-reviewer.md) / [13-fixer.md](docs/design/13-fixer.md) / [14-story-reviewer.md](docs/design/14-story-reviewer.md)
- 実装 TODO: [TODO.md](TODO.md)
- 実装ログ: [docs/impl/](docs/impl/)

## データモデル（粒度の階層）
- **Shortcut Story**: 人間が作成し、人間が最終受け入れを判断する成果単位
- **beads_story**（= Shortcut Story）: Shortcut Story と 1:1 で紐づく AI workflow 上の root
- **beads_task**: PR 粒度の作業単位。1 beads_task = 1 task branch / task PR。PR 作成後に `pr_numbers` と紐づく
- **beads_subtask**: agent 実行単位。`kind` = implement / review / fix / verify / summarize
- **review_finding**: review subtask から生まれる指摘。`severity` = must_fix / should_fix / nit / question

補助エンティティ: `planned_pr_task`（StoryPlanner が作る beads_task の下書き）、`story_review_summary`（StoryReviewer が Shortcut に投稿する集約サマリー）。
詳細は [docs/design/00-overview.md](docs/design/00-overview.md) §2。

## Git branch 戦略
- story branch: `story/sc-<id>-<slug>`（StoryPlanner が main から作成）
- task branch: `agent/sc-<id>-<slug>-<scope>`（Implementer が story branch から作成）
- task PR: `agent/...` → `story/...`
- final PR: `story/...` → `main`（merge は人間のみ）

## 不変ルール（AI agent が必ず守ること）
1. **main に merge しない**（merge は人間のみ）
2. **main 宛てに PR を出さない**（PR の base は必ず story branch）
3. **Shortcut Story を Done にしない**（Done 判断は人間のみ）
4. **Reviewer は直接コードを修正しない**（review_finding を作るだけ）
5. **Fixer は open review_finding の範囲だけ修正する**（範囲外の大きな変更はしない）
6. **Implementer は planned_pr_scope / expected_files の範囲内のみ変更する**
7. **外部システムは wrapper CLI 経由で操作する**（Shortcut/beads/GitHub を直接操作しない）

## Claude Code agents / commands（フェーズD）
- Agents: `.claude/agents/story-planner.md`, `implementer.md`, `reviewer.md`, `fixer.md`, `story-reviewer.md`
- Commands: `.claude/commands/story-plan.md`, `work-next.md`, `review-pr.md`, `fix-findings.md`, `story-review.md`
- 各 agent は read/write 対象、禁止事項、使用する wrapper CLI を個別ファイルに明記している。
- slash command は対応 agent を起動し、必要な wrapper CLI の前提確認と成果物の受け渡しを行う。

## wrapper CLI（フェーズCで実装済み: [phase-c.md](docs/impl/phase-c.md) / [bd-mapping.md](docs/design/bd-mapping.md)）
- `bin/sc-story`: Shortcut Story の取得 / コメント / state 更新。**Done 遷移は禁止**（mock 完結、real API は後回し）
- `bin/bdw`: beads（story / task / subtask / finding）の操作。`bd` CLI をラップ。入力は必ず schema 検証を通す
- `bin/ghw`: GitHub の branch / PR 操作。**main 直接 PR・merge は禁止**（dry-run + safe 呼出で検証）

## 設定・検証
- workflow 設定: `.ai-workflow/config.yaml`
- データスキーマ: `.ai-workflow/schemas/*.schema.json`
  - `planned_pr_task` / `beads_task` / `beads_subtask` / `review_finding` / `story_review_summary`
- スキーマ検証: `uv run python -m ai_workflow.schema_validator <file> <schema-name>`
