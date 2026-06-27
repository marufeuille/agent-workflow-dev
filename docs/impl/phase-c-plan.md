# フェーズC ロードマップ: wrapper CLI（TODO大項目 8-10）

本ファイルは**別セッションでフェーズCを始めるための引き継ぎ**。「何を達成すべきか」の抽象レベルに留め、細かい実装詳細・コマンド設計・マッピングの詰めは次セッションで行う前提。

前提資料（必ず先に読むこと）:
- [TODO.md](../../TODO.md) — 大項目8-10 に各 CLI の**コマンド仕様**が具体例付きで書かれている（これが要件の正）
- [docs/design/00-overview.md](../design/00-overview.md) — データモデル・ワークフロー・セーフティガード・各 agent の CLI 使用箇所
- [docs/impl/phase-b.md](phase-b.md) — フェーズB成果とフェーズC引き継ぎ注記
- `.ai-workflow/schemas/` — CLI が扱う5スキーマ
- `ai_workflow/` — 共通モジュール（`config.load_config`, `schema_validator.validate`）

---

## 1. フェーズCの目的（何を達成すべきか）

5つの AI agent（StoryPlanner/Implementer/Reviewer/Fixer/StoryReviewer、いずれフェーズDで作成）が**外部システム（Shortcut/beads/GitHub）を直接触らず、3つの wrapper CLI を経由して操作できるようにする**。これにより:

- **セーフティを CLI 層に集約**: main 操作禁止・Shortcut Done 禁止・scope 外変更検出などを CLI で強制できる
- **agent の実装を単純化**: agent は CLI を呼ぶだけ。外部 API の知識が不要
- **テスト容易性**: CLI 経由なら fixture/mock で検証できる

---

## 2. スコープ（TODO大項目）

| 大項目 | CLI | 達成目標（What） |
|--------|-----|------------------|
| 8 | `bin/sc-story` | Shortcut Story の取得 / コメント / state 更新 / beads_story_id 記録。**Done 遷移を禁止**するガード付き |
| 9 | `bin/bdw` | beads 上の story / task / subtask / finding の CRUD。**5スキーマに準拠した入出力**。`bd` CLI をラップ |
| 10 | `bin/ghw` | story/task branch 作成、PR 作成・取得・コメント・CI 状態、final PR 作成。**main 宛て PR 作成・merge を禁止**するガード付き |

各 CLI のコマンド仕様は **TODO.md 大項目8-10 のコードブロック**が正。これを満たすこと。

---

## 3. 共通方針（プロジェクト全体の合意・フェーズBから継承）

- **実装言語**: Python(uv)。`ai_workflow/` パッケージに共通機能を置き、各 CLI は薄いエントリポイント（`bin/<name>` → `ai_workflow.cli.<name>`）とする想定
- **テスト**: 正常系を最低限書く（フェーズBと同じ基準）
- **進め方**: フェーズ単位で「計画→実装→報告」、結果は `docs/impl/phase-c.md` に記録
- **fixture/mock ベース**: 実 token・実 repo 連携は後（フェーズA相当の人間作業）で繋ぐ。`sc-story` は offline/mock で動く作りを検討
- **スキーマ検証を必ず通す**: CLI が beads へ書き込むデータは `ai_workflow.schema_validator.validate` を経由する（フェーズB実装済み）

---

## 4. 前提・依存（フェーズC開始前に揃える/確認するもの）

1. **beads DB の初期化**: 現状 `bd` を実行すると "no beads database found"（未 init）。**embedded mode で `bd init`** が必要（TODO大項目4「beads初期化」の要素。フェーズC冒頭で対応）。
2. **Shortcut API token**: 未発行なら `sc-story` は mock モードで実装し、実連携は後回し。
3. **GitHub**: `gh` は導入済み（v2.92.0）。`gh auth status` で認証確認。PR 作成は fixture repo または dry-run で検証。

---

## 5. マッピング方針の方向性（詳細は次セッションで設計）

フェーズBの調査で、**`bd` は1つの "issue" に複数の属性を付与して表現するモデル**と分かった（階層コマンド task/subtask/finding はない）。表現力は十分:

- `--type`: issue 種別（`bug|feature|task|epic|chore|decision`、custom type 設定可）→ エンティティ種別
- `--status`: open/in_progress/closed 系 → subtask の status 等
- `set-state <dimension>=<value>`: 操作的状態ラベル → kind / current_phase / severity の表現候補
- `--metadata` / `--set-metadata`: JSON または key=value → planned_pr_scope / expected_files / acceptance_refs 等の構造化データ
- `--labels`: タグ → severity / category 等
- `--parent`: 階層（story→task→subtask の親子）
- `--deps` / `bd link`: 依存関係（depends_on / blocks）
- `--external-ref`: 外部参照（`sc-123` / `gh-456`）→ Shortcut Story ID / PR 番号の紐付け
- `--acceptance`: acceptance criteria
- 全コマンドに `--json` 出力あり（wrapper が parse しやすい）

**「5スキーマの各フィールドを bd のどの属性に割り当てるか」は次セッション冒頭で設計し、`docs/impl/phase-c.md`（または `docs/design/bd-mapping.md`）に記録すること。** 設計の前提として、実際に `bd init` → `bd create` → `bd show --json` で issue の JSON 構造を実物確認することを推奨。

---

## 6. 完了定義（Definition of Done）

- [ ] `bin/sc-story`, `bin/bdw`, `bin/ghw` が TODO.md 大項目8-10 のコマンド仕様を満たす
- [ ] セーフティガードが CLI 層に実装されている（sc-story: Done禁止 / ghw: main直接PR・merge禁止）
- [ ] bdw の入出力が5スキーマに準拠し、`schema_validator` で検証される
- [ ] 各 CLI の正常系テストが最低限ある（offline/mock で動く）
- [ ] 5スキーマ → bd issue へのマッピング設計が文書化されている
- [ ] `docs/impl/phase-c.md`（実装ログ）が作成され、TODO.md 大項目8-10 が完了化されている

---

## 7. フェーズC完了後の接続

- フェーズD（大項目11-13）: `CLAUDE.md` 詳細化 / `.claude/agents/*.md`（5エージェント）/ `.claude/commands/*.md`（5コマンド）が、これら wrapper CLI を呼び出す形で実装される
- フェーズE（大項目14-20）: 各エージェントの検証環境。fixture Story で `/story-plan` → `/work-next` → `/review-pr` → `/fix-findings` → `/story-review` を回す際に、このフェーズCの CLI が使われる

---

## 8. 注意・リスク

- **マッピング設計が最大の設計ポイント**: 5スキーマと bd issue の対応を間違えると、フェーズD/E で手戻りが大きい。慎重に。
- **bd のバージョン**: v1.0.4。コマンド体系が将来変わる可能性あり。実装時の `bd --version` を記録すること。
- **セーフティの二重化**: CLI 層のガードに加え、CLAUDE.md の不変ルール（フェーズBで記載済み）と併用して担保する。
