"""bin/ghw: GitHub（gh / git）wrapper CLI のエントリポイント。

story/task branch の作成と、story branch 宛ての PR 操作を担う。
セーフティ:
- task PR の base が default branch（main）なら拒否（pr create のみ）。
- final PR（story→main）の base==main は正当（人間が merge する）。
- merge コマンドは実装しない（block_ai_merge）。

コマンド（TODO 大項目10）:
  branch create-story <story-id> --from <ref> --slug <slug>
  branch create-task <story-id> <task-slug> --from <story-branch>
  pr create --base <story-branch> --head <task-branch> --body <file> [--title <title>]
  pr view <number>
  pr comment <number> --file <file>
  pr checks <number>
  pr create-final --story-branch <branch> --base main [--body <file>] [--title <title>]
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from .common import die, emit_json, read_text_file, slugify
from .gh_client import GhClient, GhError
from .guards import GuardError, block_pr_base


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ghw", description="GitHub wrapper CLI")
    parser.add_argument("--dry-run", action="store_true", help="git/gh を呼ばず合成応答を返す")
    sub = parser.add_subparsers(dest="command", required=True)

    p_branch = sub.add_parser("branch")
    branch_sub = p_branch.add_subparsers(dest="subcommand", required=True)
    p = branch_sub.add_parser("create-story")
    p.add_argument("id")
    p.add_argument("--from", dest="from_", default="main")
    p.add_argument("--slug", required=True, help="branch 名の slug 部分")
    p = branch_sub.add_parser("create-task")
    p.add_argument("id")
    p.add_argument("slug", help="task branch の slug 部分")
    p.add_argument("--from", dest="from_", required=True, help="起点の story branch")

    p_pr = sub.add_parser("pr")
    pr_sub = p_pr.add_subparsers(dest="subcommand", required=True)
    p = pr_sub.add_parser("create")
    p.add_argument("--base", required=True)
    p.add_argument("--head", required=True)
    p.add_argument("--body", required=True, help="PR 本文のファイル")
    p.add_argument("--title", default=None)
    p = pr_sub.add_parser("view")
    p.add_argument("number", type=int)
    p = pr_sub.add_parser("comment")
    p.add_argument("number", type=int)
    p.add_argument("--file", required=True)
    p = pr_sub.add_parser("checks")
    p.add_argument("number", type=int)
    p = pr_sub.add_parser("create-final")
    p.add_argument("--story-branch", required=True)
    p.add_argument("--base", default="main")
    p.add_argument("--body", default=None)
    p.add_argument("--title", default=None)

    return parser


# ----------------------------------------------------------------------
# handlers
# ----------------------------------------------------------------------
def h_branch_create_story(gh: GhClient, cfg, args) -> dict:
    name = f"{cfg.github.story_branch_prefix}/sc-{args.id}-{slugify(args.slug)}"
    return gh.create_branch(name, args.from_)


def h_branch_create_task(gh: GhClient, cfg, args) -> dict:
    name = f"{cfg.github.task_branch_prefix}/sc-{args.id}-{slugify(args.slug)}"
    return gh.create_branch(name, args.from_)


def h_pr_create(gh: GhClient, cfg, args) -> dict:
    block_pr_base(args.base, cfg)  # base==main を拒否
    title = args.title or args.head
    body = read_text_file(args.body)
    return gh.pr_create(args.base, args.head, title, body)


def h_pr_view(gh: GhClient, cfg, args) -> dict:
    return gh.pr_view(args.number)


def h_pr_comment(gh: GhClient, cfg, args) -> dict:
    body = read_text_file(args.file)
    return gh.pr_comment(args.number, body)


def h_pr_checks(gh: GhClient, cfg, args) -> dict:
    return gh.pr_checks(args.number)


def h_pr_create_final(gh: GhClient, cfg, args) -> dict:
    # final PR の base==main は正当（人間が merge する）。block_pr_base は適用しない。
    # 本コマンドは PR 作成のみ。merge コマンドは実装しない（merge は人間のみ）。
    title = args.title or f"final: {args.story_branch}"
    body = read_text_file(args.body) if args.body else f"Final PR for {args.story_branch} → {args.base}\n\nmerge は人間のみ。"
    result = gh.pr_create(args.base, args.story_branch, title, body)
    result["merge"] = "human-only"
    return result


_HANDLERS = {
    ("branch", "create-story"): h_branch_create_story,
    ("branch", "create-task"): h_branch_create_task,
    ("pr", "create"): h_pr_create,
    ("pr", "view"): h_pr_view,
    ("pr", "comment"): h_pr_comment,
    ("pr", "checks"): h_pr_checks,
    ("pr", "create-final"): h_pr_create_final,
}


def dispatch(args, cfg, gh: GhClient) -> Any:
    key = (args.command, getattr(args, "subcommand", None))
    handler = _HANDLERS.get(key)
    if handler is None:
        raise GhError(f"unsupported command: {key}")
    return handler(gh, cfg, args)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    from .common import load_config

    cfg = load_config()
    dry = args.dry_run or bool(os.environ.get("GHW_DRY_RUN"))
    gh = GhClient(dry_run=dry)
    try:
        result = dispatch(args, cfg, gh)
    except (GuardError, GhError) as e:
        die(f"ghw: {e}")
    except FileNotFoundError as e:
        die(f"ghw: {e}")
    if result is not None:
        emit_json(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
