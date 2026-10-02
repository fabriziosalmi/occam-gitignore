# Contributing

Thanks for considering a contribution. The bar is high but the rules are
simple.

## Local setup

```bash
git clone https://github.com/fabriziosalmi/gitignore.git
cd gitignore/occam-gitignore
uv sync
```

## Quality gates (must all pass)

```bash
uv run ruff check .                    # ruff: select = ALL
uv run mypy .                          # strict, disallow_any_explicit
uv run pytest -q
uv run occam-gitignore-bench run bench/corpus \
  --templates data/templates \
  --rules-table data/rules_table.json \
  --min-recall 0.85 --max-p99-ms 5.0
```

CI runs the same commands. PRs that don't pass are not merged.

## Design rules

1. **The core stays pure.** No I/O, no clock, no env vars, no random; and
   zero runtime dependencies in `occam-gitignore-core`.
2. **No `Any`.** `mypy.ini` sets `disallow_any_explicit = true`. Use
   `Protocol`, `TypedDict`, or generics.
3. **Frozen dataclasses with `slots=True`** for every value type.
4. **Sort before iteration.** Anywhere the output depends on a `dict` or
   `set`, wrap the iteration in `sorted(...)`.
5. **Snapshots are sacred.** If you change generator output, regenerate
   the snapshots **and** update the hard-coded hashes in
   `tests/test_snapshots.py` in the same commit.
6. **Prefer not emitting.** A new template pattern or mined rule must
   improve recall *without* destroying precision on the bench.

## Adding a feature

1. Add the detector to `packages/occam-gitignore-core/src/occam_gitignore_core/fingerprint.py`.
2. Add a `<feature>.gitignore` template in `data/templates/`.
3. Add at least one bench case in `bench/corpus/` with a realistic
   `expected` must-have set.
4. Update snapshots if pre-existing cases now include the feature.
5. Run the full quality gate.

## Updating the rules table

The rules table is content-addressed. If you change it, every downstream
consumer sees a new `rules_table_version` and every `output_hash` shifts
accordingly. Do this only when warranted by mining results, never by hand.
