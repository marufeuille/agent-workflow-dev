"""bin/sc-story: Shortcut Story wrapper CLI のエントリポイント（mock 完結）。

コマンド（TODO 大項目8）:
  get <story-id> --json
  comment <story-id> --file <path>
  set-state <story-id> <state>     # Done 遷移は拒否
  link <story-id> --beads-story <beads-story-id>
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from .common import die, emit_json, load_config, read_text_file
from .guards import GuardError, block_shortcut_done
from .sc_client import ShortcutError, make_client


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sc-story", description="Shortcut Story wrapper CLI")
    parser.add_argument("--mode", default=None, help="mock|real（省略時 SC_STORY_MODE env）")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("get")
    p.add_argument("id")
    p = sub.add_parser("comment")
    p.add_argument("id")
    p.add_argument("--file", required=True)
    p = sub.add_parser("set-state")
    p.add_argument("id")
    p.add_argument("state")
    p = sub.add_parser("link")
    p.add_argument("id")
    p.add_argument("--beads-story", required=True)

    return parser


def h_get(sc, cfg, args) -> dict:
    return sc.get(args.id)


def h_comment(sc, cfg, args) -> dict:
    text = read_text_file(args.file)
    return sc.comment(args.id, text)


def h_set_state(sc, cfg, args) -> dict:
    block_shortcut_done(args.state, cfg)  # Done 遷移を拒否
    return sc.set_state(args.id, args.state)


def h_link(sc, cfg, args) -> dict:
    return sc.set_metadata(args.id, {"beads_story_id": args.beads_story})


_HANDLERS = {
    "get": h_get,
    "comment": h_comment,
    "set-state": h_set_state,
    "link": h_link,
}


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.mode:
        os.environ["SC_STORY_MODE"] = args.mode
    cfg = load_config()
    sc = make_client()
    try:
        result = _HANDLERS[args.command](sc, cfg, args)
    except (GuardError, ShortcutError) as e:
        die(f"sc-story: {e}")
    except FileNotFoundError as e:
        die(f"sc-story: {e}")
    if result is not None:
        emit_json(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
