# occam-gitignore

> Deterministic `.gitignore` generation. Zero latency. Reproducible.
>
> _The simplest set of rules that explains the files to ignore._

[![CI](https://github.com/fabriziosalmi/gitignore/actions/workflows/ci.yml/badge.svg)](https://github.com/fabriziosalmi/gitignore/actions/workflows/ci.yml)
[![Docs](https://github.com/fabriziosalmi/gitignore/actions/workflows/docs.yml/badge.svg)](https://fabriziosalmi.github.io/gitignore/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`occam-gitignore` produces `.gitignore` files that are:

- **Deterministic** — same input ⇒ byte-identical output, content-addressed by `sha256`.
- **Pure** — the core has no I/O, no clock, no randomness, no dependencies.
- **Explainable** — every emitted rule carries provenance (template / mined / user).
- **Fast** — p99 < 200 µs end-to-end on the bench corpus.
- **Honest** — measured on a corpus with hard recall/precision/F1/stability gates.

## Architecture

Hexagonal (ports & adapters). The `core` package is the single source of truth.
All I/O lives in adapters.

```
packages/
├── occam-gitignore-core/      # pure generator + ports + schema
├── occam-gitignore-cli/       # Typer CLI adapter
├── occam-gitignore-api/       # FastAPI HTTP adapter
├── occam-gitignore-mcp/       # MCP server adapter (stdio / SSE / streamable-http)
├── occam-gitignore-training/  # offline rule mining (lift-based pair detection)
└── occam-gitignore-bench/     # reproducible benchmarks with quality gates
```

## Determinism contract

Every `GitignoreOutput` carries `core_version`, `rules_table_version`, and `output_hash`.
Two runs on the same input **must** produce byte-identical output.
This is enforced by:

1. Property tests in `occam-gitignore-core` (input-order invariance, byte-identity).
2. Snapshot golden files locked by `sha256`.
3. A bench `stability` metric (must equal `1.000` across repeats).

## Quick start

```bash
uv sync
uv run pytest -q
uv run ruff check .
uv run mypy .
uv run occam-gitignore generate ./some-repo
```

Run the benchmark with quality gates:

```bash
uv run occam-gitignore-bench run bench/corpus \
  --templates data/templates \
  --rules-table data/rules_table.json \
  --repeats 10 --diff \
  --min-recall 0.85 --max-p99-ms 5.0
```

## Adapters

| Adapter | Entry point | Purpose |
|---|---|---|
| CLI    | `occam-gitignore generate <path>`     | Local generation |
| Action | `uses: fabriziosalmi/gitignore@v0.1.3`| CI drift check / auto-fix |
| API    | `uvicorn occam_gitignore_api.app:app` | HTTP, hash in `ETag` |
| MCP    | `occam-gitignore-mcp`                 | LLM-callable tool surface |
| Bench  | `occam-gitignore-bench run`           | Quality + latency gates |
| Train  | `occam-gitignore-train mine`          | Mine rules table from JSONL |

### GitHub Action

```yaml
# .github/workflows/gitignore.yml
on: [pull_request, push]
jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: fabriziosalmi/gitignore@v0.1.3
        with:
          path: '.'
          mode: 'check'   # or 'fix' to merge the managed block (own lines are kept)
```

Inputs: `path` (default `.`), `mode` (`check`|`fix`, default `check`),
`python-version` (default `3.12`), `version` (PEP 440 specifier, default
`>=0.1.3,<0.2`). Outputs: `drift` (`true`|`false`), `output-hash`
(`sha256:<digest>`).

## Documentation

Full documentation: **<https://fabriziosalmi.github.io/gitignore/>**

- [Getting started](https://fabriziosalmi.github.io/gitignore/guide/getting-started)
- [Architecture](https://fabriziosalmi.github.io/gitignore/guide/architecture)
- [Determinism](https://fabriziosalmi.github.io/gitignore/guide/determinism)
- [Benchmark methodology](https://fabriziosalmi.github.io/gitignore/guide/benchmark)
- [API reference](https://fabriziosalmi.github.io/gitignore/reference/core)

## License

MIT
