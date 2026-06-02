"""Tests for the Excalidraw block-diagram generator (SPEC §4.4).

Strictly eight cases, matching the task spec exactly:
    1. JSON is well-formed (json.loads)
    2. basic module tokens
    3. input port order matches Excel
    4. output port order matches Excel
    5. rectangle element present
    6. text-element count = ports + module-name
    7. byte-stable on repeated generation
    8. empty-ports module renders gracefully
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from excel2design import Module
from excel2design.generators.diagram_excalidraw import generate_excalidraw
from excel2design.parsers.excel import get_module, parse_workbook


# ---- Fixture helpers -------------------------------------------------------

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


def _load(name: str) -> Module:
    modules = parse_workbook(FIXTURE_DIR / f"{name}.xlsx")
    return get_module(modules, name)


@pytest.fixture(scope="module")
def uart_rx() -> Module:
    return _load("uart_rx")


@pytest.fixture(scope="module")
def empty_ports() -> Module:
    return _load("empty_ports")


# ---- Tests (strict 8) ------------------------------------------------------

def test_json_is_well_formed(uart_rx: Module) -> None:
    """The output must be valid JSON (json.loads does not raise)."""
    out = generate_excalidraw(uart_rx)
    # json.loads must succeed and yield the scene dict.
    scene = json.loads(out)
    assert scene["type"] == "excalidraw"
    assert scene["version"] == 2
    assert isinstance(scene["elements"], list)


def test_basic_tokens(uart_rx: Module) -> None:
    """uart_rx scene must contain the module name and representative port names."""
    out = generate_excalidraw(uart_rx)
    assert "uart_rx" in out
    assert "clk" in out
    assert "rx_data" in out


def test_input_port_order(uart_rx: Module) -> None:
    """Inputs appear in the scene in the same order as Excel rows (SPEC §3.5.4)."""
    out = generate_excalidraw(uart_rx)
    expected = ["clk", "rst_n", "rx_pad", "baud_tick"]
    positions = [out.index(name) for name in expected]
    assert positions == sorted(positions), (
        f"Inputs out of order; positions={positions} for {expected}"
    )


def test_output_port_order(uart_rx: Module) -> None:
    """Outputs appear in the scene in the same order as Excel rows."""
    out = generate_excalidraw(uart_rx)
    expected = ["rx_data", "rx_valid", "fifo_full", "fifo_data"]
    positions = [out.index(name) for name in expected]
    assert positions == sorted(positions), (
        f"Outputs out of order; positions={positions} for {expected}"
    )


def test_rectangle_present(uart_rx: Module) -> None:
    """The scene must contain at least one rectangle element (the module body)."""
    scene = json.loads(generate_excalidraw(uart_rx))
    rects = [e for e in scene["elements"] if e["type"] == "rectangle"]
    assert len(rects) >= 1, "expected at least one rectangle element"
    # The module rect must carry the hand-drawn Excalidraw look.
    rect = rects[0]
    assert rect["roughness"] == 1
    assert rect["strokeStyle"] == "solid"
    assert rect["fillStyle"] == "hachure"
    # All required Excalidraw fields are present.
    for field in (
        "id", "x", "y", "width", "height", "seed",
        "strokeWidth", "opacity", "angle", "groupIds",
        "frameId", "roundness", "boundElements", "updated", "link", "locked",
    ):
        assert field in rect, f"rectangle missing required field: {field!r}"


def test_text_elements_count(uart_rx: Module) -> None:
    """text-element count = #ports + 1 (module name)."""
    scene = json.loads(generate_excalidraw(uart_rx))
    texts = [e for e in scene["elements"] if e["type"] == "text"]
    n_ports = len(uart_rx.ports)
    assert len(texts) == n_ports + 1, (
        f"expected {n_ports + 1} text elements (ports + module name), "
        f"got {len(texts)}"
    )


def test_byte_stable_on_repeat(uart_rx: Module) -> None:
    """Two consecutive renders of the same Module must be byte-identical.

    Seeds are derived from element index (not random), coordinates are int,
    and we emit a trailing LF only — no timestamps, no UUIDs.
    """
    a = generate_excalidraw(uart_rx)
    b = generate_excalidraw(uart_rx)
    assert a == b


def test_empty_ports_renders(empty_ports: Module) -> None:
    """Zero-port module must not crash and must still produce valid Excalidraw."""
    out = generate_excalidraw(empty_ports)
    scene = json.loads(out)  # must not raise
    assert scene["type"] == "excalidraw"
    # Module name should still appear (text-name element).
    assert "empty_ports" in out
    # We must still have the module rectangle and the module-name text.
    rects = [e for e in scene["elements"] if e["type"] == "rectangle"]
    texts = [e for e in scene["elements"] if e["type"] == "text"]
    assert len(rects) == 1
    assert len(texts) == 1  # the module-name text only — no ports
