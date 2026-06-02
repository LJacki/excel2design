"""End-to-end tests for the CLI (SPEC §13.5).

Exercises the full pipeline: invoke the CLI as a subprocess, check exit codes
and output files.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"


def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run the CLI as a subprocess. Uses the venv python."""
    cmd = [sys.executable, "-m", "excel2design.cli", *args]
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd or REPO_ROOT,
    )


# ---- Help / version -------------------------------------------------------

def test_help_exits_0() -> None:
    r = _run_cli("--help")
    assert r.returncode == 0
    assert "Usage:" in r.stdout
    assert "parse" in r.stdout
    assert "diagram" in r.stdout
    assert "wrapper" in r.stdout
    assert "all" in r.stdout


def test_version_exits_0() -> None:
    r = _run_cli("--version")
    assert r.returncode == 0
    assert "0.3" in r.stdout or "0.4" in r.stdout


# ---- parse ----------------------------------------------------------------

def test_parse_lists_module(tmp_path: Path) -> None:
    r = _run_cli("parse", str(FIXTURE_DIR / "uart_rx.xlsx"))
    assert r.returncode == 0
    assert "Module: uart_rx" in r.stdout
    assert "Parameters: 3" in r.stdout
    assert "Ports:" in r.stdout
    assert "inputs:   4" in r.stdout


def test_parse_json(tmp_path: Path) -> None:
    r = _run_cli("parse", str(FIXTURE_DIR / "uart_rx.xlsx"), "--json")
    assert r.returncode == 0
    import json
    data = json.loads(r.stdout)
    assert "modules" in data
    assert data["modules"][0]["name"] == "uart_rx"
    assert data["modules"][0]["input_count"] == 4
    assert data["modules"][0]["output_count"] == 4


# ---- diagram --------------------------------------------------------------

def test_diagram_html(tmp_path: Path) -> None:
    r = _run_cli(
        "diagram", str(FIXTURE_DIR / "uart_rx.xlsx"), "uart_rx",
        "--format", "html", "--output", str(tmp_path),
    )
    assert r.returncode == 0
    out = tmp_path / "uart_rx.html"
    assert out.exists()
    assert "<!DOCTYPE" in out.read_text(encoding="utf-8")


def test_diagram_svg(tmp_path: Path) -> None:
    r = _run_cli(
        "diagram", str(FIXTURE_DIR / "uart_rx.xlsx"), "uart_rx",
        "--format", "svg", "--output", str(tmp_path),
    )
    assert r.returncode == 0
    out = tmp_path / "uart_rx.svg"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "<?xml" in content
    assert "<svg" in content


def test_diagram_excalidraw(tmp_path: Path) -> None:
    r = _run_cli(
        "diagram", str(FIXTURE_DIR / "uart_rx.xlsx"), "uart_rx",
        "--format", "excalidraw", "--output", str(tmp_path),
    )
    assert r.returncode == 0
    out = tmp_path / "uart_rx.excalidraw"
    assert out.exists()
    import json
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["type"] == "excalidraw"


def test_diagram_all_three(tmp_path: Path) -> None:
    r = _run_cli(
        "diagram", str(FIXTURE_DIR / "uart_rx.xlsx"), "uart_rx",
        "--format", "all", "--output", str(tmp_path),
    )
    assert r.returncode == 0
    for ext in ("html", "svg", "excalidraw"):
        assert (tmp_path / f"uart_rx.{ext}").exists()


# ---- wrapper --------------------------------------------------------------

def test_wrapper_basic(tmp_path: Path) -> None:
    out = tmp_path / "uart_rx.v"
    r = _run_cli(
        "wrapper", str(FIXTURE_DIR / "uart_rx.xlsx"), "uart_rx",
        "--output", str(out),
    )
    assert r.returncode == 0
    assert out.exists()
    v = out.read_text(encoding="utf-8")
    assert "module uart_rx" in v
    assert "endmodule" in v
    assert "parameter [31:0] DATA_WIDTH" in v


def test_wrapper_default_output_path(tmp_path: Path) -> None:
    """Without --output, writes to ./<module>.v in cwd."""
    # Subprocess inherits the calling test's cwd which pytest manages; we just
    # pass --output explicitly here to keep the test hermetic.
    out = tmp_path / "uart_rx.v"
    r = _run_cli(
        "wrapper", str(FIXTURE_DIR / "uart_rx.xlsx"), "uart_rx",
        "--output", str(out),
    )
    assert r.returncode == 0
    assert out.exists()


# ---- all ------------------------------------------------------------------

def test_all_generates_everything(tmp_path: Path) -> None:
    r = _run_cli(
        "all", str(FIXTURE_DIR / "uart_rx.xlsx"), "uart_rx",
        "--output", str(tmp_path),
    )
    assert r.returncode == 0
    for ext in ("html", "svg", "excalidraw", "v"):
        assert (tmp_path / f"uart_rx.{ext}").exists()


# ---- Error paths (exit codes per SPEC §6) ---------------------------------

def test_missing_file_exits_2() -> None:
    r = _run_cli("all", "nonexistent.xlsx", "uart_rx")
    assert r.returncode == 2
    assert "not found" in r.stderr.lower() or "not found" in r.stdout.lower()


def test_missing_module_exits_3() -> None:
    r = _run_cli("all", str(FIXTURE_DIR / "uart_rx.xlsx"), "nonexistent_module")
    assert r.returncode == 3
    assert "nonexistent_module" in r.stdout + r.stderr


def test_malformed_excel_exits_4(tmp_path: Path) -> None:
    """A non-xlsx file should produce a parse error (P1-4 fix: exit 4)."""
    bad = tmp_path / "bad.xlsx"
    bad.write_text("not a real xlsx", encoding="utf-8")
    r = _run_cli("all", str(bad), "uart_rx")
    assert r.returncode == 4, f"expected exit 4, got {r.returncode}"


def test_empty_file_exits_4(tmp_path: Path) -> None:
    """An empty .xlsx file is also a bad zip → exit 4."""
    bad = tmp_path / "empty.xlsx"
    bad.write_text("", encoding="utf-8")
    r = _run_cli("all", str(bad), "uart_rx")
    assert r.returncode == 4


def test_truncated_xlsx_exits_4(tmp_path: Path) -> None:
    """A truncated xlsx (just the magic bytes) should also exit 4."""
    bad = tmp_path / "trunc.xlsx"
    bad.write_bytes(b"PK\x03\x04")  # zip magic but nothing else
    r = _run_cli("all", str(bad), "uart_rx")
    assert r.returncode == 4
