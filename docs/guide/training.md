# Training pipeline

The training package is **offline-only**. It ingests structured records and
emits a content-addressed `rules_table.json`. It is invoked manually (or by
a release pipeline), never at runtime.

## Record format

Each line of the JSONL input is one repo:

```json
{
  "repo": "owner/name",
  "had_gitignore": true,
  "files_listed": ["pyproject.toml", "src/main.py", "tests/test_x.py"],
  "proposed_rules": ["__pycache__/", ".env", "coverage.xml"],
  "accepted": true
}
```

- `files_listed` drives the fingerprint (or set `features` explicitly).
- `proposed_rules` is the rule set the repo actually committed.
- `accepted` is a soft flag; combine it with `MineConfig(accepted_only=True)`
  if your dataset includes rejected proposals.

## Mining

```python
from occam_gitignore_training import MineConfig, mine, to_payload

config = MineConfig(
    min_support=0.5,
    min_repos_per_feature=2,
    mine_pairs=True,
    min_pair_support=0.6,
    min_pair_lift=1.5,
    min_repos_per_pair=2,
)
rules = mine(records, templates=templates, config=config)
payload = to_payload(rules)
```

## CLI

```bash
uv run occam-gitignore-train mine \
  --records dataset.jsonl \
  --templates data/templates \
  --output data/rules_table.json \
  --min-support 0.5 \
  --min-pair-lift 1.5
```

## Properties enforced by tests

- **Order invariance.** Shuffling the records yields an identical payload.
- **Template suppression.** A pattern already present in feature *F*'s
  template is never re-emitted as an *F*-only mined rule.
- **Threshold respect.** `min_support`, `min_repos_per_feature`,
  `min_pair_support`, `min_pair_lift`, `min_repos_per_pair` are all
  individually tested.
- **Content-addressed version.** `payload["version"]` is
  `sha256(canonical_json(rules))[:12]`, prefixed with `sha256:`.

## When to mine

You should re-mine when:

1. You have at least ~50 new records for a feature, or
2. You add a new feature/detector, or
3. You observe `false_negatives` in `bench --diff` that look generalisable.

In all other cases, leave the rules table alone: its stability is part of
the determinism contract for downstream consumers.
