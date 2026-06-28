# フェーズF 実装ログ: MVP・運用（大項目21〜23）

- 完了日: 2026-06-28
- 対象: TODO.md 大項目 21〜23
- 前提: フェーズEの検証・ガード

## 概要

fixture Story を使った MVP 全行程の E2E 検証を追加し、初期運用に必要な人間向けドキュメントを整備した。
Shortcut / GitHub は引き続き mock / dry-run、beads はテストごとの一時 DB で検証する。

## 成果物

### MVP E2E テスト

- `tests/test_mvp_flow.py`
  - `/story-plan` 相当:
    - Shortcut Story 取得
    - `beads_story` / `beads_task` / 初期 `implement` + `review` subtask 作成
    - story branch 作成
    - Shortcut への planning summary 投稿
    - Shortcut Story の `Doing` 遷移
  - `/work-next` 相当:
    - implement subtask claim
    - task branch 作成
    - story branch 宛て task PR 作成
    - `pr_number` 記録
    - implement subtask close
  - `/review-pr` 相当:
    - review subtask claim
    - PR / CI 情報取得
    - `review_finding` 作成
    - fix subtask 作成
    - review subtask close
  - `/fix-findings` 相当:
    - fix subtask claim
    - finding fixed 化
    - fix subtask close
    - 再 review subtask 作成・close
    - task phase を `verified` に更新
  - `/story-review` 相当:
    - `story_review_summary` schema validation
    - In Review 遷移ガード通過
    - Shortcut への summary 投稿
    - Shortcut Story の `In Review` 遷移
  - 安全条件:
    - Shortcut Story を `Done` にできない
    - task PR を `main` へ直接作成できない
    - final PR は `merge=human-only`

### 運用ドキュメント

- `docs/operations.md`
  - Shortcut Story テンプレート
  - acceptance criteria の書き方
  - StoryPlanner 実行タイミング
  - AI 作成 PR の人間レビュー観点
  - StoryReviewer summary 確認手順
  - Shortcut Story を Done にする条件
  - final PR 手順
  - 失敗時の story branch 破棄手順
  - branch protection rule など環境依存の確認項目

## 主要な決定事項

1. **MVP 全行程は wrapper CLI 連鎖で固定**: Claude Code slash command 自体は Markdown 設定なので、テストでは各 command が呼ぶ wrapper CLI の連鎖を検証対象にした。
2. **外部サービスは使わない**: 実 Shortcut token / 実 GitHub PR はフェーズAの人間作業後に確認する。フェーズFでは CI で再現できる mock / dry-run の MVP を完了条件にした。
3. **PR merge 状態は StoryReviewer 入力として扱う**: dry-run GitHub は永続 PR 状態を持たないため、E2E テストでは `block_story_review_if_not_ready(open_must_fix_count=0, unmerged_pr_count=0)` で集約済み状態を検証する。
4. **Done と main merge は最後まで人間専用**: E2E の終点は Shortcut `In Review` と final PR 作成まで。`Done` への遷移と `main` merge は実装しない。

## 検証

- `tests/test_mvp_flow.py` により、fixture Story から planning / implementation / review / fix / story review までの一連の状態遷移が同じ beads DB と Shortcut mock store 上でつながることを確認。
- `story_review_summary` は schema validation を通す。
- open finding が fixed になり、`finding list --open` が空になることを確認。
- beads_task に `pr_numbers=[456]` と `current_phase=verified` が残ることを確認。
- Shortcut Story が `In Review` で止まり、`Done` にならないことを確認。

## 残る人間作業

- 実 Shortcut workspace の API token / State ID 対応確認。
- 実 GitHub repository の `main` branch protection rule 確認。
- 実運用 repo で `GHW_DRY_RUN` を外した task PR / final PR 作成確認。
- final PR merge と Shortcut Done 判断。
