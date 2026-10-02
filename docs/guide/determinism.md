# Determinism contract

Every `GitignoreOutput` is uniquely identified by:

```python
GitignoreOutput(
    content: str,
    rules: tuple[Rule, ...],
    output_hash: str,            # "sha256:<hex>"
    rules_table_version: str,    # carried from the rules table
    core_version: str,           # the package version of the generator
)
```

For a fixed input, all five fields are stable across runs, machines, and
Python interpreters of the same major version.

## Three layers of enforcement

### 1. Property tests

Located in `packages/occam-gitignore-core/tests/test_determinism.py`:

- `test_generate_is_byte_identical_across_runs`: call `generate(...)` twice
  with the same arguments; assert `out.content` and `out.output_hash` match.
- `test_generate_is_invariant_to_input_order`: shuffle the tree and the
  user extras; assert the output is byte-identical.
- `test_output_carries_versions`: both `core_version` and
  `rules_table_version` are non-empty and present in the result.

### 2. Snapshots

Located in `packages/occam-gitignore-core/tests/test_snapshots.py`. Five
golden files in `tests/snapshots/` capture the canonical output for typical
project shapes (Python, Node+TS, Python+Docker, Java, Rust). The test:

1. Re-runs `generate(...)` with the recorded inputs.
2. Asserts byte-equality with the snapshot.
3. Asserts the `sha256` of `content` matches a hash hard-coded in the test.
4. Asserts `out.output_hash` matches that hash.

If any of those four checks fails, the change is intentional, and the
snapshot **and** hash must be updated together.

### 3. Benchmark stability

Run with `--repeats N`. Each case is generated `N` times. The bench computes:

```
stability = (#cases whose hash is identical across all N runs) / (#cases)
```

A regression to `< 1.0` is a release blocker: the CI workflow exits with
code `1` in that case (see `_exit_code` in
`occam_gitignore_bench.__main__`).

## What can change the hash legitimately

- A new template file (or an edit to an existing template).
- A new `rules_table.json` (its version is content-addressed too).
- A change in `core_version`.
- A change in `GenerateOptions` (`include_comments`, `include_provenance`,
  `extras`).

## What must never change the hash

- Process restarts, machine, OS, locale, timezone.
- The order in which the input tree is enumerated.
- The order in which user extras are passed.
- `PYTHONHASHSEED` (we always sort before iteration).
