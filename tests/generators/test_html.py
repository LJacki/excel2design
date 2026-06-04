"""Tests for the HTML block-diagram generator (SPEC §4.2 + §5.7).

These tests verify:
  * Basic content (module name, port names) appears in output
  * Port order within inputs and within outputs is stable
  * Parameterised widths (e.g. [DATA_WIDTH-1:0]) survive verbatim
  * 1-bit widths are omitted
  * inout ports are present and labelled
  * signed ports carry the "signed" badge
  * zero-port modules render gracefully (no crash, empty-state marker present)
  * Two consecutive renders of the same Module are byte-identical
  * Output is valid HTML (parseable by html.parser)
"""

from __future__ import annotations

import html.parser
from pathlib import Path

import pytest

from excel2design import Module, Port, SignalType
from excel2design.parsers.excel import get_module, parse_workbook
from excel2design.generators.diagram_html import PortView, generate_html


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
def multi_clock() -> Module:
    return _load("multi_clock")


@pytest.fixture(scope="module")
def empty_ports() -> Module:
    return _load("empty_ports")


# ---- Tests -----------------------------------------------------------------

def test_basic_module_tokens(uart_rx: Module) -> None:
    """uart_rx: module name + key port names must be present."""
    out = generate_html(uart_rx)
    assert "uart_rx" in out
    assert "clk" in out
    assert "rx_data" in out
    assert "rx_valid" in out
    assert "fifo_data" in out


def test_input_port_order_matches_excel(uart_rx: Module) -> None:
    """Inputs in the HTML appear in the same order as Excel rows.

    Per SPEC §3.5.4, ports within a direction group must NOT be reordered.
    """
    out = generate_html(uart_rx)
    expected_inputs = ["clk", "rst_n", "rx_pad", "baud_tick"]
    positions = [out.index(name) for name in expected_inputs]
    assert positions == sorted(positions), (
        f"Inputs out of order; positions={positions} for {expected_inputs}"
    )


def test_output_port_order_matches_excel(uart_rx: Module) -> None:
    """Outputs in the HTML appear in the same order as Excel rows."""
    out = generate_html(uart_rx)
    expected_outputs = ["rx_data", "rx_valid", "fifo_full", "fifo_data"]
    positions = [out.index(name) for name in expected_outputs]
    assert positions == sorted(positions), (
        f"Outputs out of order; positions={positions} for {expected_outputs}"
    )


def test_parameterised_width_preserved(uart_rx: Module) -> None:
    """[DATA_WIDTH-1:0] must appear verbatim (no evaluation)."""
    out = generate_html(uart_rx)
    assert "[DATA_WIDTH-1:0]" in out


def test_one_bit_width_omitted(uart_rx: Module) -> None:
    """clk/rst_n are 1-bit; their row must NOT contain a width badge."""
    out = generate_html(uart_rx)
    # The first occurrence of "clk" is in the input port row (port name).
    clk_idx = out.index("clk")
    # Bound the window to roughly the port block (clamp to end of doc).
    window = out[clk_idx:clk_idx + 500]
    # clk is 1-bit wire → no width bracket must appear in its port block.
    # We allow "[" elsewhere in the document (rx_data etc.), but NOT in this
    # 500-char window that contains clk's port row.
    assert "[" not in window, (
        f"clk (1-bit) window unexpectedly contains a width bracket: {window!r}"
    )
    # Sanity: rx_data (8-bit parameterised) does carry a width bracket
    assert "[DATA_WIDTH-1:0]" in out


def test_inout_ports_present(axi_crossbar: Module) -> None:
    """axi_crossbar has inout ports; they must be rendered in the inout strip."""
    out = generate_html(axi_crossbar)
    # These five are inouts per the fixture (s_axi_*_user × 4 + debug)
    for name in ("s_axi_awuser", "s_axi_aruser", "s_axi_buser", "s_axi_ruser", "debug"):
        assert name in out, f"Missing inout port {name!r}"
    # inout strip heading must be present
    assert "Inouts" in out
    # Inputs section heading present
    assert "Inputs" in out
    # Outputs section heading present
    assert "Outputs" in out
    # The 'inout' direction badge must appear (used as a CSS class trigger)
    assert "badge--inout" in out


def test_signed_badge_present(uart_rx: Module) -> None:
    """fifo_data is signed=1; output must contain the 'signed' badge text."""
    out = generate_html(uart_rx)
    assert "signed" in out
    # Locate fifo_data's section and check the signed badge sits next to it
    fifo_idx = out.index("fifo_data")
    window = out[fifo_idx:fifo_idx + 500]
    assert "signed" in window


