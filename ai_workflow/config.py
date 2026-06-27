"""workflow 設定 (.ai-workflow/config.yaml) のローダ。

Shortcut の State 対応・GitHub 設定・計画ポリシー・スキーマ位置を型付きで扱う。
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(".ai-workflow/config.yaml")


@dataclass
class ShortcutStates:
    """Shortcut Story の State 名（ワークスペースごとに表記が異なる前提）。"""

    backlog: str = "Backlog"
    ready: str = "Ready"
    planning: str = "Planning"
    doing: str = "Doing"
    in_review: str = "In Review"
    blocked: str = "Blocked"
    done: str = "Done"


@dataclass
class GithubConfig:
    default_branch: str = "main"
    story_branch_prefix: str = "story"
    task_branch_prefix: str = "agent"
    allow_ai_merge_to_main: bool = False
    allow_ai_mark_shortcut_done: bool = False


@dataclass
class PlanningPolicy:
    pr_granularity: str = "reviewable_change_set"
    branch_strategy: str = "story_branch"
    max_expected_prs: int = 5
    prefer_separate_refactor_pr: bool = True
    require_tests_per_pr: bool = True


@dataclass
class WorkflowConfig:
    shortcut_states: ShortcutStates = field(default_factory=ShortcutStates)
    github: GithubConfig = field(default_factory=GithubConfig)
    planning_policy: PlanningPolicy = field(default_factory=PlanningPolicy)
    schemas_dir: str = ".ai-workflow/schemas"


def _coerce(dataclass_type, raw: dict):
    """raw のうち dataclass_type が持つフィールドだけを取り出して生成する。

    config.yaml に未知のキーがあってもエラーにしないための緩いマッピング。
    """
    known = {f.name for f in fields(dataclass_type)}
    return dataclass_type(**{k: v for k, v in raw.items() if k in known})


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> WorkflowConfig:
    """config.yaml を読み込み WorkflowConfig を返す。"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"config not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    states = (raw.get("shortcut") or {}).get("states") or {}
    github = raw.get("github") or {}
    policy = raw.get("planning_policy") or {}
    schemas = raw.get("schemas") or {}

    return WorkflowConfig(
        shortcut_states=_coerce(ShortcutStates, states),
        github=_coerce(GithubConfig, github),
        planning_policy=_coerce(PlanningPolicy, policy),
        schemas_dir=schemas.get("dir", ".ai-workflow/schemas"),
    )
