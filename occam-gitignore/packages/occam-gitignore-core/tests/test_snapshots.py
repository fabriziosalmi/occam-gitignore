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
        "sha256:409fe9f1e0143152f8ec53f5885f926571c9680453094d51a49cec457b346dfb",
    ),
    (
        "node-ts",
        ("package.json", "tsconfig.json"),
        "sha256:8f87285d80d6c3a71c2583207d6f5c86e9920f1dbbd98af21747a6f790b359fd",
    ),
    (
        "python-docker",
        ("pyproject.toml", "Dockerfile", "docker-compose.yml"),
        "sha256:8484f701ced72cb73bfe180c6e47675343ab1e88bdc09d7ee0bf3573897e02ce",
    ),
    (
        "java",
        ("pom.xml", "src/main/java/A.java"),
        "sha256:13b84c24feae190a2cb7b957a5104edbe26d49877073c8fcaf6bc08545e20b98",
    ),
    (
        "rust",
        ("Cargo.toml", "src/main.rs"),
        "sha256:7e713ff29703f781cacecae96e76b10233e2e04e905972b824b40601614e37a3",
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
