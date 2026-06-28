"""expected_files スコープ検査ユーティリティ（大項目20）。

Reviewer が expected_files 外の変更を検出するために使う。
fnmatch（glob）パターンで expected_files を評価し、
パターン外の変更ファイルを返す。

使い方（Reviewer の finding 生成例）:
    outside = files_outside_scope(changed_files, task["expected_files"])
    if outside:
        # scope 外変更の finding を作成
"""
from __future__ import annotations

import fnmatch


def files_outside_scope(changed_files: list[str], expected_files: list[str]) -> list[str]:
    """changed_files のうち expected_files のいずれのパターンにも一致しないものを返す。"""
    return [
        f for f in changed_files
        if not any(fnmatch.fnmatch(f, pat) for pat in expected_files)
    ]


def is_within_scope(changed_files: list[str], expected_files: list[str]) -> bool:
    """すべての変更ファイルが expected_files の範囲内かを返す。"""
    return len(files_outside_scope(changed_files, expected_files)) == 0
