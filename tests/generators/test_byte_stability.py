"""P0-4 regression: SVG output must be byte-stable across processes.

Prior to the P0-4 fix, the diagram generators used Python's built-in
``hash()`` for clock-name → colour / marker-id mapping, which is randomised
by ``PYTHONHASHSEED`` and thus produced different bytes for the same
fixture in different processes. This test runs the CLI twice with
different ``PYTHONHASHSEED`` values and asserts the outputs match.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
PY = sys.executable


def _run_svg_to(out_dir: Path, hash_seed: int | None) -> Path:
    env = os.environ.copy()
    if hash_seed is None:
        env.pop("PYTHONHASHSEED", None)
    else:
        env["PYTHONHASHSEED"] = str(hash_seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [PY, "-m", "excel2design.cli", "diagram",
         str(FIXTURE_DIR / "multi_clock.xlsx"), "multi_clock",
         "--format", "svg", "--output", str(out_dir)],
        capture_output=True, text=True, env=env, cwd=REPO_ROOT,
    )
    assert r.returncode == 0, f"seed={hash_seed} stderr={r.stderr}"
    out = out_dir / "multi_clock.svg"
    assert out.exists()
    return out


def test_svg_byte_stable_across_hash_seeds(tmp_path: Path) -> None:
    """Same fixture, two different PYTHONHASHSEED values → identical bytes."""
    out1 = _run_svg_to(tmp_path / "run1", hash_seed=42)
    out2 = _run_svg_to(tmp_path / "run2", hash_seed=99)
    assert out1.read_bytes() == out2.read_bytes(), (
        "SVG output is not byte-stable across PYTHONHASHSEED — "
        "P0-4 regression!"
    )


def test_clock_color_deterministic() -> None:
    """The clock_color helper itself must be process-stable."""
    # Import inside the test so a different PYTHONHASHSEED in this
    # process doesn't affect the test outcome.
    from excel2design.utils.clock_colors import clock_color

    # Two separate processes, different seeds — same clock → same colour.
    import subprocess

    def _color(clock: str) -> str:
        return clock_color(clock, is_input=True)

    # In-process, calling twice must obviously give the same answer.
    a = _color("clk_a")
    b = _color("clk_a")
    assert a == b

    # Across processes: run a tiny snippet in two different seeds.
    snippet = (
        "from excel2design.utils.clock_colors import clock_color; "
        "print(clock_color('clk_a', is_input=True))"
    )
    r1 = subprocess.run(
        [PY, "-c", snippet], capture_output=True, text=True,
        env={**os.environ, "PYTHONHASHSEED": "1"}, cwd=REPO_ROOT,
    )
    r2 = subprocess.run(
        [PY, "-c", snippet], capture_output=True, text=True,
        env={**os.environ, "PYTHONHASHSEED": "7"}, cwd=REPO_ROOT,
    )
    assert r1.returncode == 0 and r2.returncode == 0
    assert r1.stdout.strip() == r2.stdout.strip(), (
        f"clock_color is not deterministic across processes: "
        f"seed=1 → {r1.stdout.strip()!r}, seed=7 → {r2.stdout.strip()!r}"
    )


# v0.6 Phase 12 — array_dim byte-stability regression

def test_array_dim_byte_stable() -> None:
    """Generating verilog for a port with array_dim is byte-stable."""
    from excel2design.core.models import (
        Direction, Module, Port, PortWidth, SignalType,
    )
    from excel2design.generators.verilog import generate_wrapper
    p = Port(name="data_bus", direction=Direction.OUTPUT, type=SignalType.WIRE,
             width=PortWidth(raw="1", msb=0, is_parameter=False),
             array_dim=[(7, 0)])
    m = Module(name="arr", ports=[p])
    a = generate_wrapper(m)
    b = generate_wrapper(m)
    assert a == b, "array_dim output not byte-stable"
