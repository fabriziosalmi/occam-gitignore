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
        "sha256:546fa208269a459d761e802636a2818336f63ffdab3f33ca5c11f89b8c835731",
    ),
    (
        "node-ts",
        ("package.json", "tsconfig.json"),
        "sha256:91a5acb0121733e3d225cd550ba358a40fb6d5a612cb7110fa8993afcc67aa3f",
    ),
    (
        "python-docker",
        ("pyproject.toml", "Dockerfile", "docker-compose.yml"),
        "sha256:6511e0b14913e9455b8f3010fba6bc4cdc6b13884b4527357ec41ba742bd3e02",
    ),
    (
        "java",
        ("pom.xml", "src/main/java/A.java"),
        "sha256:5fbbe7c7afbe449a6305312d508def7d46c2841c4eee7949059dfe91678587a9",
    ),
    (
        "rust",
        ("Cargo.toml", "src/main.rs"),
        "sha256:6f0bd2bf835b01ab988911ac646827c79a2b5ad047d77e0d4b84675c194d3980",
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
