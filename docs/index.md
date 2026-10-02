---
layout: home

hero:
  name: occam-gitignore
  text: Deterministic .gitignore generation
  tagline: Same input, byte-identical output. Hash-verifiable. No network, no LLM at runtime.
  actions:
    - theme: brand
      text: Get started
      link: /guide/getting-started
    - theme: alt
      text: Architecture
      link: /guide/architecture
    - theme: alt
      text: View on GitHub
      link: https://github.com/fabriziosalmi/gitignore

features:
  - title: Deterministic by contract
    details: Every output carries a sha256 hash, a core version, and a rules-table version. Two runs on the same tree produce byte-identical output, enforced by tests.
  - title: Hexagonal architecture
    details: The core is a pure function of (fingerprint, options, templates, rules). All I/O lives in adapters (CLI, HTTP, MCP) sharing the same generator.
  - title: Explainable output
    details: Every rule carries provenance (template, mined, or user). Mined rules come from a documented, lift-based association pipeline.
  - title: Low latency
    details: No filesystem walks, no LLMs at runtime. On the local benchmark corpus, generation runs in well under a millisecond per repo.
  - title: Measured quality
    details: The benchmark reports recall, precision, F1, stability, and latency p50/p99. CI fails when any threshold regresses.
  - title: Three adapters, one core
    details: CLI, FastAPI HTTP, and MCP server share a single deterministic generator. Bench and training are offline harnesses on top of the same core.
---
