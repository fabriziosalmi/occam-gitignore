# Why deterministic?

A `.gitignore` is a configuration file consumed by tooling and humans. It is
not a creative artefact. There is no reason for the same project shape to
produce different ignore files at different times, yet most generators
(template assemblers, LLMs) do exactly that.

`occam-gitignore` rejects this. The contract is:

> **For a fixed `(fingerprint, options, templates, rules_table)`, the output
> bytes are a pure function. The same inputs always yield the same bytes,
> indexed by a `sha256` hash.**

## Consequences

- **Caching is trivial.** A hash uniquely identifies an output; no second run
  is ever needed for the same inputs.
- **Code review is meaningful.** A diff is caused by a real input change
  (template version, rules-table version, or detected features), never by
  noise.
- **Audit and reproduction are free.** `output_hash` + `core_version` +
  `rules_table_version` is a complete provenance record.
- **LLMs can call the tool safely.** No prompt drift, no hallucinated
  patterns. The MCP adapter is a thin wrapper around the same pure function
  the CLI uses.

## What we forbid in the core

The `occam_gitignore_core` package has zero runtime dependencies and bans:

- Reading files at generation time (templates and rules are passed in via
  ports, loaded once by the adapter).
- Reading the clock or any environment variable.
- Random number generators.
- Hash maps with iteration-order assumptions: every aggregation that produces
  output goes through an explicit `sorted(...)`.

## How we prove it

- **Property tests** in `packages/occam-gitignore-core/tests/test_determinism.py`
  shuffle inputs and assert byte-identical output.
- **Snapshot tests** lock the bytes of canonical outputs against `sha256`
  hashes committed to the repo.
- **Benchmark stability metric** is the fraction of cases whose hash is
  identical across `--repeats N` runs. CI fails if it drops below `1.000`.

## Why "Occam"?

We prefer the simplest rule set that explains the files we want to ignore.
Mined rules must clear a support threshold. Pair rules must clear a lift
threshold. Anything that does not earn its keep stays out.
