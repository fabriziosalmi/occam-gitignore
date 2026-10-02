# Ports

Two `Protocol`s define everything the core needs from the outside world.
Adapters that satisfy them can be swapped freely.

## `TemplateRepository`

```python
class TemplateRepository(Protocol):
    def get(self, feature: Feature) -> tuple[Rule, ...]: ...
    def features(self) -> tuple[Feature, ...]: ...
    def version(self) -> str: ...
```

### Built-in adapters

- **`FileSystemTemplateRepository(root: Path, version: str)`**: loads
  `<feature>.gitignore` files from a directory; caches per feature.
- **`InMemoryTemplateRepository(data: dict[Feature, tuple[Rule, ...]], version: str = "test")`**:
  for tests and embedded use.

`features()` is sorted; the generator never relies on insertion order.

## `RulesTable`

```python
class RulesTable(Protocol):
    def extras_for(self, features: frozenset[Feature]) -> tuple[Rule, ...]: ...
    def version(self) -> str: ...
```

`extras_for` performs **subset matching**: a rule with feature set *S* is
returned iff *S ⊆ features*. The result is sorted by `(features, pattern)`.

### Built-in adapters

- **`JsonRulesTable.from_file(path: Path)`**: loads a `rules_table.json`.
- **`InMemoryRulesTable(...)`**: for tests.

## Custom adapters

Anything that satisfies the protocols works. Examples:

- A `TemplateRepository` backed by a remote object store with a content
  hash as `version()`.
- A `RulesTable` that reads from a database, pinning `version()` to a
  schema-migration revision.

The core never serializes these objects; it only calls the methods above.
