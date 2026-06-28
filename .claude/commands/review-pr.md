---
description: task PR をレビューし、必要な review_finding と fix subtask を作成する。
argument-hint: <pr-number>
---

# /review-pr

Use the `reviewer` subagent for PR `$ARGUMENTS`.

## Required Input

- `$ARGUMENTS` は GitHub PR number。

## Execution Contract

1. `bin/ghw pr view <number> --json` と `bin/ghw pr checks <number> --json` で PR 状態を取得する。
2. 対応する beads_task、review subtask、Shortcut acceptance criteria を確認する。
3. PR diff を `planned_pr_scope`, `expected_files`, `acceptance_refs` に照らしてレビューする。
4. 問題があれば schema 準拠の `review_finding` を `bin/bdw finding create` で作成する。
5. `must_fix` があれば fix subtask を作成する。問題がなければ review subtask を close し、task phase を `verified` に進める。
6. PR に review summary をコメントする。

## Guardrails

- Reviewer はコードを修正しない。
- out of scope な好みの変更を `must_fix` にしない。
- main merge と Shortcut `Done` はしない。
