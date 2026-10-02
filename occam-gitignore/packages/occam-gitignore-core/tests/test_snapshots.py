# SPDX-License-Identifier: MIT
"""Snapshot tests: lock canonical generator output.

If a snapshot fails, inspect the diff. To intentionally update, regenerate via:
    python -m occam_gitignore_core._snapshot_helper  (dev-only)
or manually replace the file contents and the matching hash.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from occam_gitignore_core import (
    DefaultFingerprinter,
    FileSystemTemplateRepository,
    GenerateOptions,
    JsonRulesTable,
    generate,
)

_DATA = Path(__file__).resolve().parents[3] / "data"
_SNAP = Path(__file__).resolve().parent / "snapshots"

_CASES = (
    (
        "python",
        ("pyproject.toml",),
        "sha256:de7f3061df49ff4035be5b6152d36c0cb749b62f55e5cabd4058013f2f70cca4",
    ),
    (
        "node-ts",
        ("package.json", "tsconfig.json"),
        "sha256:86d9c355e8defe5d0bb64aabf9ae7a512555e9ee34abe4c62f883f9e34dcaa93",
    ),
    (
        "python-docker",
        ("pyproject.toml", "Dockerfile", "docker-compose.yml"),
        "sha256:76f930fffec29dcb9be662d9618458505264bfa67a5d27a49bd23a65fc8c8dd3",
    ),
    (
        "java",
        ("pom.xml", "src/main/java/A.java"),
        "sha256:0db6ad2f2f53add2402c76fff136006c9228d867778fc8e27385ae7c457c4593",
    ),
    (
        "rust",
        ("Cargo.toml", "src/main.rs"),
        "sha256:ca7278c6e91c667506e42fed8bb67716c11d2f13ff30b3a4a1cef37f06db8498",
    ),
)


@pytest.fixture(scope="module")
def deps() -> tuple[FileSystemTemplateRepository, JsonRulesTable]:
    return (
        FileSystemTemplateRepository(_DATA / "templates"),
        JsonRulesTable.from_file(_DATA / "rules_table.json"),
    )


@pytest.mark.parametrize(("label", "tree", "expected_hash"), _CASES)
def test_snapshot_matches(
    deps: tuple[FileSystemTemplateRepository, JsonRulesTable],
    label: str,
    tree: tuple[str, ...],
    expected_hash: str,
) -> None:
    templates, rules = deps
    fp = DefaultFingerprinter().fingerprint(tree)
    out = generate(
        fp,
        GenerateOptions(include_comments=True),
        templates=templates,
        rules_table=rules,
    )
    snapshot_file = _SNAP / f"{label}.gitignore"
    assert snapshot_file.exists(), f"missing snapshot {snapshot_file}"
    assert out.content == snapshot_file.read_text("utf-8"), (
        f"snapshot drift for {label}: regenerate intentionally"
    )
    digest = "sha256:" + hashlib.sha256(out.content.encode("utf-8")).hexdigest()
    assert digest == expected_hash
    assert out.output_hash == expected_hash
