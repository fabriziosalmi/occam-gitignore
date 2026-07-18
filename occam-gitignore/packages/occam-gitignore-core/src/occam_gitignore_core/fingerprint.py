# SPDX-License-Identifier: MIT
"""Strategy registry of detectors. Add a `Detector` to extend without core changes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from .schema import Feature, FingerprintResult

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["DefaultFingerprinter", "Detector"]


@dataclass(frozen=True, slots=True)
class Detector:
    """Maps a feature to a path-predicate. Pure, side-effect free."""

    feature: Feature
    matches: Callable[[str], bool]


def _is_or_endswith(name: str) -> Callable[[str], bool]:
    suffix = "/" + name
    return lambda p: p == name or p.endswith(suffix)


def _ext(*suffixes: str) -> Callable[[str], bool]:
    return lambda p: p.endswith(suffixes)


_DETECTORS: Final[tuple[Detector, ...]] = (
    Detector(
        Feature("python"),
        lambda p: (
            _is_or_endswith("pyproject.toml")(p)
            or _is_or_endswith("requirements.txt")(p)
            or _is_or_endswith("setup.py")(p)
            or _is_or_endswith("setup.cfg")(p)
            or _ext(".py")(p)
        ),
    ),
    Detector(
        Feature("node"),
        lambda p: (
            _is_or_endswith("package.json")(p)
            or _ext(".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx")(p)
        ),
    ),
    Detector(
        Feature("go"),
        lambda p: _is_or_endswith("go.mod")(p) or _ext(".go")(p),
    ),
    Detector(
        Feature("rust"),
        lambda p: _is_or_endswith("Cargo.toml")(p) or _ext(".rs")(p),
    ),
    Detector(
        Feature("docker"),
        lambda p: (
            _is_or_endswith("Dockerfile")(p)
            or _is_or_endswith("docker-compose.yml")(p)
            or _is_or_endswith("docker-compose.yaml")(p)
        ),
    ),
    Detector(Feature("terraform"), _ext(".tf", ".tfvars")),
    Detector(Feature("jupyter"), _ext(".ipynb")),
    Detector(
        Feature("java"),
        lambda p: (
            _is_or_endswith("pom.xml")(p)
            or _is_or_endswith("build.gradle")(p)
            or _is_or_endswith("build.gradle.kts")(p)
            or _is_or_endswith("settings.gradle")(p)
            or _is_or_endswith("settings.gradle.kts")(p)
            or _ext(".java", ".kt", ".kts", ".gradle")(p)
        ),
    ),
    Detector(
        Feature("ruby"),
        lambda p: (
            _is_or_endswith("Gemfile")(p)
            or _is_or_endswith("Rakefile")(p)
            or _ext(".rb", ".gemspec")(p)
        ),
    ),
    Detector(
        Feature("csharp"),
        _ext(".csproj", ".sln", ".cs", ".fsproj", ".vbproj"),
    ),
    Detector(
        Feature("swift"),
        lambda p: _is_or_endswith("Package.swift")(p) or _ext(".swift")(p),
    ),
    # Machine learning. Detected conservatively from the presence of model
    # weight files. Deps-based detection (torch/transformers/onnxruntime in
    # requirements/pyproject) is intentionally NOT done here: the fingerprint
    # is a pure function of the path list and never reads file contents.
    Detector(
        Feature("ml"),
        _ext(".pt", ".onnx", ".gguf", ".safetensors"),
    ),
)


class DefaultFingerprinter:
    """Default implementation of the `Fingerprinter` port."""

    __slots__ = ("_detectors",)

    def __init__(self, detectors: tuple[Detector, ...] = _DETECTORS) -> None:
        self._detectors = detectors

    def fingerprint(self, tree: tuple[str, ...]) -> FingerprintResult:
        # We collect ALL witness paths per feature, then pick the
        # lexicographically smallest one. This makes the witness independent
        # of input order: ``fp(tree) == fp(shuffle(tree))`` for both features
        # AND evidence. (A first-seen rule would leak input order.)
        witnesses: dict[Feature, list[str]] = {}
        for path in tree:
            for det in self._detectors:
                if det.matches(path):
                    witnesses.setdefault(det.feature, []).append(path)
        matched: dict[Feature, str] = {f: min(paths) for f, paths in witnesses.items()}
        # `common` is implicitly part of any non-empty fingerprint. Recording
        # it in `features` keeps the contract:
        #     output := f(features, options, templates, rules)
        # so that `generate()` is a pure function of the fingerprint's
        # `features` tuple alone (no hidden dependency on the template
        # repository's contents).
        if matched:
            matched.setdefault(Feature("common"), "(implicit)")
        ordered_features = tuple(sorted(matched.keys()))
        evidence = tuple(sorted((f.name, matched[f]) for f in ordered_features))
        return FingerprintResult(features=ordered_features, evidence=evidence)
