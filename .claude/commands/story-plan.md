---
description: Shortcut Story を計画し、beads task/subtask と story branch を作成する。
argument-hint: <shortcut-story-id>
---

# /story-plan

Use the `story-planner` subagent for Shortcut Story `$ARGUMENTS`.

## Required Input

- `$ARGUMENTS` は Shortcut Story ID。例: `123` または `sc-123`。`sc-story` には入力 ID を使い、`ghw branch create-story` には `sc-` を外した numeric ID を渡す。

## Execution Contract

1. `bin/sc-story get <story-id> --json` で Story を取得する。
2. Story を `planned_pr_task` に分解し、schema validation を通す。
3. `bin/bdw story create` と `bin/bdw task create --story <beads-story-id>` で beads に materialize する。
4. `bin/ghw branch create-story <numeric-story-id> --from main --slug <slug>` で story branch を作成する。
5. `bin/sc-story link`, `set-state`, `comment` で planning summary を Shortcut に戻す。

## Guardrails

- 実装、PR 作成、review_finding 作成、fix subtask 作成をしない。
- Shortcut Story を `Done` にしない。
- main への PR / merge をしない。
