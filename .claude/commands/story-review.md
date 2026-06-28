---
description: Story 全体を集約し、条件が揃った場合だけ Shortcut を In Review にする。
argument-hint: <shortcut-story-id>
---

# /story-review

Use the `story-reviewer` subagent for Shortcut Story `$ARGUMENTS`.

## Required Input

- `$ARGUMENTS` は Shortcut Story ID。例: `123` または `sc-123`。

## Execution Contract

1. `bin/sc-story get <story-id> --json` で Shortcut Story と beads_story_id を取得する。
2. beads_story 配下の task、subtask、finding を集約する。
3. 各 task PR の state と CI を `bin/ghw pr view` / `bin/ghw pr checks` で確認する。
4. open `must_fix` finding、未 merge PR、失敗 CI、未充足 acceptance criteria をゲート判定する。
5. `story_review_summary.schema.json` に準拠する summary を作成して検証する。
6. すべてのゲートが通った場合だけ `bin/sc-story set-state <story-id> "In Review"` を実行する。
7. Shortcut に人間向け summary をコメントする。

## Guardrails

- Shortcut Story を `Done` にしない。
- main への merge をしない。
- open `must_fix` finding や未 merge PR がある状態で `In Review` にしない。
