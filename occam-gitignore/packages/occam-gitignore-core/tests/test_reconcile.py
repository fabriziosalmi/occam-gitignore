# SPDX-License-Identifier: MIT
"""Tests for the pure reconcile layer: coverage check + managed-block merge."""

from __future__ import annotations

import pytest

from occam_gitignore_core import (
    ManagedBlockError,
    apply_managed_block,
    build_managed_block,
    missing_patterns,
)
from occam_gitignore_core.reconcile import (
    MANAGED_BLOCK_END,
    MANAGED_BLOCK_NOTICE,
    MANAGED_BLOCK_START,
)

# --------------------------------------------------------------------------- #
# missing_patterns — coverage semantics                                       #
# --------------------------------------------------------------------------- #


def test_missing_patterns_reports_absent_in_canonical_order() -> None:
    canonical = ["__pycache__/", ".env", "*.pem", "!.env.example"]
    existing = "__pycache__/\n"
    assert missing_patterns(canonical, existing) == (".env", "*.pem", "!.env.example")


def test_missing_patterns_empty_when_all_present() -> None:
    canonical = [".env", "*.key"]
    existing = "# comment\n\n.env\n*.key\ncustom-project-line\n"
    assert missing_patterns(canonical, existing) == ()


def test_missing_patterns_ignores_extra_project_lines() -> None:
    # Extra, project-specific lines must NOT cause a report: coverage, not equality.
    canonical = [".env"]
    existing = ".env\nsecrets/\n/build-artifacts/\n"
    assert missing_patterns(canonical, existing) == ()


def test_missing_patterns_ignores_comments_and_blanks_in_existing() -> None:
    canonical = ["*.pem"]
    existing = "#*.pem\n   \n"  # commented-out + blank: does NOT count as present
    assert missing_patterns(canonical, existing) == ("*.pem",)


def test_missing_patterns_strips_whitespace_before_comparing() -> None:
    canonical = ["*.key"]
    existing = "   *.key   \n"
    assert missing_patterns(canonical, existing) == ()


def test_missing_patterns_dedups_repeated_canonical() -> None:
    assert missing_patterns(["*.pem", "*.pem"], "") == ("*.pem",)


def test_missing_patterns_all_missing_for_empty_file() -> None:
    canonical = ["a", "b", "c"]
    assert missing_patterns(canonical, "") == ("a", "b", "c")


# --------------------------------------------------------------------------- #
# build_managed_block                                                          #
# --------------------------------------------------------------------------- #


def test_build_managed_block_has_markers_and_notice() -> None:
    block = build_managed_block("a\nb\n")
    lines = block.split("\n")
    assert lines[0] == MANAGED_BLOCK_START
    assert lines[1] == MANAGED_BLOCK_NOTICE
    assert lines[-1] == MANAGED_BLOCK_END
    assert "a" in lines
    assert "b" in lines


def test_build_managed_block_trims_body_edges_keeps_interior_blanks() -> None:
    block = build_managed_block("\n\nx\n\ny\n\n")
    body = block.split("\n")[2:-1]  # between notice and end marker
    assert body == ["x", "", "y"]


# --------------------------------------------------------------------------- #
# apply_managed_block — merge, not replace                                     #
# --------------------------------------------------------------------------- #


def test_apply_appends_block_to_empty_file() -> None:
    result = apply_managed_block("", "rule-a\nrule-b\n")
    assert result.startswith(MANAGED_BLOCK_START)
    assert result.endswith(MANAGED_BLOCK_END + "\n")
    assert "rule-a" in result
    assert MANAGED_BLOCK_START in result


def test_apply_preserves_lines_before_the_block() -> None:
    existing = "# my rules\nsecrets.txt\n/cache/\n"
    result = apply_managed_block(existing, "rule-a\n")
    assert "# my rules" in result
    assert "secrets.txt" in result
    assert "/cache/" in result
    # Custom content comes before the managed block.
    assert result.index("secrets.txt") < result.index(MANAGED_BLOCK_START)


def test_apply_preserves_lines_after_the_block() -> None:
    existing = (
        f"top-line\n{MANAGED_BLOCK_START}\n{MANAGED_BLOCK_NOTICE}\n"
        f"OLD\n{MANAGED_BLOCK_END}\nbottom-line\n"
    )
    result = apply_managed_block(existing, "rule-a\n")
    assert "top-line" in result
    assert "bottom-line" in result
    assert "OLD" not in result  # old block body replaced
    assert "rule-a" in result


def test_apply_replaces_existing_block_content_in_place() -> None:
    first = apply_managed_block("keep-me\n", "rule-a\nrule-b\n")
    second = apply_managed_block(first, "rule-c\n")
    assert "keep-me" in second
    assert "rule-c" in second
    assert "rule-a" not in second
    assert "rule-b" not in second
    # Exactly one block after replacement.
    assert second.count(MANAGED_BLOCK_START) == 1
    assert second.count(MANAGED_BLOCK_END) == 1


def test_apply_is_idempotent() -> None:
    body = "rule-a\nrule-b\n"
    existing = "# custom\nfoo/\n"
    once = apply_managed_block(existing, body)
    twice = apply_managed_block(once, body)
    assert once == twice


def test_apply_idempotent_with_content_after_block() -> None:
    body = "rule-a\n"
    existing = (
        f"before\n\n{MANAGED_BLOCK_START}\n{MANAGED_BLOCK_NOTICE}\n"
        f"OLD\n{MANAGED_BLOCK_END}\n\nafter\n"
    )
    once = apply_managed_block(existing, body)
    twice = apply_managed_block(once, body)
    assert once == twice
    assert "before" in once
    assert "after" in once


def test_apply_result_ends_with_single_newline() -> None:
    result = apply_managed_block("x\n\n\n", "rule-a\n")
    assert result.endswith("\n")
    assert not result.endswith("\n\n")


def test_apply_single_blank_line_separates_block_from_content() -> None:
    result = apply_managed_block("foo\n", "rule-a\n")
    assert f"foo\n\n{MANAGED_BLOCK_START}" in result


def test_apply_raises_on_start_without_end() -> None:
    with pytest.raises(ManagedBlockError, match="start marker"):
        apply_managed_block(f"{MANAGED_BLOCK_START}\nfoo\n", "rule-a\n")


def test_apply_raises_on_end_without_start() -> None:
    with pytest.raises(ManagedBlockError, match="end marker"):
        apply_managed_block(f"foo\n{MANAGED_BLOCK_END}\n", "rule-a\n")


def test_apply_deterministic_same_inputs_same_output() -> None:
    a = apply_managed_block("p\nq\n", "r\ns\n")
    b = apply_managed_block("p\nq\n", "r\ns\n")
    assert a == b
