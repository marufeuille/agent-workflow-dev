# AI Development Workflow 運用手順

この文書はフェーズF時点の初期 MVP 運用ルールをまとめる。実 Shortcut / GitHub 連携を使う場合も、AI agent は必ず `bin/sc-story` / `bin/bdw` / `bin/ghw` 経由で操作する。

## Shortcut Story テンプレート

Shortcut Story は人間が作成し、AI は Story の内容を読み取って計画する。

```md
## 背景
なぜこの変更が必要か。

## 期待する成果
ユーザーまたは運用者に見える最終状態。

## Acceptance Criteria
- AC-1: <観測可能な条件>
- AC-2: <失敗条件や境界条件>

## 非対象
- 今回やらない範囲。

## 補足
- 関連リンク、既知制約、対象画面や API。
```

## Acceptance Criteria の書き方

- `AC-1`, `AC-2` のように安定した ID を付ける。
- 「実装する」ではなく「観測できる結果」を書く。
- 正常系だけでなく、失敗条件・権限・空入力・互換性などの境界を含める。
- 1つの AC に複数の成果を詰め込まない。
- UI、API、データ移行など対象領域が異なる場合は AC を分ける。

## StoryPlanner 実行タイミング

人間が Story と Acceptance Criteria に合意し、Shortcut State を `Ready` にした後で実行する。

```sh
/story-plan <shortcut-story-id>
```

StoryPlanner は以下を行う。

- Shortcut Story を取得する。
- `beads_story` と PR 粒度の `beads_task` を作る。
- 初期 `implement` / `review` subtask を作る。
- `story/sc-...` branch を作る。
- Shortcut に planning summary をコメントする。
- Shortcut Story を `Doing` へ進める。

## 実装・レビュー・修正

通常の進行は次の順序で行う。

```sh
/work-next
/review-pr <pr-number>
/fix-findings <beads-task-id>
/review-pr <pr-number>
/story-review <shortcut-story-id>
```

人間が AI 作成 PR を見る観点は次の通り。

- PR の base が `story/sc-...` であり、`main` ではない。
- PR 本文に Shortcut Story ID、beads_task ID、対象 AC、scope が入っている。
- 差分が `planned_pr_scope` と `expected_files` の範囲内に収まっている。
- Reviewer がコードを直接直さず、必要な指摘を `review_finding` にしている。
- Fixer が open finding の範囲だけを修正している。
- 必要なテストや検証結果が PR または subtask output に残っている。

## StoryReviewer Summary の確認

`/story-review <shortcut-story-id>` は Story 全体を集約し、Shortcut に summary を投稿する。

人間は summary で次を確認する。

- 各 Acceptance Criteria が satisfied になっている。
- open な `must_fix` finding がない。
- 必要な task PR が story branch に取り込まれている。
- CI 失敗や未確認の pending PR がない。
- Shortcut Story が `In Review` まで進み、`Done` にはなっていない。

## Shortcut Story を Done にする条件

`Done` への遷移は人間だけが行う。

- StoryReviewer summary の `ready_for_review` が true。
- final PR の内容を人間が確認済み。
- final PR が `story/sc-...` から `main` へ向いている。
- main への merge を人間が実行済み。
- リリースや運用確認が必要な場合は完了済み。

## Final PR 手順

AI は final PR を作成できるが、merge はしない。

```sh
bin/ghw pr create-final \
  --story-branch story/sc-123-saved-filters \
  --base main \
  --body final-pr.md
```

人間は final PR の差分、CI、review 状態、branch protection rule を確認してから merge する。

## 失敗時の story branch 破棄

Story branch を捨てる判断は人間が行う。破棄前に Shortcut コメントへ理由、対象 branch、残すべき知見を記録する。

推奨手順:

1. Shortcut Story を `Blocked` または運用上の差し戻し state にする。
2. open PR を close し、必要なら comment で破棄理由を書く。
3. story branch / task branch の削除対象を人間が確認する。
4. GitHub 上で branch を削除する。
5. beads の task / finding は監査用に残し、再計画時は新しい task を作る。

## 環境依存の確認項目

次の項目は実リポジトリ・実 Shortcut workspace で人間が確認する。

- Shortcut API token と State ID 対応。
- `gh auth login` と PR 作成権限。
- `main` branch protection rule。
- AI workflow の「main merge 禁止」「Done 禁止」と branch protection rule が矛盾しないこと。
