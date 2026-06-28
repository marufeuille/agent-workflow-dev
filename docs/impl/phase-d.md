# フェーズD 実装ログ: Claude Code agents / commands

- 完了日: 2026-06-28
- 対象: TODO.md 大項目 11・12・13
- 前提: フェーズCの wrapper CLI（`bin/sc-story` / `bin/bdw` / `bin/ghw`）

## 概要

Claude Code が workflow を実行するための共通ルール、5つの subagent、5つの slash command を追加した。各 agent は外部システムを直接操作せず、フェーズCで実装した wrapper CLI を使う前提で、read/write 対象・禁止事項・完了条件を明記している。

## 成果物

### 共通ルール

- `CLAUDE.md` に Shortcut Story / beads_story / beads_task / beads_subtask の粒度を補強。
- 不変ルールに「外部システムは wrapper CLI 経由で操作する」を追加。
- フェーズDで追加した agents / commands の配置を追記。

### subagent

- `.claude/agents/story-planner.md`
  - Shortcut Story を `planned_pr_task` に分解し、beads_story / beads_task / 初期 subtask / story branch を作成する。
- `.claude/agents/implementer.md`
  - ready implement subtask を実行し、scope 内の変更を task PR として story branch に出す。
- `.claude/agents/reviewer.md`
  - PR をレビューし、必要な `review_finding` と fix subtask を作成する。コード修正は禁止。
- `.claude/agents/fixer.md`
  - open finding の範囲だけを修正し、finding fixed 化と再 review subtask 作成を行う。
- `.claude/agents/story-reviewer.md`
  - Story 全体を集約し、ゲート通過時のみ Shortcut Story を `In Review` にする。`Done` にはしない。

### slash command

- `.claude/commands/story-plan.md`: `/story-plan <shortcut-story-id>`
- `.claude/commands/work-next.md`: `/work-next`
- `.claude/commands/review-pr.md`: `/review-pr <pr-number>`
- `.claude/commands/fix-findings.md`: `/fix-findings <beads-task-id>`
- `.claude/commands/story-review.md`: `/story-review <shortcut-story-id>`

## 主要な決定事項

1. **実装は Markdown 設定に限定**: フェーズDは Claude Code 設定フェーズのため、Python CLI の機能追加は行っていない。
2. **wrapper CLI 前提を維持**: Shortcut/beads/GitHub は `bin/sc-story`, `bin/bdw`, `bin/ghw` 経由で操作する。必要情報が wrapper から得られない場合は raw CLI で迂回せず安全に停止する方針を agent に明記した。
3. **role 名と kind 名を分離**: `bdw ready --role reviewer|fixer` は受け付けるが、永続化する `beads_subtask.kind` は schema に合わせて `review|fix` とする。
4. **安全側に倒す指示**: Reviewer の直接修正禁止、Fixer の finding 範囲外変更禁止、StoryReviewer の Done 禁止を各 agent / command に重複して記載した。

## 検証

- agents 5件と commands 5件のファイル存在を確認。
- 各 agent に read/write 対象、禁止事項、wrapper CLI、完了条件を記載。
- 各 command に slash command 名、引数、実行契約、guardrails を記載。
- 既存テストでフェーズB/Cの CLI・schema 挙動が壊れていないことを確認する。

## フェーズEへの引き継ぎ

- TODO.md 大項目14以降で fixture Story を用意し、各 slash command の実行経路を検証する。
- MVP検証中に wrapper CLI の読み取り系不足が判明した場合は、raw `bd` 迂回ではなく `bin/bdw` に明示的な read/list 操作を追加する。
