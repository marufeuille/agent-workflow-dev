# 全体アーキテクチャ設計

本ファイルは「AI Development Workflow」の全体像を扱う。各 Agent の詳細な内部処理（入出力スキーマ・シーケンス・成功条件）は本ファイルでは一覧表レベルで留め、別ファイルに譲る。

- 全体概要: 本ファイル（`00-overview.md`）
- 各 Agent 詳細: `10-story-planner.md` / `11-implementer.md` / `12-reviewer.md` / `13-fixer.md` / `14-story-reviewer.md`

> 出典の凡例:
> - **（画像より）**: `workflow_and_basic_data.excalidraw.png` / `git_branch.excalidraw.png` から読み取った情報
> - **（TODO.mdより）**: `TODO.md` から補完した情報（大項目番号を併記）
> - **（11-implementer.mdより）**: 既存の Implementer 設計書から得た画像断片情報
> - **（画像から不明）**: 画像からは読み取れなかった箇所

---

## 1. システム全体像

4 つの構成要素が連携し、人間と AI の役割を明確に分離する（画像より）。

### 構成要素
- **Shortcut**: 人間が Story（成果の受け入れ単位）を作成・管理するチケット管理系。AI は読み取り・コメント・State の一部更新は行うが、**Done への遷移は人間のみ**（TODO.md大項目0・11・20より）。
- **beads**: AI の作業進行を管理するタスクトラッキング DB。story / task / subtask / finding の階層構造を持ち、Claude Code が JSON で読み書きする（TODO.md大項目4・9より）。
- **GitHub**: コード変更の実体を置く Git ホスティング。story branch / task branch の2層構成で PR を管理する。**main への直接 PR・merge は AI 禁止**（TODO.md大項目0・3・20より）。
- **Claude Code**: AI agent の実行環境。5 つの subagent（StoryPlanner / Implementer / Reviewer / Fixer / StoryReviewer）と slash command（`/story-plan` `/work-next` `/review-pr` `/fix-findings` `/story-review`）からなる（TODO.md大項目12・13より）。

### 人間と AI の役割分担
| 役割 | 人間 | AI agent |
|------|------|----------|
| Shortcut Story の作成 | 行う | 行わない |
| acceptance criteria の合意 | 行う | 参照のみ |
| Story の Done 化 | **行う（唯一）** | 禁止 |
| main への merge（final PR） | **行う（唯一）** | 禁止 |
| 計画・実装・レビュー・修正 | 監督・最終判断 | 行う |
| beads の task/subtask/finding 管理 | 監督のみ | 行う |

（TODO.md大項目0・11・20・23より）

---

## 2. データモデル

beads 上の作業単位は **story → task → subtask → finding** の階層（TODO.md大項目7より）。画像ではこの階層と各エンティティのフィールドが図示されている。

### 2.1 `beads_story`
- Shortcut Story に 1:1 で紐づく、人間が合意する成果単位（TODO.md大項目7より）。
- 画像では Shortcut Story と beads_story の紐付け関係が描かれている（画像より）。
- フィールドの詳細: **（画像から不明 - TODO.md大項目7・9より）** `shortcut_story_id`, `title` 等を保持。`bin/bdw story create --shortcut-story <id> --title <title>` で作成（TODO.md大項目9より）。

### 2.2 `beads_task`（PR 粒度、pr_number と紐づく）
- **PR 粒度の作業単位**。作成時点では planned PR、PR 作成後に `pr_number`（`pr_numbers`）と紐づく（TODO.md大項目7より、11-implementer.mdより）。
- 1つの beads_task = 1つの task branch / PR（複数 task の混在禁止）（11-implementer.mdより）。
- フィールド（11-implementer.md に記載された画像断片より、`parent_task` として参照）:
  - `id`: 例 `bd-task-001`
  - `planned_pr_scope`: 例 `"Backend API and persistence only; UI changes are out of scope."`
  - `acceptance_refs`: 例 `["AC-1", "AC-2"]`
  - `expected_files`: 例 `["app/api/*", "app/models/*", "tests/api/*"]`
  - `branch_name`: 例 `"agent/sc-123-saved-filters-api"`
  - `pr_numbers`: PR 作成後に記録（`bin/bdw task link-pr`）（TODO.md大項目9・15より）

### 2.3 `beads_subtask`（role 別: implement/review/fix/verify/summarize）
- **agent が実行する単位**。role（kind）ごとに分かれる（TODO.md大項目7より）。
- kind 一覧: `implement` / `review` / `fix` / `verify` / `summarize`（TODO.md大項目7より）。
- フィールド（11-implementer.md の画像断片より）:
  - `id`: 例 `bd-subtask-implement-001`
  - `kind`: `implement` / `review` / `fix` / `verify` / `summarize`
  - `status`: `ready` / `closed` 等
