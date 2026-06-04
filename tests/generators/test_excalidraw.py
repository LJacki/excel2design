"""Tests for the Excalidraw block-diagram generator (SPEC §4.4).

v0.4: port labels are on text elements bound to arrows via containerId,
      all input arrows uniform length, all output arrows uniform length.
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


# ---- Tests -----------------------------------------------------------------

def test_json_is_well_formed(uart_rx: Module) -> None:
    out = generate_excalidraw(uart_rx)
    scene = json.loads(out)
    assert scene["type"] == "excalidraw"
    assert scene["version"] == 2
    assert isinstance(scene["elements"], list)


def test_basic_tokens(uart_rx: Module) -> None:
    out = generate_excalidraw(uart_rx)
    assert "uart_rx" in out
    assert "clk" in out
    assert "rx_data" in out


def test_input_port_order(uart_rx: Module) -> None:
    out = generate_excalidraw(uart_rx)
    expected = ["clk", "rst_n", "rx_pad", "baud_tick"]
    positions = [out.index(name) for name in expected]
    assert positions == sorted(positions), (
        f"Inputs out of order; positions={positions} for {expected}"
    )


def test_output_port_order(uart_rx: Module) -> None:
    out = generate_excalidraw(uart_rx)
    expected = ["rx_data", "rx_valid", "fifo_full", "fifo_data"]
    positions = [out.index(name) for name in expected]
    assert positions == sorted(positions), (
        f"Outputs out of order; positions={positions} for {expected}"
    )


def test_rectangle_present(uart_rx: Module) -> None:
    scene = json.loads(generate_excalidraw(uart_rx))
    rects = [e for e in scene["elements"] if e["type"] == "rectangle"]
    assert len(rects) >= 1
    rect = rects[0]
    assert rect["roughness"] == 1
    assert rect["strokeStyle"] == "solid"
    assert rect["fillStyle"] == "hachure"


def test_bound_text_arrows(uart_rx: Module) -> None:
    """v0.4: text elements are bound to arrows via containerId."""
    scene = json.loads(generate_excalidraw(uart_rx))
    arrows = [e for e in scene["elements"] if e["type"] == "arrow"]
    texts = [e for e in scene["elements"] if e["type"] == "text"]
    # 1 module name + 8 port texts = 9 text elements
    assert len(texts) == len(uart_rx.ports) + 1
    assert len(arrows) == len(uart_rx.ports)
    # Port texts should have containerId pointing to their arrow
    port_texts = [t for t in texts if t["text"] != "uart_rx"]
    for pt in port_texts:
        assert pt["containerId"] != "", f"text '{pt['text']}' not bound"


def test_uniform_arrow_lengths(uart_rx: Module) -> None:
    """v0.4: all input arrows same length, all output arrows same length."""
    scene = json.loads(generate_excalidraw(uart_rx))
    arrows = [e for e in scene["elements"] if e["type"] == "arrow"]
    # Arrow IDs: "arrow-in-N" for inputs, "arrow-out-N" for outputs
    in_lens = [a["width"] for a in arrows if "arrow-in-" in a["id"]]
    out_lens = [a["width"] for a in arrows if "arrow-out-" in a["id"]]
    assert len(set(in_lens)) == 1, f"input arrows have different lengths: {in_lens}"
    assert len(set(out_lens)) == 1, f"output arrows have different lengths: {out_lens}"


def test_byte_stable_on_repeat(uart_rx: Module) -> None:
    a = generate_excalidraw(uart_rx)
    b = generate_excalidraw(uart_rx)
    assert a == b


def test_empty_ports_renders(empty_ports: Module) -> None:
    out = generate_excalidraw(empty_ports)
    scene = json.loads(out)
    assert scene["type"] == "excalidraw"
    assert "empty_ports" in out
    rects = [e for e in scene["elements"] if e["type"] == "rectangle"]
    texts = [e for e in scene["elements"] if e["type"] == "text"]
    assert len(rects) == 1
    assert len(texts) == 1  # module name only


def test_font_family_is_helvetica(uart_rx: Module) -> None:
    """v0.4: fontFamily must be 5 (Helvetica/Normal) on all text elements."""
    scene = json.loads(generate_excalidraw(uart_rx))
    for e in scene["elements"]:
        if "fontFamily" in e:
            assert e["fontFamily"] == 5, f"Expected fontFamily=5, got {e['fontFamily']} for {e['id']}"


def test_arrow_elements_present(uart_rx: Module) -> None:
    """v0.4: every port has an arrow with endArrowhead and correct color."""
    scene = json.loads(generate_excalidraw(uart_rx))
    arrows = [e for e in scene["elements"] if e["type"] == "arrow"]
    assert len(arrows) > 0
    for a in arrows:
        assert a.get("endArrowhead") == "arrow"
        assert "strokeColor" in a
