# SPDX-License-Identifier: MIT
"""CLI: occam-gitignore-bench run <corpus>."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from occam_gitignore_core import (
    CORE_VERSION,
    DefaultFingerprinter,
    FileSystemTemplateRepository,
    GenerateOptions,
    JsonRulesTable,
    generate,
)

from .cases import load_cases
from .metrics import CaseResult, ReportSummary, evaluate, summarize


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="occam-gitignore-bench")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Evaluate a corpus.")
    run.add_argument("corpus", type=Path)
    run.add_argument("--templates", type=Path, required=True)
    run.add_argument("--rules-table", type=Path, required=True)
    run.add_argument("--repeats", type=int, default=5)
    run.add_argument("--json", action="store_true", help="Emit JSON to stdout.")
    run.add_argument(
        "--diff",
        action="store_true",
        help="Show false negatives / false positives per case (text mode).",
    )
    run.add_argument(
        "--min-recall", type=float, default=None, help="Fail if macro recall is below.",
    )
    run.add_argument(
        "--min-precision",
        type=float,
        default=None,
        help="Fail if macro precision is below. Guards against silent over-generation "
        "(the metric a recall-only gate would let rot).",
    )
    run.add_argument(
        "--min-f1", type=float, default=None, help="Fail if macro F1 is below.",
    )
    run.add_argument(
        "--max-p99-ms", type=float, default=None, help="Fail if p99 latency (ms) exceeds.",
    )

    perf = sub.add_parser(
        "perf",
        help="Synthetic latency budget gate. Independent of accuracy.",
    )
    perf.add_argument("--templates", type=Path, required=True)
    perf.add_argument("--rules-table", type=Path, required=True)
    perf.add_argument("--n-trees", type=int, default=1000, help="Synthetic trees.")
    perf.add_argument(
        "--paths-per-tree", type=int, default=200,
        help="Path count per synthetic tree.",
    )
    perf.add_argument("--seed", type=int, default=0)
    perf.add_argument("--max-fingerprint-p99-ms", type=float, default=2.0)
    perf.add_argument("--max-generate-p99-ms", type=float, default=0.5)
    perf.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "run":
        return _cmd_run(args)
    if args.cmd == "perf":
        return _cmd_perf(args)
    return 2  # unreachable


def _cmd_run(args: argparse.Namespace) -> int:
    cases = load_cases(args.corpus)
    templates = FileSystemTemplateRepository(args.templates)
    rules = JsonRulesTable.from_file(args.rules_table)

    results = tuple(
        evaluate(case, templates=templates, rules_table=rules, repeats=args.repeats)
        for case in cases
    )
    summary = summarize(results)

    if args.json:
        sys.stdout.write(_to_json(results, summary, rules.version()))
    else:
        sys.stdout.write(_to_text(results, summary, rules.version(), diff=args.diff))

    return _exit_code(summary, args)


def _exit_code(summary: ReportSummary, args: argparse.Namespace) -> int:
    if summary.stability_rate < 1.0:
        return 1
    if args.min_recall is not None and summary.macro_recall < args.min_recall:
        return 2
    if args.min_precision is not None and summary.macro_precision < args.min_precision:
        return 5
    if args.min_f1 is not None and summary.macro_f1 < args.min_f1:
        return 3
    if args.max_p99_ms is not None and summary.latency_p99_ms > args.max_p99_ms:
        return 4
    return 0


def _to_text(
    results: tuple[CaseResult, ...],
    s: ReportSummary,
    rt_version: str,
    *,
    diff: bool,
) -> str:
    header = f"{'case':30s} {'P':>6s} {'R':>6s} {'F1':>6s} {'n_pred':>7s} {'stable':>7s}"
    lines: list[str] = [header, "-" * len(header)]
    lines.extend(
        (
            f"{r.name:30s} {r.precision:6.3f} {r.recall:6.3f} {r.f1:6.3f} "
            f"{r.n_predicted:>7d} {('yes' if r.stable else 'NO'):>7s}"
        )
        for r in results
    )
    lines.append("")
    lines.append(f"core={CORE_VERSION} rules_table={rt_version} cases={s.n_cases}")
    lines.append(
        f"macro: P={s.macro_precision:.3f} R={s.macro_recall:.3f} F1={s.macro_f1:.3f}",
    )
    lines.append(
        f"micro: P={s.micro_precision:.3f} R={s.micro_recall:.3f} F1={s.micro_f1:.3f}",
    )
    lines.append(
        f"stability={s.stability_rate:.3f} "
        f"latency p50={s.latency_p50_ms:.3f}ms p99={s.latency_p99_ms:.3f}ms",
    )
    if diff:
        lines.append("")
        lines.append("# diagnostics")
        for r in results:
            if r.false_negatives or r.false_positives:
                lines.append(f"## {r.name}")
                if r.false_negatives:
                    lines.append(
                        f"  missing ({len(r.false_negatives)}): "
                        f"{', '.join(r.false_negatives)}",
                    )
                if r.false_positives:
                    lines.append(
                        f"  extra   ({len(r.false_positives)}): "
                        f"{', '.join(r.false_positives)}",
                    )
    return "\n".join(lines) + "\n"


def _to_json(
    results: tuple[CaseResult, ...],
    s: ReportSummary,
    rt_version: str,
) -> str:
    payload = {
        "core_version": CORE_VERSION,
        "rules_table_version": rt_version,
        "summary": {
            "n_cases": s.n_cases,
            "macro": {
                "precision": s.macro_precision,
                "recall": s.macro_recall,
                "f1": s.macro_f1,
            },
            "micro": {
                "precision": s.micro_precision,
                "recall": s.micro_recall,
                "f1": s.micro_f1,
            },
            "stability_rate": s.stability_rate,
            "latency_ms": {"p50": s.latency_p50_ms, "p99": s.latency_p99_ms},
        },
        "cases": [
            {
                "name": r.name,
                "precision": r.precision,
                "recall": r.recall,
                "f1": r.f1,
                "n_predicted": r.n_predicted,
                "n_expected": r.n_expected,
                "n_correct": r.n_correct,
                "stable": r.stable,
                "false_negatives": list(r.false_negatives),
                "false_positives": list(r.false_positives),
                "latency_ms": {"p50": r.latency_p50, "p99": r.latency_p99},
            }
            for r in results
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# perf subcommand: synthetic latency budgets, independent of accuracy
# ---------------------------------------------------------------------------

# A small deterministic alphabet of "marker" + "extension" paths covering
# every detector. Trees are built by sampling with a seeded LCG so the
# corpus is fully reproducible across machines / runs.
_MARKERS: tuple[str, ...] = (
    "pyproject.toml", "requirements.txt", "setup.py",
    "package.json", "tsconfig.json",
    "go.mod", "Cargo.toml", "Dockerfile", "docker-compose.yml",
    "main.tf", "variables.tfvars", "notebook.ipynb",
    "pom.xml", "build.gradle", "build.gradle.kts",
    "Gemfile", "Rakefile", "App.csproj", "Package.swift",
)
_EXT_NAMES: tuple[str, ...] = (
    "main.py", "lib.py", "app.js", "index.ts", "view.tsx",
    "main.go", "lib.rs", "build.tf", "model.ipynb",
    "Service.java", "Bean.kt", "core.rb", "Program.cs", "App.swift",
    "README.md", "notes.txt",
)
_DIR_PARTS: tuple[str, ...] = ("src", "lib", "tests", "internal", "pkg", "app", "vendor")


def _build_tree(seed: int, n_paths: int) -> tuple[str, ...]:
    """Deterministic synthetic tree from a seed. Pure LCG, no `random`."""
    state = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    paths: list[str] = []
    for _ in range(n_paths):
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        pool = _MARKERS if (state % 5 == 0) else _EXT_NAMES
        leaf = pool[state % len(pool)]
        depth = (state >> 8) % 4
        parts = [_DIR_PARTS[(state >> (4 * (i + 1))) % len(_DIR_PARTS)] for i in range(depth)]
        paths.append("/".join([*parts, leaf]) if parts else leaf)
    return tuple(paths)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, min(len(s) - 1, round((pct / 100.0) * (len(s) - 1))))
    return s[idx]


def _cmd_perf(args: argparse.Namespace) -> int:
    templates = FileSystemTemplateRepository(args.templates)
    rules = JsonRulesTable.from_file(args.rules_table)
    fingerprinter = DefaultFingerprinter()
    options = GenerateOptions()

    fp_times_ms: list[float] = []
    gen_times_ms: list[float] = []

    # Warmup: prime caches, JIT-effects of CPython interpreter.
    warmup_tree = _build_tree(args.seed, min(args.paths_per_tree, 50))
    for _ in range(20):
        fp = fingerprinter.fingerprint(warmup_tree)
        generate(fp, options, templates=templates, rules_table=rules)

    for i in range(args.n_trees):
        tree = _build_tree(args.seed + i, args.paths_per_tree)
        t0 = time.perf_counter()
        fp = fingerprinter.fingerprint(tree)
        t1 = time.perf_counter()
        generate(fp, options, templates=templates, rules_table=rules)
        t2 = time.perf_counter()
        fp_times_ms.append((t1 - t0) * 1000.0)
        gen_times_ms.append((t2 - t1) * 1000.0)

    fp_p50 = statistics.median(fp_times_ms)
    fp_p99 = _percentile(fp_times_ms, 99.0)
    gen_p50 = statistics.median(gen_times_ms)
    gen_p99 = _percentile(gen_times_ms, 99.0)

    if args.json:
        sys.stdout.write(
            json.dumps(
                {
                    "core_version": CORE_VERSION,
                    "n_trees": args.n_trees,
                    "paths_per_tree": args.paths_per_tree,
                    "fingerprint_ms": {"p50": fp_p50, "p99": fp_p99},
                    "generate_ms": {"p50": gen_p50, "p99": gen_p99},
                    "budgets": {
                        "max_fingerprint_p99_ms": args.max_fingerprint_p99_ms,
                        "max_generate_p99_ms": args.max_generate_p99_ms,
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
    else:
        sys.stdout.write(
            f"perf: trees={args.n_trees} paths/tree={args.paths_per_tree}\n"
            f"  fingerprint: p50={fp_p50:.3f}ms  p99={fp_p99:.3f}ms  "
            f"(budget {args.max_fingerprint_p99_ms:.3f}ms)\n"
            f"  generate...: p50={gen_p50:.3f}ms  p99={gen_p99:.3f}ms  "
            f"(budget {args.max_generate_p99_ms:.3f}ms)\n",
        )

    if fp_p99 > args.max_fingerprint_p99_ms:
        sys.stderr.write(
            f"FAIL: fingerprint p99 {fp_p99:.3f}ms > "
            f"budget {args.max_fingerprint_p99_ms:.3f}ms\n",
        )
        return 4
    if gen_p99 > args.max_generate_p99_ms:
        sys.stderr.write(
            f"FAIL: generate p99 {gen_p99:.3f}ms > "
            f"budget {args.max_generate_p99_ms:.3f}ms\n",
        )
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
