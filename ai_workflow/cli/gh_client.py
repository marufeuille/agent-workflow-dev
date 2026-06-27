"""GitHub（gh CLI / git）のラッパ。

ghw は story/task branch 作成と PR 操作（作成・取得・コメント・CI 状態）を担う。
main 宛て PR 作成・merge の禁止は ghw.py のガード層で強制し、ここでは純粋な
API 呼出（と dry-run 合成応答）のみを担う。

dry-run モード（GhClient(dry_run=True)）では git/gh を呼ばず合成応答を返す。
テストは dry-run で検証し、実 repo への作用はフェーズCのスコープ外。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any


class GhError(Exception):
    """gh / git コマンドの失敗。"""


class GhClient:
    def __init__(self, *, dry_run: bool = False, cwd: str | None = None) -> None:
        self.dry_run = dry_run
        self.cwd = cwd or os.getcwd()

    def _run(self, cmd: list[str], *, want_json: bool = False) -> Any:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=self.cwd)
        if proc.returncode != 0:
            err = proc.stderr.strip() or proc.stdout.strip()
            raise GhError(err or f"{' '.join(cmd)} failed (exit {proc.returncode})")
        if not want_json:
            return proc.stdout.strip()
        out = proc.stdout.strip()
        return json.loads(out) if out else {}

    # ------------------------------------------------------------------
    # branch
    # ------------------------------------------------------------------
    def create_branch(self, name: str, from_ref: str) -> dict:
        if self.dry_run:
            return {"branch": name, "from": from_ref, "dry_run": True}
        self._run(["git", "checkout", "-b", name, from_ref])
        return {"branch": name, "from": from_ref}

    # ------------------------------------------------------------------
    # pr
    # ------------------------------------------------------------------
    def pr_create(self, base: str, head: str, title: str, body: str) -> dict:
        if self.dry_run:
            return {"number": 0, "base": base, "head": head, "title": title, "dry_run": True}
        out = self._run(
            [
                "gh", "pr", "create",
                "--base", base, "--head", head,
                "--title", title, "--body", body,
            ]
        )
        m = re.search(r"/pull/(\d+)", out)
        number = int(m.group(1)) if m else 0
        return {"number": number, "base": base, "head": head, "url": out}

    def pr_view(self, number: int) -> dict:
        if self.dry_run:
            return {
                "number": number,
                "state": "OPEN",
                "baseRefName": "",
                "headRefName": "",
                "dry_run": True,
            }
        return self._run(
            [
                "gh", "pr", "view", str(number),
                "--json", "number,state,baseRefName,headRefName,title,url,mergeable",
            ],
            want_json=True,
        )

    def pr_comment(self, number: int, body: str) -> dict:
        if self.dry_run:
            return {"number": number, "commented": True, "dry_run": True}
        self._run(["gh", "pr", "comment", str(number), "--body", body])
        return {"number": number, "commented": True}

    def pr_checks(self, number: int) -> dict:
        if self.dry_run:
            return {"number": number, "status": "pending", "dry_run": True}
        data = self._run(
            ["gh", "pr", "view", str(number), "--json", "statusCheckRollup"],
            want_json=True,
        )
        return {"number": number, "checks": data.get("statusCheckRollup", [])}