- 状態遷移の例: `kind=implement, status=ready` →（実装後）→ `status=closed`、次に `kind=review, status=ready` を生成（11-implementer.mdより）。
- wrapper: `bin/bdw ready --role <role>` で取得、`bin/bdw close <id>` でクローズ、`bin/bdw subtask create` で生成（TODO.md大項目9より）。

### 2.4 `review_finding`（must_fix / should_fix 等）
- review subtask から生まれる構造化された指摘（TODO.md大項目7より）。
- severity として `must_fix` / `should_fix` 等の区分を持つ（テンプレート指定より）。
- wrapper: `bin/bdw finding create` / `bin/bdw finding list --task <id> --open`（TODO.md大項目9・16より）。
- フィールドの詳細: **（画像から不明 - TODO.md大項目7・16より）** severity・対象ファイル・指摘内容等。must_fix finding がある場合は fix subtask が生成される。

### 2.5 補助エンティティ
- **`planned_pr_task`**: StoryPlanner が作る beads_task の下書き。永続化するかは任意（TODO.md大項目7より）。
- **`story_review_summary`**: StoryReviewer が Shortcut に投稿する、Story 全体の集約サマリー。acceptance criteria ごとの充足状況を含む（TODO.md大項目7・18より）。

---

## 3. ワークフロー全体フロー

人間が Shortcut Story を作るところから Done までの時系列（画像の全体フロー図より、TODO.md大項目21の MVP フローで裏付け）。

```
[人間] Shortcut Story を作成（acceptance criteria 記載）
   │
   ▼
[人間] /story-plan <story-id> を実行
   │
   ▼
[StoryPlanner] Story を読む → planned_pr_tasks を生成
   │   → beads_story / beads_task / 初期 subtask（implement, review）を作成
   │   → story branch を作成（bin/ghw branch create-story --from main）
   │   → Shortcut に planning summary コメントを投稿
   │   → Shortcut Story の State を Planning → Doing に（画像より、TODO.md大項目2・6より）
   ▼
[人間/AI] /work-next を実行 → ready な implement subtask を取得
   │
   ▼
[Implementer] planned_pr_scope 内で実装
   │   → task branch 作成（bin/ghw branch create-task --from <story-branch>）
   │   → story branch 宛てに PR 作成（bin/ghw pr create --base <story-branch>）
   │   → beads_task に pr_number 記録（bin/bdw task link-pr）
   │   → implement subtask を closed、review subtask を ready 化
   ▼
[人間/AI] /review-pr <pr-number> を実行
   │
   ▼
[Reviewer] PR を取得 → acceptance criteria / planned_pr_scope に対して差分確認
   │   問題なし → review subtask を closed → verify/summarize subtask へ
   │   問題あり → review_finding を作成（must_fix / should_fix）
   │            → must_fix があれば fix subtask を ready 化
   │   ※ Reviewer は直接コード修正しない（TODO.md大項目11・16より）
   ▼
[人間/AI] /fix-findings <task-id> を実行（must_fix finding がある場合）
   │
   ▼
[Fixer] open finding の範囲だけ修正
   │   → 既存 PR に commit を追加
   │   → finding を fixed、fix subtask を closed
   │   → 再 review subtask を ready 化
   │   ※ finding の範囲外の大きな変更は行わない（TODO.md大項目17より）
   ▼
（すべての task PR で review 通過 → 全 task 完了）
   │
   ▼
[人間/AI] /story-review <story-id> を実行
   │
   ▼
[StoryReviewer] beads_story 配下の task / subtask / finding を集約
   │   → 各 PR の open / merged / CI 状態を確認
   │   → acceptance criteria ごとの充足状況を判定
   │   → open must_fix がなく、必要 PR が merge 済みなら Shortcut Story を In Review に
   │   → Shortcut に人間向け summary コメントを投稿（story_review_summary）
   │   ※ StoryReviewer は Done にしない（TODO.md大項目18より）
   ▼
[人間] final PR（story branch → main）を確認・merge（人間のみ）
   │
   ▼
[人間] Shortcut Story を Done に（人間のみ）
```

（フロー全体構造は画像より、各ステップの詳細は TODO.md大項目14〜18・21、11-implementer.mdより）

---

## 4. Git branch 戦略

2層の branch 構造で、main への直接アクセスを AI から遮断する（画像の git_branch 図より、TODO.md大項目3・19より）。

