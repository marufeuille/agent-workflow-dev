---
description: 次の ready implement subtask を取得し、Implementer で実装する。
argument-hint: ""
---

# /work-next

Use the `implementer` subagent for the next ready implement subtask.

## Execution Contract

1. `bin/bdw ready --role implement --json` で ready subtask を1件 claim する。
2. 親 beads_task の scope、expected files、acceptance refs、story branch を確認する。
3. task branch を作り、scope 内で実装とテストを行う。
4. task PR を story branch 宛てに作成または更新する。
5. PR 番号を `bin/bdw task link-pr` で記録し、implement subtask を close する。
6. review subtask を ready にし、task phase を `review` に進める。

## Guardrails

- `planned_pr_scope` / `expected_files` 外の変更をしない。
- PR base を main にしない。
- main merge と Shortcut `Done` はしない。
- ready implement subtask が無い場合は作業しない。
