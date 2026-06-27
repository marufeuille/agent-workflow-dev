"""bin/bdw: beads（bd）wrapper CLI のエントリポイント。

5スキーマ（story / task / subtask / finding）を bd の issue モデルへマッピングして
操作する。入力は必ず schema_validator で検証してから bd へ書き込む。

コマンド（TODO 大項目9 + 設計書整合の拡張2件）:
  init
  story create --shortcut-story <id> --title <title>
  task create --file <planned.yaml> --story <bd-story-id> [--no-initial-subtasks]
  task link-pr <id> --pr <num>
  task set-phase <id> <phase>            # 拡張
  subtask create --file <subtask.yaml>
  ready --role <role> [--list]
  close <subtask-id> --output <file>
  finding create --file <finding.yaml>
  finding list --task <task-id> --open
  finding update <id> --status <status>  # 拡張
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from ai_workflow.config import WorkflowConfig

from . import bd_mapping as M
from . import bd_setup
from .bd_client import BdClient, BdError
from .common import beads_dir, die, emit_json, read_yaml_file
from .guards import GuardError, require_valid

# role（agent 役割名）→ subtask kind
ROLE_TO_KIND = {
    "implement": "implement", "implementer": "implement",
    "review": "review", "reviewer": "review",
    "fix": "fix", "fixer": "fix",
    "verify": "verify",
    "summarize": "summarize",
}

TASK_CREATE_KIND = {"implement", "review"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bdw", description="beads wrapper CLI")
    parser.add_argument("--json", action="store_true", default=True, help="JSON 出力（既定）")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="bd DB を初期化し custom type を登録")

    p_story = sub.add_parser("story")
    story_sub = p_story.add_subparsers(dest="subcommand", required=True)
    p = story_sub.add_parser("create")
    p.add_argument("--shortcut-story", required=True)
    p.add_argument("--title", required=True)

    p_task = sub.add_parser("task")
    task_sub = p_task.add_subparsers(dest="subcommand", required=True)
    p = task_sub.add_parser("create")
    p.add_argument("--file", required=True)
    p.add_argument("--story", required=True, help="親 beads_story の id")
    p.add_argument("--no-initial-subtasks", action="store_true")
    p = task_sub.add_parser("link-pr")
    p.add_argument("id")
    p.add_argument("--pr", type=int, required=True)
    p = task_sub.add_parser("set-phase")
    p.add_argument("id")
    p.add_argument("phase", choices=M.TASK_PHASES)

    p_subtask = sub.add_parser("subtask")
    subtask_sub = p_subtask.add_subparsers(dest="subcommand", required=True)
    p = subtask_sub.add_parser("create")
    p.add_argument("--file", required=True)

    p = sub.add_parser("ready")
    p.add_argument("--role", required=True, choices=sorted(ROLE_TO_KIND))
    p.add_argument("--list", action="store_true", help="claim せず一覧のみ返す")

    p = sub.add_parser("close")
    p.add_argument("id")
    p.add_argument("--output", required=True, help="output_refs を読む YAML/JSON ファイル")

    p_finding = sub.add_parser("finding")
    finding_sub = p_finding.add_subparsers(dest="subcommand", required=True)
    p = finding_sub.add_parser("create")
    p.add_argument("--file", required=True)
    p = finding_sub.add_parser("list")
    p.add_argument("--task", required=True)
    p.add_argument("--open", action="store_true")
    p = finding_sub.add_parser("update")
    p.add_argument("id")
    p.add_argument("--status", required=True, choices=["open", "fixed"])

    return parser


# ----------------------------------------------------------------------
# handlers
# ----------------------------------------------------------------------
def _merge_metadata(bd: BdClient, id: str, updates: dict) -> dict:
    """既存 metadata を読み、updates をマージして全体を書き戻す（配列・ネスト対応）。"""
    cur = bd.show(id) or {}
    md = dict(cur.get("metadata", {}) or {})
    md.update(updates)
    return bd.update(id, metadata=md)


def h_init(bd: BdClient) -> dict:
    return bd_setup.run(bd)


def h_story_create(bd: BdClient, cfg: WorkflowConfig, args) -> dict:
    story_id = bd.next_id("bd-story", issue_type=M.TYPE_STORY)
    bd.create(**M.story_to_create_args(story_id, args.shortcut_story, args.title))
    return {"beads_story_id": story_id, "shortcut_story_id": args.shortcut_story}


def h_task_create(bd: BdClient, cfg: WorkflowConfig, args) -> dict:
    planned = read_yaml_file(args.file)
    require_valid(planned, "planned_pr_task", cfg.schemas_dir)

    # 親 story から shortcut_story_id を解決
    story = bd.show(args.story)
    if not story:
        raise BdError(f"story not found: {args.story}")
    shortcut_story_id = (story.get("metadata", {}) or {}).get("shortcut_story_id") or story.get("external_ref")
    if not shortcut_story_id:
        raise BdError(f"story {args.story} に shortcut_story_id がありません")

    task_id = bd.next_id("bd-task", issue_type=M.TYPE_TASK)
    task = M.materialize_task(planned, task_id, shortcut_story_id)
    require_valid(task, "beads_task", cfg.schemas_dir)

    bd.create(**M.task_to_create_args(task))
    bd.set_parent(task_id, args.story)
    bd.set_state(task_id, "phase", "planning", reason="task created")

    subtasks: list[dict] = []
    if not args.no_initial_subtasks:
        for init in planned.get("initial_subtasks", []):
            kind = init.get("kind")
            if kind not in TASK_CREATE_KIND:
                continue
            sid = bd.next_id(f"bd-subtask-{kind}", issue_type=M.TYPE_SUBTASK)
            sub = M.materialize_subtask(sid, task_id, kind, init.get("instructions"))
            require_valid(sub, "beads_subtask", cfg.schemas_dir)
            bd.create(**M.subtask_to_create_args(sub))
            bd.set_parent(sid, task_id)
            subtasks.append(sub)

    return {"task": task, "subtasks": subtasks}


def h_task_link_pr(bd: BdClient, cfg: WorkflowConfig, args) -> dict:
    cur = bd.show(args.id) or {}
    md = cur.get("metadata", {}) or {}
    prs = sorted(set(md.get("pr_numbers", []) or []) | {args.pr})
    _merge_metadata(bd, args.id, {"pr_numbers": prs})
    return {"task_id": args.id, "pr_numbers": prs}


def h_task_set_phase(bd: BdClient, cfg: WorkflowConfig, args) -> dict:
    bd.set_state(args.id, "phase", args.phase, reason="phase update")
    _merge_metadata(bd, args.id, {"current_phase": args.phase})
    return {"task_id": args.id, "phase": args.phase}


def h_subtask_create(bd: BdClient, cfg: WorkflowConfig, args) -> dict:
    st = read_yaml_file(args.file)
    require_valid(st, "beads_subtask", cfg.schemas_dir)
    bd.create(**M.subtask_to_create_args(st))
    bd.set_parent(st["id"], st["parent_task_id"])
    return {"subtask": st}


def h_ready(bd: BdClient, cfg: WorkflowConfig, args) -> Any:
    kind = ROLE_TO_KIND[args.role]
    rows = bd.list(
        type=M.TYPE_SUBTASK, label=[f"kind:{kind}"], status="open", ready=True
    )
    if args.list or not rows:
        return [M.bd_to_subtask(r) for r in rows]
    # 1件 claim（ready → in_progress）
    picked = rows[0]
    bd.update(picked["id"], status="in_progress", set_metadata=["status=in_progress"])
    return M.bd_to_subtask(bd.show(picked["id"]))


def h_close(bd: BdClient, cfg: WorkflowConfig, args) -> dict:
    output = read_yaml_file(args.output) or {}
    if not isinstance(output, dict):
        raise BdError(f"--output は dict の YAML/JSON が必要: {args.output}")
    _merge_metadata(bd, args.id, {"output_refs": output, "status": "closed"})
    bd.close(args.id, reason="subtask closed")
    return {"subtask_id": args.id, "closed": True, "output_refs": output}


def h_finding_create(bd: BdClient, cfg: WorkflowConfig, args) -> dict:
    f = read_yaml_file(args.file)
    require_valid(f, "review_finding", cfg.schemas_dir)
    bd.create(**M.finding_to_create_args(f))
    bd.set_parent(f["id"], f["task_id"])
    return {"finding": f}


def h_finding_list(bd: BdClient, cfg: WorkflowConfig, args) -> list[dict]:
    if not args.open:
        # 仕様上 --open 想定だが、未指定時は open を含む全件（closed 含む）を返さないよう open に固定
        rows = bd.list(type=M.TYPE_FINDING, parent=args.task, all_=True)
    else:
        rows = bd.list(type=M.TYPE_FINDING, parent=args.task, status="open")
    return [M.bd_to_finding(r) for r in rows]


def h_finding_update(bd: BdClient, cfg: WorkflowConfig, args) -> dict:
    if args.status == "fixed":
        # reopen 中の場合を考慮し status は close で表現
        _merge_metadata(bd, args.id, {"status": "fixed"})
        bd.set_state(args.id, "finding", "fixed", reason="finding fixed")
        bd.close(args.id, reason="finding fixed")
    else:  # open（reopen）
        _merge_metadata(bd, args.id, {"status": "open"})
        bd.update(args.id, status="open")
        bd.set_state(args.id, "finding", "open", reason="finding reopened")
    return {"finding_id": args.id, "status": args.status}


_HANDLERS = {
    ("init", None): lambda bd, cfg, args: h_init(bd),
    ("story", "create"): h_story_create,
    ("task", "create"): h_task_create,
    ("task", "link-pr"): h_task_link_pr,
    ("task", "set-phase"): h_task_set_phase,
    ("subtask", "create"): h_subtask_create,
    ("ready", None): h_ready,
    ("close", None): h_close,
    ("finding", "create"): h_finding_create,
    ("finding", "list"): h_finding_list,
    ("finding", "update"): h_finding_update,
}


def dispatch(args, cfg: WorkflowConfig, bd: BdClient) -> Any:
    key = (args.command, getattr(args, "subcommand", None))
    handler = _HANDLERS.get(key)
    if handler is None:
        raise BdError(f"unsupported command: {key}")
    return handler(bd, cfg, args)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    from .common import load_config

    cfg = load_config()
    bd = BdClient(directory=beads_dir())
    try:
        result = dispatch(args, cfg, bd)
    except (GuardError, BdError) as e:
        die(f"bdw: {e}")
    except FileNotFoundError as e:
        die(f"bdw: {e}")
    if result is not None:
        emit_json(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
