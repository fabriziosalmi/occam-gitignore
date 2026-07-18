# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from occam_gitignore_core import DefaultFingerprinter, Feature


def test_python_is_detected() -> None:
    fp = DefaultFingerprinter().fingerprint(("pyproject.toml", "src/main.py"))
    assert Feature("python") in fp.features


def test_unknown_tree_yields_empty_features() -> None:
    fp = DefaultFingerprinter().fingerprint(("README.md", "LICENSE"))
    assert fp.features == ()


def test_features_are_sorted() -> None:
    fp = DefaultFingerprinter().fingerprint(
        ("Dockerfile", "main.go", "pyproject.toml", "Cargo.toml"),
    )
    assert list(fp.features) == sorted(fp.features)


def test_evidence_matches_features() -> None:
    fp = DefaultFingerprinter().fingerprint(("pyproject.toml", "Dockerfile"))
    feature_names = {f.name for f in fp.features}
    evidence_names = {name for name, _ in fp.evidence}
    assert feature_names == evidence_names


def test_invalid_feature_name_rejected() -> None:
    with pytest.raises(ValueError, match="invalid feature name"):
        Feature("bad name!")


def test_uppercase_feature_name_rejected() -> None:
    with pytest.raises(ValueError, match="lowercase"):
        Feature("Python")


@pytest.mark.parametrize(
    ("tree", "expected"),
    [
        (("pom.xml", "src/main/java/A.java"), "java"),
        (("build.gradle.kts",), "java"),
        (("Gemfile", "app/x.rb"), "ruby"),
        (("App.csproj", "Program.cs"), "csharp"),
        (("Package.swift", "Sources/main.swift"), "swift"),
        (("model.onnx",), "ml"),
        (("checkpoints/model.pt",), "ml"),
        (("weights.safetensors",), "ml"),
        (("llama.gguf",), "ml"),
    ],
)
def test_new_detectors(tree: tuple[str, ...], expected: str) -> None:
    fp = DefaultFingerprinter().fingerprint(tree)
    assert Feature(expected) in fp.features


def test_ml_detection_is_conservative() -> None:
    """A plain Python repo (no model weights) must NOT be flagged as ml."""
    fp = DefaultFingerprinter().fingerprint(("pyproject.toml", "src/main.py"))
    assert Feature("ml") not in fp.features
