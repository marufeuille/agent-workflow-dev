# フェーズE 実装ログ: 検証・ガード（大項目14〜20）

- 完了日: 2026-06-28
- 対象: TODO.md 大項目 14〜20
- 前提: フェーズDの Claude Code agents / commands

## 概要

各 Agent の検証環境を整備し、セーフティガードを強化した。
実際の外部システム（Shortcut API / GitHub / beads）は依然として mock / dry-run で動作する。
5つの Agent フロー検証、branch 戦略検証、scope 検査ユーティリティを追加した。

## 成果物

### フィクスチャ

- `tests/fixtures/shortcut_story.valid.yaml`
  - StoryPlanner が読む Shortcut Story の fixture（sc-123: saved-filters）。
  - acceptance_criteria 2件、state="Ready" を初期値として定義。

- `tests/fixtures/beads_subtask_review.valid.yaml`
  - Implementer が実装後に作成する review subtask の fixture（id=bd-subtask-review-002）。

- `tests/fixtures/beads_subtask_review2.valid.yaml`
  - Fixer が修正後に作成する re-review subtask の fixture（id=bd-subtask-review-003）。
  - input_refs に finding-001 を含む。

- `tests/fixtures/implement_output.yaml`
  - Implementer が bdw close 時に渡す output_refs fixture。
  - status, pr_number, commit_shas, changed_files を定義。

- `tests/fixtures/review_output.yaml`
  - Reviewer が bdw close 時に渡す output_refs（問題なし時）fixture。

### 新規モジュール

- `ai_workflow/cli/scope_checker.py`
  - `files_outside_scope(changed_files, expected_files)`: changed_files のうち expected_files のいずれのパターンにも一致しないものを返す。
  - `is_within_scope(changed_files, expected_files)`: 全変更ファイルが scope 内かを boolean で返す。
  - fnmatch（glob）パターンで評価する。Reviewer が finding 生成時に使う。

### guards.py 拡張

- `block_story_review_if_not_ready(open_must_fix_count, unmerged_pr_count)` を追加。
  - open な must_fix finding がある場合はブロック（GuardError）。
  - 必要な PR が未 merge の場合はブロック（GuardError）。
  - StoryReviewer が sc-story set-state "In Review" を呼ぶ前にこのガードを適用する。

### テストファイル

| ファイル | 大項目 | 件数 |
|----------|--------|------|
| `tests/test_story_planner_flow.py` | 14 | 8件 |
| `tests/test_implementer_flow.py` | 15 | 8件 |
| `tests/test_reviewer_flow.py` | 16 | 7件 |
| `tests/test_fixer_flow.py` | 17 | 6件 |
| `tests/test_story_reviewer_flow.py` | 18 | 9件 |
| `tests/test_branch_strategy.py` | 19 | 8件 |
| `tests/test_scope_checker.py` | 20 | 12件 |

合計: 58件の新テスト（フェーズD以前の 45件に加算）。

## 主要な決定事項

1. **フロー検証は CLI 連鎖テストで実現**: 実際のエージェント動作はブラックボックスだが、
   各 wrapper CLI の連鎖で想定フローが実現できることを検証した。
   各テストは独立した beads DB（tmp_path）で実行される。

2. **StoryReviewer ガードは pure 関数**: `block_story_review_if_not_ready()` は
   外部状態に依存しない純粋関数として実装。呼び出し側（StoryReviewer agent）が
   open_must_fix_count と unmerged_pr_count を集約して渡す。

3. **scope_checker は fnmatch で実装**: glob パターンは fnmatch 標準ライブラリで評価。
   `app/api/*` は `app/api/v2/foo.py` にはマッチしない（サブディレクトリは別パターン必要）。

4. **Reviewer の「直接修正しない」は CLI 設計で担保**: Reviewer が使える bdw/ghw コマンドには
   ファイル書き込み操作が存在しない。finding create / subtask create / close のみ。

5. **re-review subtask の ID は fixture で明示**: `bdw subtask create` は fixture ファイルの
   id をそのまま使うため、id=bd-subtask-review-002/003 を明示した fixture を用意した。

## 検証

- 全テスト（既存45件 + 新規58件）がパスすることを確認。
- guards.py の新関数が GuardError を正しく raise することを確認。
- scope_checker が fnmatch パターンで期待通りに動作することを確認。
- StoryReviewer が Done にできず In Review にのみできることを確認。

## フェーズFへの引き継ぎ

- TODO.md 大項目21（MVP 動作確認）: fixture Story で全 slash command を end-to-end 実行する。
  外部 API（Shortcut / GitHub / beads 実環境）の準備が必要。
- TODO.md 大項目22（運用ドキュメント）: Story テンプレート・acceptance criteria 書き方・
  final PR 手順を整備する。
- TODO.md 大項目23（MVP 完了条件）: 大項目21-22が完了した時点で達成を確認する。
- scope_checker は Reviewer agent の `.claude/agents/reviewer.md` に
  「expected_files 外の変更を `scope_checker.py` で検出し finding を作成する」ガイダンスを追記する余地がある。
