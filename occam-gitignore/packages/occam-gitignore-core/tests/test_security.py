# SPDX-License-Identifier: MIT
"""Security regression tests: secrets must be ignored for EVERY stack.

Guards the 0.2.0 fix that moved `.env` and secret patterns out of the
python-only mined table and into the `common` template. Before the fix a
Rust/Go/Node repo without Python generated a `.gitignore` with no `.env`
line, so applying the tool could silently commit secrets.
"""

from __future__ import annotations

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

_SECRET_PATTERNS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.keystore",
    "id_rsa",
    "id_ed25519",
)


@pytest.fixture(scope="module")
def deps() -> tuple[FileSystemTemplateRepository, JsonRulesTable]:
    return (
        FileSystemTemplateRepository(_DATA / "templates"),
        JsonRulesTable.from_file(_DATA / "rules_table.json"),
    )


@pytest.mark.parametrize(
    "tree",
    [
        ("Cargo.toml", "src/main.rs"),  # rust, no python
        ("go.mod", "main.go"),  # go, no python
        ("package.json", "src/index.ts"),  # node, no python
    ],
)
def test_secrets_ignored_for_non_python_stacks(
    deps: tuple[FileSystemTemplateRepository, JsonRulesTable],
    tree: tuple[str, ...],
) -> None:
    templates, rules = deps
    fp = DefaultFingerprinter().fingerprint(tree)
    out = generate(fp, GenerateOptions(), templates=templates, rules_table=rules)
    patterns = {r.pattern for r in out.rules}
    for secret in _SECRET_PATTERNS:
        assert secret in patterns, f"{secret!r} missing for stack {tree!r}"


def test_env_example_negation_renders_after_env_glob(
    deps: tuple[FileSystemTemplateRepository, JsonRulesTable],
) -> None:
    """`!.env.example` must appear after `.env.*` so git re-includes it.

    git resolves ignore status by "last matching pattern wins"; a naive
    alphabetical sort would place `!` before `.` and neuter the negation.
    """
    templates, rules = deps
    fp = DefaultFingerprinter().fingerprint(("Cargo.toml",))
    out = generate(
        fp,
        GenerateOptions(include_comments=False),
        templates=templates,
        rules_table=rules,
    )
    lines = out.content.splitlines()
    assert ".env.*" in lines
    assert "!.env.example" in lines
    assert lines.index(".env.*") < lines.index("!.env.example")