def test_empty_ports_module_renders(empty_ports: Module) -> None:
    """Zero-port module: must not crash and must show the empty-state marker."""
    out = generate_html(empty_ports)
    assert "empty_ports" in out
    assert "no ports" in out
    # And the document must still be well-formed HTML
    v = HTMLValidator()
    v.feed(out)
    v.close()
    assert v.errors == [], f"empty_ports HTML parser errors: {v.errors}"
    # No 'Inputs'/'Outputs' headings should appear (no body block at all)
    assert "Inputs" not in out
    assert "Outputs" not in out


def test_byte_stable_on_repeat(uart_rx: Module) -> None:
    """SPEC §5.7.10: two consecutive renders of the same Module are byte-identical."""
    a = generate_html(uart_rx)
    b = generate_html(uart_rx)
    assert a == b


def test_byte_stable_on_repeat_large(axi_crossbar: Module) -> None:
    """Same byte-stability check on the largest fixture (30+ ports, inouts)."""
    a = generate_html(axi_crossbar)
    b = generate_html(axi_crossbar)
    assert a == b


def test_html_is_well_formed(uart_rx: Module, axi_crossbar: Module,
                              multi_clock: Module, empty_ports: Module) -> None:
    """All four fixture outputs must parse cleanly with html.parser."""
    for m in (uart_rx, axi_crossbar, multi_clock, empty_ports):
        out = generate_html(m)
        v = HTMLValidator()
        v.feed(out)
        v.close()
        # No unmatched tags / no parser errors:
        assert v.errors == [], f"{m.name}: parser errors {v.errors}"


def test_type_badges_present(uart_rx: Module) -> None:
    """wire/reg type badges must be styled via their CSS classes."""
    out = generate_html(uart_rx)
    assert "badge--wire" in out
    assert "badge--reg" in out
    assert "wire</span>" in out   # 'wire' type label
    assert "reg</span>" in out    # 'reg' type label


def test_reg_clk_badge_for_registers(uart_rx: Module) -> None:
    """Each reg/logic port must carry a 'clk: <name>' badge in its meta row."""
    out = generate_html(uart_rx)
    assert "clk: clk" in out  # rx_data / rx_valid / fifo_full / fifo_data all use clk


def test_no_crlf_or_trailing_whitespace(uart_rx: Module) -> None:
    """SPEC §5.7.2: LF line endings, no trailing whitespace on any line."""
    out = generate_html(uart_rx)
    assert "\r" not in out
    for i, line in enumerate(out.split("\n"), start=1):
        assert line == line.rstrip(), f"Line {i} has trailing whitespace: {line!r}"


def test_comment_shown_verbatim(uart_rx: Module) -> None:
    """Port comments (中文 + English) must appear in the output."""
    out = generate_html(uart_rx)
    assert "系统时钟" in out
    assert "波特率 tick" in out
    assert "接收数据" in out


def test_port_view_width_str_omits_for_one_bit() -> None:
    """Unit-level: PortView renders 1-bit width as empty string."""
    from excel2design.parsers.width import PortWidth
    from excel2design.core.models import Direction

    one_bit = Port(
        name="x",
        direction=Direction.INPUT,
        width=PortWidth(raw="1", msb=0, is_parameter=False),
        type=SignalType.WIRE,
    )
    assert PortView.from_port(one_bit).width_str == ""

    fixed8 = Port(
        name="y",
        direction=Direction.OUTPUT,
        width=PortWidth(raw="8", msb=7, is_parameter=False),
        type=SignalType.REG,
    )
    assert PortView.from_port(fixed8).width_str == "[7:0]"

    param = Port(
        name="z",
        direction=Direction.OUTPUT,
        width=PortWidth(raw="DATA_WIDTH", msb=None, is_parameter=True),
        type=SignalType.REG,
    )
    assert PortView.from_port(param).width_str == "[DATA_WIDTH-1:0]"


def test_doctype_and_html_root(uart_rx: Module) -> None:
    """Output must be a complete HTML document starting with <!DOCTYPE html>."""
    out = generate_html(uart_rx)
    assert out.lstrip().startswith("<!DOCTYPE html>")
    assert "</html>" in out
    assert "<body>" in out
    assert "</body>" in out


def test_has_arrow_elements(uart_rx: Module) -> None:
    """v0.4: HTML must contain directional arrow spans with color classes."""
    out = generate_html(uart_rx)
    assert "port__arrow--in" in out
    assert "port__arrow--out" in out
    # Unicode arrows
    assert "&#8594;" in out  # → right arrow (input/output)
    # inout: only for modules with inout ports
    if "s_axi_awuser" in out:
        assert "&#8596;" in out  # ↔ bidirectional arrow


# ---- HTML validator helper -------------------------------------------------

class HTMLValidator(html.parser.HTMLParser):
    """Minimal HTML parser wrapper that collects errors."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[str] = []

    def error(self, message: str) -> None:  # html.parser API
        self.errors.append(message)
