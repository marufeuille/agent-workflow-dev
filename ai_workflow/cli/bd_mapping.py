"""5スキーマ dict ↔ bd issue の双方向マッピング。

状態概念を bd のスロットに責務ごとに分離して格納する:
- type        : エンティティ種別（不変）beads_story / beads_task / beads_subtask / review_finding
- status      : ライフサイクル（subtask: ready→open / in_progress / closed。finding: open→open / fixed→closed）
- labels      : 恒久タグ（kind:* / severity:* / phase:* / entity 名）
- metadata    : 構造化データ（scope / files / refs / instructions / input_refs / output_refs / pr_numbers …）
- parent      : 階層（task→story, subtask→task, finding→task）
- external-ref: 外部ID（story の sc-<id>）

schema 準拠の正（kind / severity / subtask.status / finding.status / current_phase）は
metadata にも保持し、bd→schema 変換時にラベル/status と合わせて復元する。
"""

from __future__ import annotations

from .common import drop_none

# エンティティ種別 ↔ bd type
TYPE_STORY = "beads_story"
TYPE_TASK = "beads_task"
TYPE_SUBTASK = "beads_subtask"
TYPE_FINDING = "review_finding"

# subtask.status ↔ bd status（ready は bd の open + blocker 無しで表現）
SUBTASK_STATUS_TO_BD = {"ready": "open", "in_progress": "in_progress", "closed": "closed"}
BD_TO_SUBTASK_STATUS = {"open": "ready", "in_progress": "in_progress", "closed": "closed"}

# finding.status ↔ bd status（bd に fixed は無いので closed で代用。正は metadata.status）
FINDING_STATUS_TO_BD = {"open": "open", "fixed": "closed"}
BD_TO_FINDING_STATUS = {"open": "open", "closed": "fixed"}

TASK_PHASES = ["planning", "implementation", "review", "verified", "done"]
SUBTASK_KINDS = ["implement", "review", "fix", "verify", "summarize"]
FINDING_SEVERITIES = ["must_fix", "should_fix", "nit", "question"]
FINDING_STATUSES = ["open", "fixed"]
SUBTASK_STATUSES = ["ready", "in_progress", "closed"]


def _label_value(labels: list[str], prefix: str) -> str | None:
    """labels から `<prefix>:<value>` を探し value を返す。"""
    p = f"{prefix}:"
    for lab in labels or []:
        if lab.startswith(p):
            return lab[len(p) :]
    return None


def _deps_for_create(depends_on: list[str] | None) -> list[str] | None:
    """beads_task.depends_on（自 issue が依存する task ID 列）→ bd deps 'blocks:<id>'。
    'blocks:<id>' は「<id> が自 issue をブロック（自 issue は <id> 完了まで待つ）」を意味する。
    """
    if not depends_on:
        return None
    return [f"blocks:{d}" for d in depends_on]


# ----------------------------------------------------------------------
# schema dict → bd create 引数
# ----------------------------------------------------------------------
def story_to_create_args(story_id: str, shortcut_story_id: str, title: str) -> dict:
    return {
        "type": TYPE_STORY,
        "id": story_id,
        "title": title,
        "force": True,
        "labels": ["story"],
        "external_ref": shortcut_story_id,
        "metadata": drop_none(
            {
                "beads_story_id": story_id,
                "shortcut_story_id": shortcut_story_id,
                "title": title,
            }
        ),
    }


def task_to_create_args(task: dict) -> dict:
    return {
        "type": TYPE_TASK,
        "id": task["id"],
        "title": task["title"],
        "force": True,
        "labels": ["task"],
        "deps": _deps_for_create(task.get("depends_on")),
        "metadata": drop_none(
            {
                "shortcut_story_id": task["shortcut_story_id"],
                "planned_pr_scope": task["planned_pr_scope"],
                "acceptance_refs": task["acceptance_refs"],
                "expected_files": task["expected_files"],
                "branch_name": task.get("branch_name"),
                "pr_numbers": task.get("pr_numbers", []),
                "current_phase": task.get("current_phase", "planning"),
                "depends_on": task.get("depends_on", []),
            }
        ),
    }


def subtask_to_create_args(st: dict) -> dict:
    return {
        "type": TYPE_SUBTASK,
        "id": st["id"],
        "title": f"[{st['kind']}] {st['parent_task_id']}",
        "force": True,
        "labels": [f"kind:{st['kind']}", "subtask"],
        "metadata": drop_none(
            {
                "kind": st["kind"],
                "parent_task_id": st["parent_task_id"],
                "instructions": st.get("instructions"),
                "input_refs": st.get("input_refs"),
                "output_refs": st.get("output_refs"),
                "status": st["status"],
            }
        ),
    }


