# Rules table

A **rules table** is a content-addressed list of additional patterns,
conditional on feature sets. It captures what the static templates miss but
real projects emit consistently.

## File format

```json
{
  "version": "sha256:<content-addressed>",
  "rules": [
    { "features": ["python", "docker"], "patterns": [".dockerignore.local"] }
  ]
}
```

> Secrets are **not** ecosystem-scoped. `.env`, `.env.*` and patterns like
> `*.pem` / `id_rsa` live in the `common` template so they apply to every stack,
> not just the one that happened to mine them. The rules table is for genuine
> co-occurrence rules that the static templates miss.

- `version` is `sha256(canonical_json(rules))[:12]`, prefixed with `sha256:`.
  Edit the rules and the version changes deterministically.
- `features` are matched as a **subset**: a rule with
  `["python", "docker"]` fires when both features are present in the
  fingerprint.
- `patterns` are sorted alphabetically inside each entry; entries are sorted
  by `features`.

## Loading

```python
from pathlib import Path
from occam_gitignore_core import JsonRulesTable

rules = JsonRulesTable.from_file(Path("data/rules_table.json"))
rules.version()                        # "sha256:72fd0c323cc1"
rules.extras_for(frozenset({"python"}))  # tuple of Rule(...)
```

## Mining a new table

The `occam-gitignore-training` package mines a rules table from JSONL
records — one record per repo — describing the files listed and the
`.gitignore` rules the repo actually used. The pipeline:

1. **Fingerprint** each record's file list (or use a declared feature set).
2. **Group** records by feature.
3. **Single-feature rules** — emit a pattern for feature *F* iff its support
   in *F*-bearing repos clears `min_support` and the pattern is not already
   covered by *F*'s template.
4. **Pair rules** — for feature pairs *(A, B)*, emit a pattern iff:
   - support among *{A,B}* repos clears `min_pair_support`,
   - the same support is `>= min_pair_lift × max(support_A, support_B)`,
   - it's not already emitted as a single-feature rule.
5. **Render** the result with `to_payload(...)` — content-addressed,
   sorted, stable.

```bash
uv run occam-gitignore-train mine \
  --records dataset.jsonl \
  --templates data/templates \
  --output data/rules_table.json
```

## Why mining is conservative

`MineConfig` defaults are deliberately strict:

- `min_support = 0.5` (a pattern must appear in at least half the repos)
- `min_repos_per_feature = 2`
- `min_pair_lift = 1.5` (the pair must explain the pattern more than either
  feature alone)

Occam: prefer not emitting over emitting noise. A noisy rules table burns
precision in the benchmark and confuses users.
