# Fingerprinting

The fingerprinter answers a single question: **which features does this tree
contain?** Features are the keys that drive both template selection and
rules-table lookup.

## Default detectors

The default `Fingerprinter` ships with **11 detectors**:

| Feature      | Triggers on                                                  |
|--------------|--------------------------------------------------------------|
| `python`     | `pyproject.toml`, `requirements.txt`, `setup.py`, `*.py`     |
| `node`       | `package.json`, `*.{js,mjs,cjs,jsx,ts,tsx}`                  |
| `go`         | `go.mod`, `*.go`                                             |
| `rust`       | `Cargo.toml`, `*.rs`                                         |
| `docker`     | `Dockerfile`, `docker-compose.{yml,yaml}`                    |
| `terraform`  | `*.tf`, `*.tfvars`                                           |
| `jupyter`    | `*.ipynb`                                                    |
| `java`       | `pom.xml`, `build.gradle{,.kts}`, `*.java`, `*.kt`           |
| `ruby`       | `Gemfile`, `Rakefile`, `*.rb`, `*.gemspec`                   |
| `csharp`     | `*.{csproj,sln,cs,fsproj,vbproj}`                            |
| `swift`      | `Package.swift`, `*.swift`                                   |

A 12th feature, **`common`**, exists only as a template (`.DS_Store`,
`.idea/`, `.vscode/`, `Thumbs.db`, etc.). It is not detected; it is
**implicitly included** by `generate()` whenever the fingerprint is
non-empty and a `common` template is present in the repository.

This decoupling matters: the fingerprint stays a pure description of what
the tree contains. The decision to add OS/IDE patterns is a generation
policy, applied in the generator.

## Result shape

```python
@dataclass(frozen=True, slots=True)
class FingerprintResult:
    features: tuple[Feature, ...]      # sorted, deduplicated
    evidence: tuple[tuple[str, str], ...]  # sorted (feature_name, witness_path)
```

`evidence` carries one witness path per detected feature, useful for
debugging and explainable output.

## Extending detectors

Add a `Detector` and pass a custom tuple to `DefaultFingerprinter(...)`:

```python
from occam_gitignore_core import DefaultFingerprinter, Detector, Feature

custom = (
    *DefaultFingerprinter._DETECTORS,  # type: ignore[attr-defined]
    Detector(Feature("haskell"), lambda p: p.endswith((".hs", ".cabal"))),
)
fp = DefaultFingerprinter(detectors=custom)
```

In practice, prefer adding the detector to `fingerprint.py` and submitting a
PR: that way it benefits everyone, the rules-table miner sees the new
feature, and the bench corpus can cover it.
