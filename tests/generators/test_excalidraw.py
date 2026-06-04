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
    rect = rects[0]
    assert rect["roughness"] == 1
    assert rect["strokeStyle"] == "solid"
    assert rect["fillStyle"] == "hachure"
    for field in (
        "id", "x", "y", "width", "height", "seed",
        "strokeWidth", "opacity", "angle", "groupIds",
        "frameId", "roundness", "boundElements", "updated", "link", "locked",
    ):
        assert field in rect, f"rectangle missing required field: {field!r}"


def test_port_arrow_labels(uart_rx: Module) -> None:
    """v0.4: port labels are on arrow elements (arrow.text), not separate text elements."""
    scene = json.loads(generate_excalidraw(uart_rx))
    arrows = [e for e in scene["elements"] if e["type"] == "arrow"]
    texts = [e for e in scene["elements"] if e["type"] == "text"]
    # Only the module name is a separate text element
    assert len(texts) == 1, f"expected 1 text (module name only), got {len(texts)}"
    # Arrow count = #ports (no inouts in uart_rx)
    assert len(arrows) == len(uart_rx.ports)
    # Every arrow carries a text label
    for a in arrows:
        assert "text" in a
        assert a["text"] in ["clk", "rst_n", "rx_pad", "baud_tick",
                               "rx_data[DATA_WIDTH-1:0]", "rx_valid",
                               "fifo_full", "fifo_data[DATA_WIDTH-1:0]"]


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
    scene = json.loads(out)
    assert scene["type"] == "excalidraw"
    assert "empty_ports" in out
    rects = [e for e in scene["elements"] if e["type"] == "rectangle"]
    texts = [e for e in scene["elements"] if e["type"] == "text"]
    assert len(rects) == 1
    assert len(texts) == 1  # module name only


def test_font_family_is_helvetica(uart_rx: Module) -> None:
    """v0.4: fontFamily must be 5 (Helvetica/Normal) on arrows and text."""
    scene = json.loads(generate_excalidraw(uart_rx))
    for e in scene["elements"]:
        if "fontFamily" in e:
            assert e["fontFamily"] == 5, f"Expected fontFamily=5, got {e['fontFamily']} for {e['id']}"


def test_arrow_elements_present(uart_rx: Module) -> None:
    """v0.4: every port is an arrow element with text label and arrowhead."""
    scene = json.loads(generate_excalidraw(uart_rx))
    arrows = [e for e in scene["elements"] if e["type"] == "arrow"]
    assert len(arrows) > 0, "Expected at least one arrow element"
    for a in arrows:
        assert "text" in a, f"arrow {a['id']} missing text label"
        assert a.get("endArrowhead") == "arrow"
        assert a["fontFamily"] == 5
