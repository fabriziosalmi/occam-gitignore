# SPDX-License-Identifier: MIT
"""Repository scanning utilities. Kept here, out of the pure core."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

__all__ = ["scan_tree"]

_SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn",
    "node_modules", ".venv", "venv", "env",
    "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache",
    "target", "dist", "build",
})

_GIT_TIMEOUT_S = 120


def scan_tree(root: Path, *, max_entries: int = 50_000) -> tuple[str, ...]:
    """Return sorted repo-relative POSIX paths describing the project.

    Inside a git work tree the answer comes from git itself: tracked files
    plus untracked files that are *not* ignored. Anything already ignored
    (virtualenvs of any name, build output, agent worktrees, caches) is
    therefore never mistaken for project evidence. Outside git, the
    filesystem is walked with a fixed skip-list.

    Truncation to ``max_entries`` happens after sorting, so the result is a
    pure function of the file set, never of filesystem iteration order.
    """
    if not root.is_dir():
        raise NotADirectoryError(str(root))
    listed = _git_paths(root)
    entries = sorted(listed) if listed is not None else _walk(root)
    return tuple(entries[:max_entries])


def _git_paths(root: Path) -> list[str] | None:
    """Tracked + untracked-not-ignored paths, or ``None`` if git can't answer."""
    try:
        res = subprocess.run(  # noqa: S603 - fixed argv, no shell
            [  # noqa: S607
                "git", "-C", str(root), "-c", "core.quotepath=off",
                "ls-files", "-z", "--cached", "--others", "--exclude-standard",
            ],
            capture_output=True,
            # Read-only: never take the index lock or refresh stat info.
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            check=False,
            timeout=_GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if res.returncode != 0:
        return None
    paths = res.stdout.decode("utf-8", "surrogateescape").split("\0")
    # A path listed in the index may be gone from disk (deleted, not staged);
    # it still describes the project, so it is kept.
    return list(dict.fromkeys(p for p in paths if p))


def _walk(root: Path) -> list[str]:
    out: list[str] = []
    stack: list[Path] = [root]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_symlink():
                continue
            if child.is_dir():
                if child.name in _SKIP_DIRS:
                    continue
                stack.append(child)
            elif child.is_file():
                out.append(Path(os.path.relpath(child, root)).as_posix())
    out.sort()
    return out
