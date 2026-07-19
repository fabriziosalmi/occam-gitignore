# SPDX-License-Identifier: MIT
"""Smoke tests for the bench CLI (run + perf subcommands)."""

from __future__ import annotations

import json
from pathlib import Path  # noqa: TC003 - used at runtime by pytest fixture

from occam_gitignore_bench.__main__ import main


def _write_fixtures(tmp_path: Path) -> tuple[Path, Path, Path]:
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "python.gitignore").write_text("__pycache__/\n*.pyc\n", "utf-8")
    rules = tmp_path / "rules_table.json"
    rules.write_text('{"version":"t","rules":[]}', "utf-8")
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "py.json").write_text(
        json.dumps(
            {
                "name": "py",
                "tree": ["pyproject.toml"],
                "expected": ["__pycache__/", "*.pyc"],
            },
        ),
        "utf-8",
    )
    return corpus, templates, rules


def test_run_subcommand_returns_zero(tmp_path: Path) -> None:
    corpus, templates, rules = _write_fixtures(tmp_path)
    rc = main(
        [
            "run",
            str(corpus),
            "--templates",
            str(templates),
            "--rules-table",
            str(rules),
            "--repeats",
            "2",
            "--min-recall",
            "0.5",
        ],
    )
    assert rc == 0


def test_run_min_precision_gate_fails_when_below(tmp_path: Path) -> None:
    """A recall-only gate would pass this; the precision gate must catch it."""
    corpus, templates, rules = _write_fixtures(tmp_path)
    # Expected omits `*.pyc`, so the generator over-produces -> precision 0.5.
    (corpus / "py.json").write_text(
        json.dumps(
            {"name": "py", "tree": ["pyproject.toml"], "expected": ["__pycache__/"]},
        ),
        "utf-8",
    )
    rc = main(
        [
            "run",
            str(corpus),
            "--templates",
            str(templates),
            "--rules-table",
            str(rules),
            "--repeats",
            "2",
            "--min-recall",
            "0.5",  # would pass alone
            "--min-precision",
            "0.99",  # must fail
        ],
    )
    assert rc == 5


def test_perf_subcommand_meets_default_budget(tmp_path: Path) -> None:
    """Smoke test only — uses generous budgets so it passes on slow CI runners.

    Real performance gates live in the dedicated CI step that runs the full
    1000-tree perf command with strict budgets.
    """
    _, templates, rules = _write_fixtures(tmp_path)
    rc = main(
        [
            "perf",
            "--templates",
            str(templates),
            "--rules-table",
            str(rules),
            "--n-trees",
            "50",
            "--paths-per-tree",
            "100",
            "--max-fingerprint-p99-ms",
            "100.0",
            "--max-generate-p99-ms",
            "50.0",
        ],
    )
    assert rc == 0


def test_perf_subcommand_fails_when_budget_too_tight(tmp_path: Path) -> None:
    _, templates, rules = _write_fixtures(tmp_path)
    rc = main(
        [
            "perf",
            "--templates",
            str(templates),
            "--rules-table",
            str(rules),
            "--n-trees",
            "30",
            "--paths-per-tree",
            "100",
            "--max-generate-p99-ms",
            "0.0",  # Impossible: must fail
        ],
    )
    assert rc == 4
