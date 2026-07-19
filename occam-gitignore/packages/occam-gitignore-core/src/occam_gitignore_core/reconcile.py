# SPDX-License-Identifier: MIT
"""Reconcile a generated `.gitignore` with an existing file on disk.

Two pure operations power the CLI's drift-guard and merge workflows:

* :func:`missing_patterns` — the *coverage* check behind ``occam-gitignore
  check``. Which canonical patterns are absent from an existing ``.gitignore``?
  Extra, project-specific lines are ignored: this is a subset/coverage test,
  not an equality test.
* :func:`apply_managed_block` — the *merge* behind ``occam-gitignore apply``.
  Insert or replace a single delimited block, leaving every line outside the
  block untouched.

Both are pure functions of their arguments: deterministic, no I/O, no clock,
no randomness. The same inputs always yield the same output.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .errors import ManagedBlockError

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = [
    "MANAGED_BLOCK_END",
    "MANAGED_BLOCK_NOTICE",
    "MANAGED_BLOCK_START",
    "apply_managed_block",
    "build_managed_block",
    "missing_patterns",
]

# Delimiters for the managed block. The `>>>` / `<<<` fences mirror the
# conda-style "managed region" convention and are unambiguous inside a
# `.gitignore` (a leading `#` makes them comments, so git ignores them).
MANAGED_BLOCK_START = "# >>> occam-gitignore >>>"
MANAGED_BLOCK_NOTICE = "# managed by occam-gitignore — do not edit inside this block"
MANAGED_BLOCK_END = "# <<< occam-gitignore <<<"


def _pattern_lines(text: str) -> frozenset[str]:
    """Stripped, non-comment, non-blank lines of a `.gitignore`."""
    out: set[str] = set()
    for raw in text.splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return frozenset(out)


def missing_patterns(canonical: Iterable[str], existing: str) -> tuple[str, ...]:
    """Canonical patterns absent from ``existing``. Canonical order preserved.

    Coverage semantics: only *missing* canonical lines are reported. Extra,
    project-specific lines already present in ``existing`` are intentionally
    ignored, so a repository can keep its own rules and still pass the check.

    Duplicate patterns in ``canonical`` are reported at most once.
    """
    have = _pattern_lines(existing)
    seen: set[str] = set()
    out: list[str] = []
    for pattern in canonical:
        if pattern not in have and pattern not in seen:
            seen.add(pattern)
            out.append(pattern)
    return tuple(out)


def build_managed_block(body: str) -> str:
    """Render the delimited managed block around ``body`` (no trailing newline).

    Leading and trailing blank lines of ``body`` are trimmed; interior blank
    lines (section separators) are preserved verbatim.
    """
    inner = body.strip("\n")
    lines = [MANAGED_BLOCK_START, MANAGED_BLOCK_NOTICE]
    if inner:
        lines.extend(inner.split("\n"))
    lines.append(MANAGED_BLOCK_END)
    return "\n".join(lines)


def apply_managed_block(existing: str, body: str) -> str:
    """Insert or replace the occam-gitignore managed block in ``existing``.

    - Lines outside the block are preserved (merge, not replace).
    - If the block is already present, its content is replaced in place.
    - If absent, the block is appended after the existing content.
    - **Idempotent**: ``apply_managed_block(apply_managed_block(x, b), b) ==
      apply_managed_block(x, b)``.
    - **Deterministic**: a pure function of ``(existing, body)``.

    The result always ends with exactly one trailing newline, with a single
    blank line separating the block from any surrounding content.

    Raises
    ------
    ManagedBlockError
        If the markers are malformed: a start without a matching end, or an
        end marker that appears before any start.
    """
    block_lines = build_managed_block(body).split("\n")
    src = existing.split("\n")

    start = _find(src, MANAGED_BLOCK_START)
    if start is None:
        if _find(src, MANAGED_BLOCK_END) is not None:
            raise ManagedBlockError("end marker found without a start marker")
        before, after = src, []
    else:
        end = _find(src, MANAGED_BLOCK_END, start + 1)
        if end is None:
            raise ManagedBlockError("start marker found without an end marker")
        before, after = src[:start], src[end + 1 :]

    before = _rstrip_blank(before)
    after = _rstrip_blank(_lstrip_blank(after))

    parts: list[str] = list(before)
    if before:
        parts.append("")
    parts.extend(block_lines)
    if after:
        parts.append("")
        parts.extend(after)
    return "\n".join(parts) + "\n"


def _find(lines: list[str], marker: str, start: int = 0) -> int | None:
    for i in range(start, len(lines)):
        if lines[i].strip() == marker:
            return i
    return None


def _rstrip_blank(lines: list[str]) -> list[str]:
    out = list(lines)
    while out and not out[-1].strip():
        out.pop()
    return out


def _lstrip_blank(lines: list[str]) -> list[str]:
    out = list(lines)
    while out and not out[0].strip():
        out.pop(0)
    return out