### 構造
```
main（保護ブランチ・人間のみ merge 可）
 │
 ├── story/sc-123-saved-filters        ← StoryPlanner が作成（bin/ghw branch create-story --from main）
 │     │
 │     ├── agent/sc-123-saved-filters-api      ← Implementer が作成
 │     │     └── task PR ─────────────────────►  (base) story/sc-123-saved-filters
 │     │
 │     ├── agent/sc-123-saved-filters-ui       ← 別 task（別 beads_task）
 │     │     └── task PR ─────────────────────►  (base) story/sc-123-saved-filters
 │     │
 │     └── （複数 task PR を story branch に集約）
 │
 └── final PR: story/sc-123-saved-filters ───► (base) main   ← 人間のみ merge
```

### 命名規則（TODO.md大項目3より）
- story branch: `story/sc-123-saved-filters`
- task branch: `agent/sc-123-saved-filters-api`
- final PR: `story/sc-123-saved-filters` → `main`
- task PR: `agent/sc-123-saved-filters-api` → `story/sc-123-saved-filters`

### 重要な不変条件
- **main への直接 PR は禁止**（AI は必ず story branch 宛てに出す）（TODO.md大項目3・19・20より）。`bin/ghw` は main 宛て PR 作成をデフォルト禁止（TODO.md大項目20より）。
- **main への merge は禁止**（AI は merge しない）（TODO.md大項目0・11・20より）。
- **final PR の merge は人間のみ**（TODO.md大項目3・19・22より）。
- story branch には複数の task PR を集約できる（TODO.md大項目19より）。
- task PR の base は必ず story branch（main に直接向かわない）（TODO.md大項目19より）。

（branch 間の矢印の向き・集約関係は画像より、命名規則・禁止事項は TODO.md大項目3・19・20より）

---

## 5. 各 Agent の役割分担（一覧表）

| Agent | 責務 | 主な入力 | 主な出力 | 使う wrapper CLI |
|-------|------|----------|----------|------------------|
| **StoryPlanner** | Shortcut Story を分解し、planned PR（beads_task）と初期 subtask を計画・作成。story branch を作成し、Shortcut に planning summary を投稿 | Shortcut Story（acceptance criteria） | beads_story / beads_task / 初期 subtask（implement, review）/ story branch / planning summary コメント | `bin/sc-story`（get/comment/set-state）・`bin/bdw`（story/task/subtask create）・`bin/ghw`（branch create-story） |
| **Implementer** | ready な implement subtask を取り、planned_pr_scope 内で実装し、story branch 宛てに PR 作成。pr_number 記録・次 review subtask を ready 化 | beads_subtask（kind=implement, ready）/ parent beads_task（scope, expected_files, acceptance_refs, branch_name） | コード実装 / task branch / story branch 宛て PR / pr_number 記録 / implement subtask closed / review subtask ready | `bin/bdw`（ready/link-pr/close/subtask create）・`bin/ghw`（branch create-task, pr create） |
| **Reviewer** | PR を取得し、acceptance criteria / planned_pr_scope に対して差分レビュー。問題なければ subtask を closed、問題あれば review_finding を作成し fix subtask を ready 化。**直接修正しない** | beads_subtask（kind=review, ready）/ PR / Shortcut Story の acceptance criteria / planned_pr_scope / expected_files | review_finding（must_fix/should_fix）/ review subtask closed / fix subtask ready（must_fix 時） | `bin/bdw`（finding create, close, subtask create）・`bin/ghw`（pr view, pr checks）・`bin/sc-story`（acceptance 参照） |
| **Fixer** | open review_finding の範囲だけ修正し、既存 PR に commit を追加。finding を fixed・fix subtask を closed・再 review subtask を ready 化。**範囲外の大きな変更はしない** | beads_subtask（kind=fix, ready）/ open review_finding / 対象 PR | commit 追加（既存 PR）/ finding fixed / fix subtask closed / 再 review subtask ready | `bin/bdw`（finding list/close, subtask create）・`bin/ghw`（pr 更新） |
| **StoryReviewer** | Story 配下の task/subtask/finding/PR を集約し、acceptance criteria ごとの充足状況を判定。条件が揃えば Shortcut Story を In Review に。人間向け summary を投稿。**Done にはしない** | beads_story（配下の task/subtask/finding）/ 各 PR の状態（open/merged/CI）/ acceptance criteria | story_review_summary / Shortcut State を In Review へ / Shortcut summary コメント | `bin/bdw`（task/subtask/finding 集約）・`bin/ghw`（pr view/checks）・`bin/sc-story`（set-state, comment） |