def finding_to_create_args(f: dict) -> dict:
    return {
        "type": TYPE_FINDING,
        "id": f["id"],
        "title": f"[{f['severity']}] {f['file']}",
        "force": True,
        "labels": [f"severity:{f['severity']}", "finding"],
        "metadata": drop_none(
            {
                "task_id": f["task_id"],
                "severity": f["severity"],
                "category": f["category"],
                "file": f["file"],
                "line": f.get("line"),
                "description": f["description"],
                "suggested_fix": f.get("suggested_fix"),
                "status": f["status"],
            }
        ),
    }


# ----------------------------------------------------------------------
# bd show --json → schema dict
# ----------------------------------------------------------------------
def bd_to_task(show: dict) -> dict:
    md = show.get("metadata", {}) or {}
    labels = show.get("labels", []) or []
    result = {
        "id": show["id"],
        "shortcut_story_id": md.get("shortcut_story_id"),
        "title": show.get("title"),
        "planned_pr_scope": md.get("planned_pr_scope"),
        "acceptance_refs": md.get("acceptance_refs", []),
        "expected_files": md.get("expected_files", []),
        "pr_numbers": md.get("pr_numbers", []),
        "current_phase": _label_value(labels, "phase") or md.get("current_phase", "planning"),
        "depends_on": md.get("depends_on", []),
    }
    if md.get("branch_name"):
        result["branch_name"] = md["branch_name"]
    return drop_none(result)


def bd_to_subtask(show: dict) -> dict:
    md = show.get("metadata", {}) or {}
    labels = show.get("labels", []) or []
    kind = _label_value(labels, "kind") or md.get("kind")
    status = BD_TO_SUBTASK_STATUS.get(show.get("status", "open"), show.get("status"))
    if md.get("status") in SUBTASK_STATUSES:
        status = md["status"]
    result = {
        "id": show["id"],
        "kind": kind,
        "status": status,
        "parent_task_id": show.get("parent") or md.get("parent_task_id"),
    }
    if md.get("instructions"):
        result["instructions"] = md["instructions"]
    if md.get("input_refs"):
        result["input_refs"] = md["input_refs"]
    if md.get("output_refs"):
        result["output_refs"] = md["output_refs"]
    return drop_none(result)


def bd_to_finding(show: dict) -> dict:
    md = show.get("metadata", {}) or {}
    labels = show.get("labels", []) or []
    severity = _label_value(labels, "severity") or md.get("severity")
    status = BD_TO_FINDING_STATUS.get(show.get("status", "open"), show.get("status"))
    if md.get("status") in FINDING_STATUSES:
        status = md["status"]
    result = {
        "id": show["id"],
        "task_id": show.get("parent") or md.get("task_id"),
        "severity": severity,
        "category": md.get("category"),
        "file": md.get("file"),
        "description": md.get("description"),
        "status": status,
    }
    if md.get("line") is not None:
        result["line"] = md["line"]
    if md.get("suggested_fix"):
        result["suggested_fix"] = md["suggested_fix"]
    return drop_none(result)


# ----------------------------------------------------------------------
# planned_pr_task → beads_task / beads_subtask の materialize
# ----------------------------------------------------------------------
def materialize_task(planned: dict, task_id: str, shortcut_story_id: str) -> dict:
    """planned_pr_task から beads_task を生成（id 採番・current_phase=planning）。"""
    return {
        "id": task_id,
        "shortcut_story_id": shortcut_story_id,
        "title": planned["title"],
        "planned_pr_scope": planned["planned_pr_scope"],
        "acceptance_refs": planned["acceptance_refs"],
        "expected_files": planned["expected_files"],
        "pr_numbers": [],
        "current_phase": "planning",
        "depends_on": planned.get("depends_on", []),
    }


def materialize_subtask(
    subtask_id: str,
    parent_task_id: str,
    kind: str,
    instructions: str | None = None,
    *,
    input_refs: dict | None = None,
) -> dict:
    return drop_none(
        {
            "id": subtask_id,
            "kind": kind,
            "status": "ready",
            "parent_task_id": parent_task_id,
            "instructions": instructions,
            "input_refs": input_refs,
        }
    )
