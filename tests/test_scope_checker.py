"""scope_checker ユーティリティのテスト（大項目20）。

Reviewer が expected_files 外の変更を検出するための
files_outside_scope() / is_within_scope() を検証する。

TODO.md大項目20:
  expected_files 外の変更がある場合に Reviewer が finding を出すようにする
  planned_pr_scope 外の変更を検出する仕組みを検討する
"""

from __future__ import annotations

import pytest

from ai_workflow.cli.scope_checker import files_outside_scope, is_within_scope


# -----------------------------------------------------------------------
# 基本的なスコープ判定
# -----------------------------------------------------------------------
def test_all_files_in_scope_returns_empty():
    """全ファイルが expected_files に一致する場合、範囲外は空。"""
    changed = ["app/models/filter.py", "app/models/user.py"]
    expected = ["app/models/*"]
    assert files_outside_scope(changed, expected) == []


def test_all_files_out_of_scope_returns_all():
    """全ファイルが expected_files に一致しない場合、全件返す。"""
    changed = ["README.md", "app/api/users.py"]
    expected = ["app/models/*"]
    outside = files_outside_scope(changed, expected)
    assert "README.md" in outside
    assert "app/api/users.py" in outside


def test_mixed_scope_returns_only_outside():
    """in-scope と out-of-scope が混在する場合、out-of-scope のみを返す。"""
    changed = [
        "app/models/filter.py",      # in scope
        "app/api/filters.py",        # out of scope
        "tests/models/test_filter.py",  # out of scope
    ]
    expected = ["app/models/*"]
    outside = files_outside_scope(changed, expected)
    assert outside == ["app/api/filters.py", "tests/models/test_filter.py"]
    assert "app/models/filter.py" not in outside


# -----------------------------------------------------------------------
# glob パターンマッチング
# -----------------------------------------------------------------------
def test_glob_wildcard_matches_any_file():
    """app/api/* は app/api/ 直下のファイルにマッチする。"""
    changed = ["app/api/saved_filters.py", "app/api/users.py"]
    expected = ["app/api/*"]
    assert files_outside_scope(changed, expected) == []


def test_glob_wildcard_matches_through_subdirectory():
    """fnmatch の * はスラッシュを含む任意文字にマッチするため、サブディレクトリも包含する。"""
    changed = ["app/api/v2/foo.py"]
    expected = ["app/api/*"]
    outside = files_outside_scope(changed, expected)
    # app/api/* の * は "/" を含む文字列にマッチする（fnmatch 仕様）
    assert "app/api/v2/foo.py" not in outside


def test_multiple_patterns_all_apply():
    """複数の expected_files パターンで and ではなく or で判定される。"""
    changed = [
        "app/models/filter.py",
        "tests/api/test_filters.py",
        "README.md",
    ]
    expected = ["app/models/*", "tests/api/*"]
    outside = files_outside_scope(changed, expected)
    assert outside == ["README.md"]


def test_db_migrations_pattern():
    """db/migrations/* パターンで SQL ファイルを検出できる。"""
    changed = ["db/migrations/001_add_filters.sql", "db/seeds/filters.sql"]
    expected = ["db/migrations/*"]
    outside = files_outside_scope(changed, expected)
    assert outside == ["db/seeds/filters.sql"]


def test_exact_match_also_works():
    """パターンではなく正確なファイル名も一致する。"""
    changed = ["CLAUDE.md", "README.md"]
    expected = ["CLAUDE.md"]
    outside = files_outside_scope(changed, expected)
    assert outside == ["README.md"]


# -----------------------------------------------------------------------
# is_within_scope 検証
# -----------------------------------------------------------------------
def test_is_within_scope_returns_true_when_all_in():
    """全ファイルが scope 内なら True。"""
    changed = ["app/models/filter.py"]
    expected = ["app/models/*"]
    assert is_within_scope(changed, expected) is True


def test_is_within_scope_returns_false_when_any_out():
    """1つでも scope 外があれば False。"""
    changed = ["app/models/filter.py", "app/api/users.py"]
    expected = ["app/models/*"]
    assert is_within_scope(changed, expected) is False


def test_empty_changed_files_is_within_scope():
    """変更ファイルが空の場合は scope 内（True）。"""
    assert is_within_scope([], ["app/models/*"]) is True


def test_empty_expected_files_all_outside():
    """expected_files が空の場合は全変更ファイルが scope 外。"""
    changed = ["app/models/filter.py"]
    outside = files_outside_scope(changed, [])
    assert outside == ["app/models/filter.py"]
    assert is_within_scope(changed, []) is False


# -----------------------------------------------------------------------
# 実際の planned_pr_task fixture の expected_files で検証
# -----------------------------------------------------------------------
def test_scope_checker_with_fixture_expected_files():
    """planned_pr_task fixture の expected_files パターンで実際のファイルを検証。"""
    import yaml
    from pathlib import Path

    fixture = yaml.safe_load(
        (Path(__file__).parent / "fixtures" / "planned_pr_task.valid.yaml").read_text()
    )
    expected = fixture["expected_files"]
    # fixture は ["db/migrations/*", "app/models/*"]

    in_scope = ["db/migrations/001_saved_filters.sql", "app/models/saved_filter.py"]
    out_of_scope_files = ["app/api/saved_filters.py", "README.md", "tests/api/test_filters.py"]

    outside = files_outside_scope(in_scope + out_of_scope_files, expected)
    for f in in_scope:
        assert f not in outside
    for f in out_of_scope_files:
        assert f in outside