（責務・入出力の構造は画像より、CLI の詳細は TODO.md大項目9・10・14〜18、11-implementer.mdより。各 Agent の詳細なスキーマ・シーケンスは `10-story-planner.md` / `11-implementer.md` / `12-reviewer.md` / `13-fixer.md` / `14-story-reviewer.md` を参照）

### Claude Code slash command と Agent の対応（TODO.md大項目13より）
| Command | 起動する処理 |
|---------|--------------|
| `/story-plan <shortcut-story-id>` | StoryPlanner |
| `/work-next` | ready な subtask に応じて Implementer 等 |
| `/review-pr <pr-number>` | Reviewer |
| `/fix-findings <beads-task-id>` | Fixer |
| `/story-review <shortcut-story-id>` | StoryReviewer |

---

## 6. セーフティガード一覧

AI agent がやってはいけないことの総覧。CLAUDE.md 共通ルール（TODO.md大項目11）と wrapper CLI レベルのガード（TODO.md大項目20）の両面で担保する。

### 絶対禁止事項
1. **main merge 禁止**: AI agent はいかなる場合も main に merge しない。merge は人間のみ（TODO.md大項目0・11・20より）。`bin/ghw` は main merge を禁止（TODO.md大項目20より）。
2. **main 直接 PR 禁止**: PR の base は必ず story branch。`bin/ghw` は main 宛て PR 作成をデフォルト禁止（TODO.md大項目3・19・20より）。
3. **Shortcut Done 禁止**: AI agent は Shortcut Story を Done にできない。`bin/sc-story` は Done 遷移をデフォルト禁止（TODO.md大項目0・11・20より）。
4. **Reviewer の直接修正禁止**: Reviewer はコードを直接直さず、review_finding を作るだけ（TODO.md大項目11・16より）。

### スコープ・粒度のガード
5. **scope 外変更禁止**: Implementer は `planned_pr_scope` / `expected_files` の範囲内のみ。画像では「out of scope に含まれる変更を行わない」と明記（11-implementer.mdより、TODO.md大項目15・20より）。
6. **Fixer の範囲制限**: Fixer は open finding の範囲だけ修正し、大きな変更を行わない（TODO.md大項目17より）。
7. **複数 task の混在禁止**: 1つの task branch / PR には1つの beads_task の範囲のみ。PR 粒度 = beads_task（11-implementer.mdより、TODO.md大項目6・7より）。
8. **expected_files 外変更の検出**: expected_files 外の変更がある場合、Reviewer が finding を出す。planned_pr_scope 外変更の検出仕組みを検討（TODO.md大項目20より）。

### データ整合性のガード
9. **schema validation 失敗時の登録拒否**: validation に失敗した YAML/JSON 出力は beads に登録しない（TODO.md大項目20より）。
10. **StoryReviewer の遷移ガード**: open must_fix finding がある場合は In Review にしない。必要な PR が未 merge の場合は In Review にしない（TODO.md大項目18より）。
11. **依存未完了での実装禁止**: 依存する subtask/task が完了していることを確認してから実装する（11-implementer.mdより）。

### インフラレベルのガード
12. **branch protection rule**: main branch protection rule を確認し、AI workflow の制約と矛盾しないこと（TODO.md大項目0・3・20より）。
13. **API token 未設定時のエラー**: Shortcut API token 未設定時に分かりやすいエラーを出す（TODO.md大項目8より）。

---

## 7. TODO.md 大項目マッピング

TODO.md の23大項目をフェーズ/グループに分類。本ワークフロー全体の実装スコープを示す。

### フェーズA: 環境準備（大項目 0-4）
| 大項目 | 内容 | 本設計との対応 |
|--------|------|----------------|
| 0. 前提確認 | 対象 repo / Shortcut 設定 / GitHub 権限 / 運用ルール（main merge 禁止・Done は人間のみ）の決定 | §1, §6（禁止事項の源泉） |
| 1. ローカル開発環境 | Python / uv / Node / gh / Claude Code / beads CLI のインストール | §1（Claude Code・beads の実行環境） |
| 2. Shortcut 連携の準備 | API token / State 名と ID の対応 / 最小 API 呼び出しの確認 | §1（Shortcut）, §5（`bin/sc-story`） |
| 3. GitHub 連携の準備 | 権限確認 / branch 命名規則 / final PR ルール / main 直接 PR 禁止ルール | §4（branch 戦略） |
| 4. beads 初期化 | embedded/server mode / データ保存先 / JSON 出力の確認 | §1（beads）, §2（データモデル） |

