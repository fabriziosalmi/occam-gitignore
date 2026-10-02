# SPDX-License-Identifier: MIT
"""scan_tree: git is the source of truth inside a work tree."""

from __future__ import annotations

import subprocess
from pathlib import Path  # noqa: TC003 - used at runtime by pytest fixture

from occam_gitignore_cli.scanner import scan_tree
from occam_gitignore_core import DefaultFingerprinter


def _git(repo: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", "-C", str(repo), *args], check=True, capture_output=True,  # noqa: S607
    )


def _touch(root: Path, *rels: str) -> None:
    for rel in rels:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text("", "utf-8")


def test_ignored_dirs_are_not_evidence_in_a_git_repo(tmp_path: Path) -> None:
    # A virtualenv with a non-standard name used to make pip's vendored `.js`
    # look like a Node project. In git, its ignore rule settles it.
    _git(tmp_path, "init", "-q")
    _touch(
        tmp_path,
        "pyproject.toml",
        ".venv-py312/lib/site-packages/pip/worker.js",
        ".worktrees/feature-x/Cargo.toml",
    )
    (tmp_path / ".gitignore").write_text(".venv-py312/\n.worktrees/\n", "utf-8")
    _git(tmp_path, "add", "pyproject.toml", ".gitignore")
    tree = scan_tree(tmp_path)
    assert tree == (".gitignore", "pyproject.toml")
    features = {f.name for f in DefaultFingerprinter().fingerprint(tree).features}
    assert features == {"common", "python"}


def test_untracked_but_not_ignored_files_count(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _touch(tmp_path, "pyproject.toml", "new_module.go")
    _git(tmp_path, "add", "pyproject.toml")
    assert scan_tree(tmp_path) == ("new_module.go", "pyproject.toml")


def test_tracked_file_inside_an_ignored_dir_still_counts(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-q")
    _touch(tmp_path, "vendor/lib/go.mod")
    _git(tmp_path, "add", "vendor/lib/go.mod")
    (tmp_path / ".gitignore").write_text("vendor/\n", "utf-8")
    assert "vendor/lib/go.mod" in scan_tree(tmp_path)


def test_outside_git_falls_back_to_the_filesystem(tmp_path: Path) -> None:
    _touch(tmp_path, "pyproject.toml", "src/app.py", "node_modules/x/index.js")
    assert scan_tree(tmp_path) == ("pyproject.toml", "src/app.py")


def test_truncation_keeps_the_sorted_prefix(tmp_path: Path) -> None:
    _touch(tmp_path, "c.txt", "a.txt", "b.txt", "d/e.txt")
    assert scan_tree(tmp_path, max_entries=2) == ("a.txt", "b.txt")
    _git(tmp_path, "init", "-q")
    assert scan_tree(tmp_path, max_entries=2) == ("a.txt", "b.txt")
