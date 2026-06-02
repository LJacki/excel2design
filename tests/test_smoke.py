"""Smoke test - verifies the package can be imported and skeleton exists.

Real unit tests are added in Phase 1.
"""

from __future__ import annotations


def test_package_imports():
    """The package should be importable even with no real code yet."""
    import excel2design  # noqa: F401
    assert hasattr(excel2design, "__file__")


def test_subpackages_exist():
    """Subpackage directories should be present (per Phase 0 plan)."""
    import excel2design.core  # noqa: F401
    import excel2design.parsers  # noqa: F401
    import excel2design.generators  # noqa: F401
    import excel2design.utils  # noqa: F401


def test_pyproject_declares_dependencies():
    """pyproject.toml should list our three core dependencies."""
    from pathlib import Path
    text = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    for dep in ("openpyxl", "Jinja2", "click"):
        assert dep in text, f"Missing dependency declaration: {dep}"