### フェーズB: 基盤・スキーマ・設定（大項目 5-7）
| 大項目 | 内容 | 本設計との対応 |
|--------|------|----------------|
| 5. リポジトリ構成 | `.claude/`（agents/commands）/ `.ai-workflow/`（schemas）/ `bin/`（wrapper）/ `CLAUDE.md` の作成 | §5（Agent・CLI の格納先） |
| 6. workflow 設定ファイル | `.ai-workflow/config.yaml`（State 対応・branch 規則・PR 粒度・AI 許可/禁止操作） | §4, §6 |
| 7. データスキーマ定義 | planned_pr_task / beads_task / beads_subtask / review_finding / story_review_summary の schema | §2（データモデル） |

### フェーズC: wrapper CLI（大項目 8-10）
| 大項目 | 内容 | 本設計との対応 |
|--------|------|----------------|
| 8. Shortcut wrapper CLI | `bin/sc-story`（get/comment/set-state/link） | §5（各 Agent が使用） |
| 9. beads wrapper CLI | `bin/bdw`（story/task/subtask/finding create, ready, close, link-pr） | §2, §5 |
| 10. GitHub wrapper CLI | `bin/ghw`（branch create-story/create-task, pr create/view/comment/checks, create-final）。**main merge は実装しない** | §4, §5, §6 |

### フェーズD: Claude Code 設定（大項目 11-13）
| 大項目 | 内容 | 本設計との対応 |
|--------|------|----------------|
| 11. Claude Code 共通ルール | `CLAUDE.md` に基本ルール（PR 粒度・禁止事項・Reviewer 直接修正禁止・Fixer 範囲制限等） | §6（セーフティガード） |
| 12. Claude Code subagent | story-planner.md / implementer.md / reviewer.md / fixer.md / story-reviewer.md の作成 | §5（各 Agent 詳細は 10-14 に譲る） |
| 13. Claude Code command | `/story-plan` `/work-next` `/review-pr` `/fix-findings` `/story-review` の作成 | §5（slash command 対応表） |

### フェーズE: 検証・ガード（大項目 14-20）
| 大項目 | 内容 | 本設計との対応 |
|--------|------|----------------|
| 14. StoryPlanner の検証 | fixture Story → planned_pr_tasks → beads_task/subtask → story branch → planning summary | §3, §5（StoryPlanner） |
| 15. Implementer の検証 | ready subtask → scope 内実装 → task branch → story branch 宛 PR → pr_number 記録 → review ready | §3, §5, 詳細は `11-implementer.md` |
| 16. Reviewer の検証 | PR 取得 → acceptance/scope レビュー → review_finding 作成 → fix subtask 生成・直接修正しない | §3, §5 |
| 17. Fixer の検証 | open finding → 範囲内修正 → 既存 PR に commit 追加 → finding fixed → 再 review ready | §3, §5 |
| 18. StoryReviewer の検証 | 集約 → acceptance 充足判定 → In Review 遷移ガード → summary 投稿・Done にしない | §3, §5, §6 |
| 19. branch 戦略の検証 | story branch / task branch / task PR の base / story branch 集約 / final PR・merge は人間 | §4 |
| 20. セーフティガード | main 直接 PR/merge 禁止・Done 禁止・schema validation・scope 外検出・branch protection 整合 | §6 |

### フェーズF: MVP・運用（大項目 21-23）
| 大項目 | 内容 | 本設計との対応 |
|--------|------|----------------|
| 21. MVP 動作確認 | fixture Story で `/story-plan` → `/work-next` → `/review-pr` → `/fix-findings` → `/story-review` の全行程確認。Done にならないこと | §3（全体フロー） |
| 22. 運用ドキュメント | Story テンプレート・acceptance criteria 書き方・StoryPlanner 実行タイミング・最終 Done 条件・final PR 手順・失敗時の story branch 破棄 | §1（人間の役割）, §4（final PR 手順） |
| 23. 初期 MVP の完了条件 | beads_task/subtask 生成・story/task branch 自動作成・PR 作成・pr_number 記録・review_finding 記録・fix subtask 生成・summary 还流・AI は Done/main merge しない・人間が最終 Done 判断 | §3, §6（全フローの完了定義） |

---

### 参照
- ワークフロー図: `docs/images/workflow_and_basic_data.excalidraw.png`
- Git branch 図: `docs/images/git_branch.excalidraw.png`
- 全体参考図: `docs/images/ai_development_workflow.excalidraw.png`
- 実装 TODO: `TODO.md`
- 仕様書（画像参照のみ）: `docs/SPECIFICATION.md`
- Implementer 詳細: `docs/design/11-implementer.md`
