# SPDX-License-Identifier: MIT
# ruff: noqa: INP001 - intentional script directory, not a package.
"""Deterministic conformance case generator.

Run from the repo root:

    uv run python conformance/generate_cases.py

Produces ``conformance/fixtures/`` (pinned copies of templates +
rules_table) and ``conformance/cases/NNN-<label>/`` for every case in
the matrix below.

The matrix is hand-curated to exercise:

  - every single feature in isolation (positive + negative path)
  - every commonly-co-occurring feature pair (python+docker, node+docker,
    java+docker, jupyter+python, terraform+docker, ...)
  - both option combinations: ``include_comments`` ON/OFF, with/without
    extras, with ``include_provenance`` per-line annotations
  - inputs that are deliberately shuffled, nested, or noisy

If you change any of these inputs, every downstream consumer of the
suite is informed by the byte difference. SemVer applies.
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_TEMPLATES = ROOT / "data" / "templates"
SRC_RULES = ROOT / "data" / "rules_table.json"
DST = ROOT / "conformance"

# Make the in-repo packages importable without installation.
sys.path.insert(0, str(ROOT / "packages" / "occam-gitignore-core" / "src"))

from occam_gitignore_core import (  # noqa: E402
    DefaultFingerprinter,
    FileSystemTemplateRepository,
    GenerateOptions,
    JsonRulesTable,
    generate,
)


@dataclass(frozen=True)
class Case:
    label: str
    tree: tuple[str, ...]
    extras: tuple[str, ...] = ()
    include_comments: bool = True
    include_provenance: bool = False


# Single-feature minimal cases (positive). Order is irrelevant to output;
# we keep variety to catch any sneaky input-order leak.
SINGLE: tuple[Case, ...] = (
    Case("python-minimal", ("pyproject.toml",)),
    Case("python-nested", ("src/main.py", "tests/test_a.py", "pyproject.toml")),
    Case("node-minimal", ("package.json",)),
    Case("node-ts", ("package.json", "tsconfig.json", "src/index.ts")),
    Case("go-minimal", ("go.mod", "main.go")),
    Case("rust-minimal", ("Cargo.toml", "src/main.rs")),
    Case("docker-only", ("Dockerfile",)),
    Case("docker-compose", ("docker-compose.yml", "service/Dockerfile")),
    Case("terraform-minimal", ("main.tf", "variables.tfvars")),
    Case("jupyter-minimal", ("notebook.ipynb",)),
    Case("java-maven", ("pom.xml", "src/main/java/A.java")),
    Case("java-gradle-kts", ("build.gradle.kts", "settings.gradle.kts")),
    Case("ruby-minimal", ("Gemfile", "lib/foo.rb")),
    Case("csharp-minimal", ("App.csproj", "Program.cs")),
    Case("swift-minimal", ("Package.swift", "Sources/main.swift")),
)

# Combo cases: realistic stacks. Picks pairs/triples that surface
# co-occurrence rules from the mined table.
COMBOS: tuple[Case, ...] = (
    Case("python-docker", ("pyproject.toml", "Dockerfile", "docker-compose.yml")),
    Case("node-docker", ("package.json", "Dockerfile")),
    Case("java-docker", ("pom.xml", "Dockerfile")),
    Case("python-jupyter", ("pyproject.toml", "analysis.ipynb")),
    Case("terraform-docker", ("main.tf", "Dockerfile")),
    Case("python-node", ("pyproject.toml", "package.json", "scripts/build.js")),
    Case("python-go-rust", ("pyproject.toml", "go.mod", "Cargo.toml")),
    Case(
        "everything",
        (
            "pyproject.toml",
            "package.json",
            "go.mod",
            "Cargo.toml",
            "Dockerfile",
            "main.tf",
            "notebook.ipynb",
            "pom.xml",
            "Gemfile",
            "App.csproj",
            "Package.swift",
        ),
    ),
)

# Option-variant cases: same trees, different rendering options.
OPTION_VARIANTS: tuple[Case, ...] = (
    Case("python-no-comments", ("pyproject.toml",), include_comments=False),
    Case(
        "python-with-extras",
        ("pyproject.toml",),
        extras=(".env.local", "secrets/"),
    ),
    Case(
        "python-with-provenance",
        ("pyproject.toml",),
        include_provenance=True,
    ),
    Case(
        "python-no-comments-with-extras",
        ("pyproject.toml",),
        extras=("custom-secret.env",),
        include_comments=False,
    ),
    Case(
        "node-with-extras",
        ("package.json",),
        extras=(".vercel/", ".turbo/"),
    ),
    Case(
        "everything-no-comments",
        (
            "pyproject.toml",
            "package.json",
            "Dockerfile",
        ),
        include_comments=False,
    ),
)

# Edge cases: empty, single-noise, duplicate paths, deeply nested
EDGES: tuple[Case, ...] = (
    Case("noise-only", ("README.md", "LICENSE", "docs/index.md")),
    Case(
        "deeply-nested-python",
        ("a/b/c/d/e/f/g/pyproject.toml", "a/b/main.py"),
    ),
    Case(
        "duplicate-markers",
        (
            "pyproject.toml",
            "subpkg/pyproject.toml",
            "vendor/pyproject.toml",
        ),
    ),
)

# Machine learning: conservative file-presence detection of the `ml` feature.
ML: tuple[Case, ...] = (
    Case("ml-onnx", ("model.onnx",)),
    Case("python-ml", ("pyproject.toml", "train.py", "checkpoints/model.pt")),
)

ALL_CASES: tuple[Case, ...] = SINGLE + COMBOS + OPTION_VARIANTS + EDGES + ML


def _copy_fixtures() -> None:
    """Pin templates + rules_table into the suite as immutable fixtures."""
    fixtures = DST / "fixtures"
    if (fixtures / "templates").exists():
        shutil.rmtree(fixtures / "templates")
    fixtures.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SRC_TEMPLATES, fixtures / "templates")
    shutil.copy2(SRC_RULES, fixtures / "rules_table.json")

    # Compute a manifest hash of the fixtures so consumers can detect
    # accidental drift before running cases.
    templates = FileSystemTemplateRepository(fixtures / "templates")
    rules = JsonRulesTable.from_file(fixtures / "rules_table.json")
    manifest = {
        "templates_version": templates.version(),
        "rules_table_version": rules.version(),
    }
    (fixtures / "fixtures_hash.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _emit_case(idx: int, case: Case) -> None:
    fixtures = DST / "fixtures"
    templates = FileSystemTemplateRepository(fixtures / "templates")
    rules = JsonRulesTable.from_file(fixtures / "rules_table.json")
    fp = DefaultFingerprinter().fingerprint(case.tree)
    out = generate(
        fp,
        GenerateOptions(
            extras=case.extras,
            include_comments=case.include_comments,
            include_provenance=case.include_provenance,
        ),
        templates=templates,
        rules_table=rules,
    )

    case_dir = DST / "cases" / f"{idx:03d}-{case.label}"
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True)

    (case_dir / "tree.json").write_text(
        json.dumps(list(case.tree), indent=2) + "\n", encoding="utf-8",
    )
    (case_dir / "options.json").write_text(
        json.dumps(
            {
                "extras": list(case.extras),
                "include_comments": case.include_comments,
                "include_provenance": case.include_provenance,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (case_dir / "expected.gitignore").write_text(out.content, encoding="utf-8")
    (case_dir / "expected_hashes.json").write_text(
        json.dumps(
            {
                "content_hash": out.content_hash,
                "provenance_hash": out.provenance_hash,
                "core_version": out.core_version,
                "templates_version": out.templates_version,
                "rules_table_version": out.rules_table_version,
                "features": [f.name for f in fp.features],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    _copy_fixtures()
    cases_root = DST / "cases"
    if cases_root.exists():
        shutil.rmtree(cases_root)
    cases_root.mkdir(parents=True)
    for idx, case in enumerate(ALL_CASES):
        _emit_case(idx, case)
    sys.stderr.write(f"emitted {len(ALL_CASES)} conformance cases\n")


if __name__ == "__main__":
    main()
