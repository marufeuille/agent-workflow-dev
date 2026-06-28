---
description: 指定 task の open review_finding を Fixer で修正し、再 review に戻す。
argument-hint: <beads-task-id>
---

# /fix-findings

Use the `fixer` subagent for beads task `$ARGUMENTS`.

## Required Input

- `$ARGUMENTS` は beads_task ID。

## Execution Contract

1. `bin/bdw ready --role fix --json` で fix subtask を claim し、parent_task_id が `$ARGUMENTS` と一致することを確認する。
2. `bin/bdw finding list --task <task-id> --open --json` で open findings を取得する。
3. finding の `description` / `suggested_fix` / `file` の範囲だけ修正する。
4. 関連テストを実行する。
5. 修正済み finding を `bin/bdw finding update <finding-id> --status fixed` にする。
6. fix subtask を close し、再 review subtask を ready にする。
7. 既存 PR に修正 summary をコメントする。

## Guardrails

- finding 範囲外の変更をしない。
- 新規 PR を作らない。既存 PR が無い場合は停止する。
- main merge と Shortcut `Done` はしない。
