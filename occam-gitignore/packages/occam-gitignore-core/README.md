# occam-gitignore-core

Pure, deterministic core for [`occam-gitignore`](https://pypi.org/project/occam-gitignore/).

This package contains only the algorithm: types, ports, fingerprinter,
generator. No I/O wrappers, no CLI, no network. The public-facing tool that
end users want is [`occam-gitignore`](https://pypi.org/project/occam-gitignore/):
install that one with `pipx install occam-gitignore`.

This package is published separately so that other tools (IDE extensions,
servers, language ports) can depend on the algorithm without pulling the CLI
surface.

```python
from occam_gitignore_core import (
    DefaultFingerprinter,
    FileSystemTemplateRepository,
    GenerateOptions,
    JsonRulesTable,
    generate,
)

fp = DefaultFingerprinter().fingerprint(("pyproject.toml", "src/main.py"))
content = generate(
    fp,
    GenerateOptions(),
    templates=FileSystemTemplateRepository("data/templates"),
    rules_table=JsonRulesTable.from_file("data/rules_table.json"),
)
```

See https://github.com/fabriziosalmi/gitignore for the full project,
conformance suite, and specification.

MIT licensed.
