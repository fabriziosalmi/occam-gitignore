# Benchmark methodology

The benchmark answers: **does the generator produce the rules people
actually need, fast, and identically across runs?**

## Inputs

The corpus lives in `bench/corpus/*.json`. Each case is:

```json
{
  "name": "py-docker",
  "tree": ["pyproject.toml", "Dockerfile", "docker-compose.yml", "src/main.py"],
  "expected": [
    "__pycache__/", "*.py[cod]", "build/", "dist/", ".venv/",
    ".pytest_cache/", ".coverage", ".env",
    ".DS_Store", ".idea/", ".vscode/", "Thumbs.db"
  ]
}
```

`expected` is a **must-have** set: the patterns whose absence would make
the output wrong for that stack. It is intentionally smaller than the
total set the generator emits: this keeps the recall metric meaningful and
the precision metric honest.

## Metrics

For each case:

- **Predicted** *P* = the set of patterns produced by `core.generate(...)`.
- **Expected** *E* = the corpus `expected` set.
- `recall    = |P ∩ E| / |E|`
- `precision = |P ∩ E| / |P|`
- `f1        = 2·precision·recall / (precision + recall)`
- `false_negatives = sorted(E - P)`, surfaced via `--diff`
- `false_positives = sorted(P - E)`, surfaced via `--diff`
- `stability` = `1` iff `output_hash` is identical across all `--repeats`
  runs of this case.

Macro/micro averages are reported across cases.

Latency is measured end-to-end (`fingerprint + generate`), reported as
**p50** and **p99** in milliseconds.

## CLI

```bash
uv run occam-gitignore-bench run bench/corpus \
  --templates data/templates \
  --rules-table data/rules_table.json \
  --repeats 10 \
  --diff \
  --min-recall 0.85 \
  --min-f1     0.5  \
  --max-p99-ms 5.0
```

## Exit codes

| Code | Cause                                                |
|------|------------------------------------------------------|
| `0`  | All gates passed                                     |
| `1`  | A case was non-deterministic (`stability < 1.0`)     |
| `2`  | `macro_recall < --min-recall`                        |
| `3`  | `macro_f1 < --min-f1`                                |
| `4`  | `latency_p99_ms > --max-p99-ms`                      |

These are checked in CI; a regression fails the build.

## Current numbers

```
core=0.1.3 rules_table=sha256:72fd0c323cc1 cases=7
macro: P=0.443 R=1.000 F1=0.608
micro: P=0.425 R=1.000 F1=0.597
stability=1.000 latency p50=0.047ms p99=0.119ms
```

**Recall = 1.000.** The generator never misses a must-have pattern in the
corpus. **Precision ≈ 0.44** by design: the bundled templates from
[github/gitignore](https://github.com/github/gitignore) include legitimate
patterns (e.g. `*.next/`, `*.yarn/`, `*.war`) that aren't in our minimal
expected sets. Treat precision here as a "verbosity" indicator, not a
correctness one.

## On honesty

We resisted the temptation to set `expected = predicted`: that would yield
F1 = 1.0 by construction and tell you nothing. The corpus is curated by
hand to reflect what a human reviewer would consider essential.
