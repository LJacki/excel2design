"""Tests for the SVG block-diagram generator (SPEC §4.3 + §5.7).

Eight cases, matching the task spec exactly:
    1. basic module tokens
    2. input port order matches Excel
    3. output port order matches Excel
    4. parameterised widths preserved verbatim
    5. inout ports present
    6. empty-ports module renders gracefully
    7. XML is well-formed (xml.etree parse)
    8. byte-stable on repeated generation
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from excel2design import Module
from excel2design.generators.diagram_svg import generate_svg
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
def axi_crossbar() -> Module:
    return _load("axi_crossbar")


@pytest.fixture(scope="module")
def empty_ports() -> Module:
    return _load("empty_ports")


# ---- Tests (strict 8) ------------------------------------------------------

def test_basic_tokens(uart_rx: Module) -> None:
    """uart_rx SVG must contain the module name and a representative port name."""
    out = generate_svg(uart_rx)
    assert "uart_rx" in out
    assert "clk" in out
    assert "rx_data" in out


def test_input_port_order(uart_rx: Module) -> None:
    """Inputs in the SVG appear in the same order as Excel rows (SPEC §3.5.4)."""
    out = generate_svg(uart_rx)
    expected = ["clk", "rst_n", "rx_pad", "baud_tick"]
    positions = [out.index(name) for name in expected]
    assert positions == sorted(positions), (
        f"Inputs out of order; positions={positions} for {expected}"
    )


def test_output_port_order(uart_rx: Module) -> None:
    """Outputs in the SVG appear in the same order as Excel rows."""
    out = generate_svg(uart_rx)
    expected = ["rx_data", "rx_valid", "fifo_full", "fifo_data"]
    positions = [out.index(name) for name in expected]
    assert positions == sorted(positions), (
        f"Outputs out of order; positions={positions} for {expected}"
    )


def test_parameterised_width_preserved(uart_rx: Module) -> None:
    """[DATA_WIDTH-1:0] must appear verbatim (no evaluation)."""
    out = generate_svg(uart_rx)
    assert "[DATA_WIDTH-1:0]" in out


def test_inout_ports_present(axi_crossbar: Module) -> None:
    """axi_crossbar inout ports must appear in the SVG output."""
    out = generate_svg(axi_crossbar)
    for name in (
        "s_axi_awuser",
        "s_axi_aruser",
        "s_axi_buser",
        "s_axi_ruser",
        "debug",
    ):
        assert name in out, f"Missing inout port {name!r}"


def test_empty_ports_renders(empty_ports: Module) -> None:
    """Zero-port module must not crash and must include module name + empty marker."""
    out = generate_svg(empty_ports)
    assert "empty_ports" in out
    assert "no ports" in out


def test_xml_is_well_formed(
    uart_rx: Module,
    axi_crossbar: Module,
    empty_ports: Module,
) -> None:
    """Generated SVG must parse cleanly with xml.etree.ElementTree."""
    for m in (uart_rx, axi_crossbar, empty_ports):
        out = generate_svg(m)
        # Must not raise ParseError.
        root = ET.fromstring(out)
        # Root must be an <svg> element.
        assert root.tag.endswith("svg"), f"{m.name}: root tag is {root.tag!r}"


def test_byte_stable_on_repeat(uart_rx: Module) -> None:
    """SPEC §5.7: two consecutive renders of the same Module are byte-identical."""
    a = generate_svg(uart_rx)
    b = generate_svg(uart_rx)
    assert a == b


def test_has_arrow_markers(uart_rx: Module) -> None:
    """v0.4: SVG must contain <marker> definitions for directional arrows."""
    out = generate_svg(uart_rx)
    assert "<marker" in out
    assert "marker-end=\"url(#m_" in out  # per-clock domain marker IDs
