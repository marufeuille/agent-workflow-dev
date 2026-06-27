"""bd CLI の subprocess ラッパ。

bd（beads v1.0.4）は「単一 issue に type/status/label/metadata/parent/deps を
付与するフラットモデル」。本モジュールはその操作を型付きメソッドとして提供し、
JSON 出力の parse とエラー処理を隠蔽する。

工程0（実物確認）で判明した bd の挙動:
- `create` で `--id` と `--parent` は排他（親は create 後に `update --parent` で後付け）。
- `create` に `--status` は無い（デフォルト open。変更は `update --status` / `close`）。
- `create --json` は単オブジェクト、`show/list/update/close/children --json` は配列。
- エラーは stdout の `{"error": "..."}` または stderr の `Error: ...`。
  `Warning: auto-export: ...` は git 連携の副次的警告で無視してよい。
- `set-state <id> dim=value` は label `dim:value` を付与し event bead を記録する。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any


class BdError(Exception):
    """bd コマンドの失敗。"""


_ID_SEQ_RE = re.compile(r".*-(\d+)$")


class BdClient:
    """bd CLI を呼び出すクライアント。BEADS_DIR で DB の場所を制御する。"""

    def __init__(
        self,
        directory: str | os.PathLike[str] | None = None,
        *,
        env: dict[str, str] | None = None,
    ) -> None:
        self.env: dict[str, str] = dict(os.environ)
        if directory is not None:
            self.env["BEADS_DIR"] = str(directory)
        if env:
            self.env.update(env)
        self.env.setdefault("BD_NON_INTERACTIVE", "1")

    def _run(self, args: list[str], *, want_json: bool = True) -> Any:
        cmd = ["bd", *args]
        if want_json:
            cmd.append("--json")
        proc = subprocess.run(cmd, capture_output=True, text=True, env=self.env)
        if proc.returncode != 0:
            raise BdError(self._extract_error(proc) or f"bd failed (exit {proc.returncode})")
        if not want_json:
            return proc.stdout.strip()
        out = proc.stdout.strip()
        if not out:
            return None
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            return out
        # bd は失敗を {"error": "...", "schema_version": 1} で返すことがある
        if isinstance(data, dict) and "error" in data and "issue_type" not in data:
            raise BdError(str(data["error"]))
        return data

    @staticmethod
    def _extract_error(proc: subprocess.CompletedProcess[str]) -> str | None:
        """stderr から意味のあるエラーを抽出。auto-export 等の Warning: は無視。"""
        for line in (proc.stderr or "").splitlines():
            s = line.strip()
            if not s or s.startswith("Warning:") or s.startswith("warning:"):
                continue
            return s
        return None

    # ------------------------------------------------------------------
    # create / update / state / close
    # ------------------------------------------------------------------
    def create(
        self,
        *,
        type: str,
        id: str,
        title: str,
        labels: list[str] | None = None,
        metadata: dict | None = None,
        external_ref: str | None = None,
        deps: list[str] | None = None,
        force: bool = True,
    ) -> dict:
        """issue を作成。--id と --parent は排他のため、親は別途 set_parent で設定すること。"""
        args = ["create", title, "--type", type, "--id", id]
        if force:
            args.append("--force")
        if labels:
            args += ["--labels", ",".join(labels)]
        if metadata is not None:
            args += ["--metadata", json.dumps(metadata)]
        if external_ref:
            args += ["--external-ref", external_ref]
        if deps:
            args += ["--deps", ",".join(deps)]
        return self._run(args)

    def update(
        self,
        id: str,
        *,
        status: str | None = None,
        metadata: dict | None = None,
        set_metadata: list[str] | None = None,
        unset_metadata: list[str] | None = None,
        parent: str | None = None,
        clear_parent: bool = False,
        add_label: list[str] | None = None,
        remove_label: list[str] | None = None,
        set_labels: list[str] | None = None,
        external_ref: str | None = None,
        title: str | None = None,
    ) -> dict:
        args = ["update", id]
        if status:
            args += ["--status", status]
        if metadata is not None:
            args += ["--metadata", json.dumps(metadata)]
        for kv in set_metadata or []:
            args += ["--set-metadata", kv]
        for k in unset_metadata or []:
            args += ["--unset-metadata", k]
        if clear_parent:
            args += ["--parent", ""]
        elif parent is not None:
            args += ["--parent", parent]
        for lab in add_label or []:
            args += ["--add-label", lab]
        for lab in remove_label or []:
            args += ["--remove-label", lab]
        if set_labels is not None:
            args += ["--set-labels", ",".join(set_labels)]
        if external_ref is not None:
            args += ["--external-ref", external_ref]
        if title is not None:
            args += ["--title", title]
        return self._run(args)

    def set_parent(self, id: str, parent_id: str) -> dict:
        """親 issue を後付け（create の --id と --parent 排他を回避）。"""
        return self.update(id, parent=parent_id)

    def set_state(self, id: str, dimension: str, value: str, *, reason: str | None = None) -> dict:
        args = ["set-state", id, f"{dimension}={value}"]
        if reason:
            args += ["--reason", reason]
        return self._run(args)

    def close(self, id: str, *, reason: str | None = None) -> dict:
        args = ["close", id]
        if reason:
            args += ["--reason", reason]
        return self._run(args)

    # ------------------------------------------------------------------
    # query
    # ------------------------------------------------------------------
    def show(self, id: str) -> dict | None:
        """1件取得。show --json は配列を返すので先頭を返す。無ければ None。"""
        data = self._run(["show", id])
        if isinstance(data, list):
            return data[0] if data else None
        return data

    def list(
        self,
        *,
        type: str | None = None,
        parent: str | None = None,
        label: list[str] | None = None,
        status: str | None = None,
        ready: bool = False,
        all_: bool = False,
        metadata_field: list[str] | None = None,
    ) -> list[dict]:
        args = ["list", "--flat"]
        if type:
            args += ["--type", type]
        if parent:
            args += ["--parent", parent]
        if label:
            args += ["--label", ",".join(label)]
        if status:
            args += ["--status", status]
        if ready:
            args.append("--ready")
        if all_:
            args.append("--all")
        for kv in metadata_field or []:
            args += ["--metadata-field", kv]
        data = self._run(args)
        return data if isinstance(data, list) else []

    def children(self, parent_id: str) -> list[dict]:
        return self.list(parent=parent_id, all_=True)

    def types(self) -> dict:
        return self._run(["types"])

    # ------------------------------------------------------------------
    # setup
    # ------------------------------------------------------------------
    def init(self, *, prefix: str = "bd") -> None:
        self._run(
            ["init", "--non-interactive", "--prefix", prefix, "--skip-agents", "--skip-hooks"],
            want_json=False,
        )

    def config_set(self, key: str, value: str) -> None:
        self._run(["config", "set", key, value], want_json=False)

    def disable_auto_export(self) -> None:
        """テスト環境等で auto-export の git add 警告を消す。"""
        self.config_set("export.auto", "false")

    # ------------------------------------------------------------------
    # id 採番
    # ------------------------------------------------------------------
    def next_id(self, id_prefix: str, *, issue_type: str | None = None) -> str:
        """同 prefix の既存 ID の最大連番 + 1 を採番。
        例: id_prefix='bd-task' → 既存 'bd-task-001'..→ 'bd-task-002'。
        """
        existing = self.list(type=issue_type, all_=True) if issue_type else self.list(all_=True)
        max_n = 0
        pat = re.compile(re.escape(id_prefix) + r"-(\d+)$")
        for it in existing:
            m = pat.match(it.get("id", ""))
            if m:
                max_n = max(max_n, int(m.group(1)))
        return f"{id_prefix}-{max_n + 1:03d}"
