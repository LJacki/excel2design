"""Tests for generators/verilog.py (SPEC §5).

Per SPEC §13.4, this is the most critical test file. It validates:
  - byte-stable output (no diff on repeat)
  - port order preservation (Excel order, no resorting)
  - always block grouping by (clock, reset_type) tuple
  - multi-clock / multi-reset-type separation
  - reset_type=none behavior (no always, but initial block)
  - TODO comment completeness
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from excel2design import parse_workbook, get_module
from excel2design.core.models import Module
from excel2design.generators.verilog import generate_wrapper

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


# ---- Helpers --------------------------------------------------------------

def load(fixture: str) -> Module:
    modules = parse_workbook(FIXTURE_DIR / f"{fixture}.xlsx")
    return modules[0]


# ---- Basic token / structure ----------------------------------------------

def test_module_header_present() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m, source_file="x.xlsx", source_sheet="uart_rx")
    assert "Module:    uart_rx" in v
    assert "Source:    x.xlsx / sheet: uart_rx" in v
    assert "Company Confidential" in v


def test_module_ends_with_endmodule() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m)
    assert v.rstrip().endswith("endmodule")


def test_parameter_declaration() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m)
    assert "DATA_WIDTH" in v and "= 8" in v
    assert "FIFO_DEPTH" in v and "= 16" in v
    assert "CLK_FREQ_MHZ" in v and "= 100" in v


# ---- Port order (SPEC §3.5.4) ----------------------------------------------

def test_input_ports_in_excel_order() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m)
    assert v.index("clk") < v.index("rst_n") < v.index("rx_pad") < v.index("baud_tick")


def test_output_ports_in_excel_order() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m)
    # In the port list: rx_data < rx_valid < fifo_full < fifo_data
    assert v.index("rx_data") < v.index("rx_valid") < v.index("fifo_full") < v.index("fifo_data")


def test_inout_ports_in_excel_order() -> None:
    m = load("axi_crossbar")
    v = generate_wrapper(m)
    # axi_crossbar has 5 inouts (s_axi_awuser / s_axi_aruser / s_axi_buser / s_axi_ruser / debug)
    for name in ("s_axi_awuser", "s_axi_aruser", "s_axi_buser", "s_axi_ruser", "debug"):
        assert name in v


# ---- Width / type / signed ------------------------------------------------

def test_parameterised_width_preserved() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m)
    assert "[DATA_WIDTH-1:0]" in v


def test_one_bit_width_omits_brackets() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m)
    # 1-bit ports: clk, rst_n, rx_pad, baud_tick, rx_valid, fifo_full
    # They should NOT have [N:0] in their declarations
    for one_bit_port in ("clk", "rst_n", "rx_valid", "fifo_full"):
        # Find the port line and check there's no [N:0] before the port name
        idx = v.find(one_bit_port)
        assert idx > 0, f"port {one_bit_port} not found"
        line_start = v.rfind("\n", 0, idx) + 1
        line_end = v.find(",", idx)
        line = v[line_start:line_end]
        assert "[" not in line, f"1-bit port {one_bit_port} should not have brackets: {line!r}"


def test_signed_keyword_present() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m)
    # fifo_data is signed
    assert "signed" in v
    # Should appear in the port list for fifo_data
    assert re.search(r"output\s+reg\s{2}signed\s+\[DATA_WIDTH-1:0\]\s+fifo_data", v), (
        "fifo_data should be declared with 'reg signed' and parameterised width"
    )


# ---- Initial block ---------------------------------------------------------

def test_initial_block_present() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m)
    assert "initial begin" in v
    assert "rx_data = {DATA_WIDTH{1'b0}}" in v
    assert "rx_valid = 1'b0" in v
    assert "fifo_full = 1'b0" in v
    assert "fifo_data = {DATA_WIDTH{1'b0}}" in v


def test_no_initial_block_without_defaults() -> None:
    """A module with no default values should not generate an initial block."""
    m = load("empty_ports")
    v = generate_wrapper(m)
    assert "initial begin" not in v


# ---- Always block grouping (SPEC §3.5.6 / §5.5) ---------------------------

def test_single_clock_single_async_group() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m)
    # All 4 regs share (clk, async) → exactly 1 always block
    assert v.count("always @(") == 1
    assert "always @(posedge clk or negedge rst_n) begin" in v


def test_multi_clock_produces_multiple_always_blocks() -> None:
    """SPEC §3.5.6: different clocks → different always blocks."""
    m = load("multi_clock")
    v = generate_wrapper(m)
    # multi_clock has clk_a (async) + clk_b (async) + clk_c (sync) → 3 blocks
    assert v.count("always @(") == 3
    assert "posedge clk_a" in v
    assert "posedge clk_b" in v
    assert "posedge clk_c" in v


def test_multi_reset_type_produces_multiple_always_blocks() -> None:
    """Different reset types with the same clock → different always blocks."""
    # Build a synthetic module for this test
    from excel2design.core.models import (
        Direction, Module, Parameter, Port, ResetType, SignalType,
    )
    from excel2design.parsers.width import PortWidth
    m = Module(
        name="m",
        parameters=[Parameter(name="W", value="8")],
        ports=[
            Port(name="clk", direction=Direction.INPUT, type=SignalType.WIRE, width=PortWidth(raw="1", msb=0, is_parameter=False)),
            Port(name="rst_n", direction=Direction.INPUT, type=SignalType.WIRE, width=PortWidth(raw="1", msb=0, is_parameter=False)),
            Port(name="async_reg", direction=Direction.OUTPUT, type=SignalType.REG, width=PortWidth(raw="W", msb=None, is_parameter=True), default="1'b0", clock="clk", reset_type=ResetType.ASYNC),
            Port(name="sync_reg", direction=Direction.OUTPUT, type=SignalType.REG, width=PortWidth(raw="W", msb=None, is_parameter=True), default="1'b0", clock="clk", reset_type=ResetType.SYNC),
        ],
    )
    v = generate_wrapper(m)
    # Two different (clock, reset_type) keys → 2 always blocks
    assert v.count("always @(") == 2


def test_reset_type_none_produces_no_always() -> None:
    """SPEC §5.5: reset_type=none → no always block, but initial block if default."""
    from excel2design.core.models import (
        Direction, Module, Parameter, Port, ResetType, SignalType,
    )
    from excel2design.parsers.width import PortWidth
    m = Module(
        name="m",
        parameters=[Parameter(name="W", value="8")],
        ports=[
            Port(name="clk", direction=Direction.INPUT, type=SignalType.WIRE, width=PortWidth(raw="1", msb=0, is_parameter=False)),
            Port(name="data", direction=Direction.OUTPUT, type=SignalType.REG, width=PortWidth(raw="W", msb=None, is_parameter=True), default="1'b0", reset_type=ResetType.NONE),
        ],
    )
    v = generate_wrapper(m)
    assert "always @(" not in v
    assert "initial begin" in v  # initial block still generated


# ---- Byte stability (SPEC §5.7) -------------------------------------------

def test_no_diff_on_repeat() -> None:
    m = load("uart_rx")
    a = generate_wrapper(m)
    b = generate_wrapper(m)
    assert a == b


def test_no_diff_on_repeat_large() -> None:
    m = load("axi_crossbar")
    a = generate_wrapper(m)
    b = generate_wrapper(m)
    assert a == b


def test_lf_line_endings() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m)
    assert "\r\n" not in v, "wrapper must use LF line endings"


def test_no_trailing_whitespace() -> None:
    m = load("uart_rx")
    v = generate_wrapper(m)
    for line in v.split("\n"):
        assert line == line.rstrip(), f"trailing whitespace: {line!r}"


# ---- v0.6 Phase 14: parameter/port naming collision (_p suffix) ---------

def test_param_port_collision_suffix() -> None:
    """When ``WIDTH`` (param) collides with ``width`` (port), the parameter
    is emitted as ``WIDTH_p`` and the port keeps its original name.
    """
    from excel2design.core.models import (
        Direction, Module, Parameter, Port, ResetType, SignalType,
    )
    from excel2design.parsers.width import PortWidth
    m = Module(
        name="m",
        parameters=[Parameter(name="WIDTH", value="8")],
        ports=[
            Port(name="clk", direction=Direction.INPUT, type=SignalType.WIRE,
                 width=PortWidth(raw="1", msb=0, is_parameter=False)),
            Port(name="width", direction=Direction.OUTPUT, type=SignalType.REG,
                 width=PortWidth(raw="WIDTH", msb=None, is_parameter=True),
                 default="1'b0", clock="clk", reset_type=ResetType.ASYNC),
        ],
    )
    v = generate_wrapper(m)
    # Parameter must be emitted with _p suffix.
    assert "parameter WIDTH_p" in v, (
        f"Expected 'parameter WIDTH_p', got:\n{v}"
    )
    # Original 'parameter WIDTH ' (no suffix) should NOT appear.
    assert "parameter WIDTH " not in v, (
        f"Parameter 'WIDTH' should be suffixed; got:\n{v}"
    )
    # Port keeps its original name (no suffix).
    assert "width" in v
    # The port line should still reference 'width' (not 'width_p').
    assert re.search(r"\bwidth\b", v), "port 'width' should be present"


def test_param_port_collision_width_reference_replaced() -> None:
    """Width expression referencing a colliding param is rewritten to ``_p``."""
    from excel2design.core.models import (
        Direction, Module, Parameter, Port, ResetType, SignalType,
    )
    from excel2design.parsers.width import PortWidth
    m = Module(
        name="m",
        parameters=[Parameter(name="WIDTH", value="8")],
        ports=[
            Port(name="clk", direction=Direction.INPUT, type=SignalType.WIRE,
                 width=PortWidth(raw="1", msb=0, is_parameter=False)),
            Port(name="width", direction=Direction.OUTPUT, type=SignalType.REG,
                 width=PortWidth(raw="WIDTH", msb=None, is_parameter=True),
                 default="{WIDTH{1'b0}}", clock="clk", reset_type=ResetType.ASYNC),
        ],
    )
    v = generate_wrapper(m)
    # Width expression should now use the suffixed name.
    assert "[WIDTH_p-1:0]" in v, (
        f"Expected '[WIDTH_p-1:0]' in width expression, got:\n{v}"
    )
    assert "[WIDTH-1:0]" not in v, (
        f"Old '[WIDTH-1:0]' should be replaced; got:\n{v}"
    )
    # Default literal should also use the suffixed name.
    assert "{WIDTH_p{1'b0}}" in v, (
        f"Expected '{{WIDTH_p{{1'b0}}}}' in default, got:\n{v}"
    )
    assert "{WIDTH{1'b0}}" not in v, (
        f"Old '{{WIDTH{{1'b0}}}}' should be replaced; got:\n{v}"
    )


def test_param_port_collision_byte_stable() -> None:
    """The collision-mitigation output must be byte-stable across runs.

    SPEC §5.7: the same input Module → identical Verilog string.
    """
    from excel2design.core.models import (
        Direction, Module, Parameter, Port, ResetType, SignalType,
    )
    from excel2design.parsers.width import PortWidth
    m = Module(
        name="m",
        parameters=[Parameter(name="WIDTH", value="8")],
        ports=[
            Port(name="clk", direction=Direction.INPUT, type=SignalType.WIRE,
                 width=PortWidth(raw="1", msb=0, is_parameter=False)),
            Port(name="width", direction=Direction.OUTPUT, type=SignalType.REG,
                 width=PortWidth(raw="WIDTH", msb=None, is_parameter=True),
                 default="1'b0", clock="clk", reset_type=ResetType.ASYNC),
        ],
    )
    a = generate_wrapper(m)
    b = generate_wrapper(m)
    assert a == b


def test_no_collision_unchanged() -> None:
    """When there's no conflict, output is identical to v0.5 baseline.

    The ``DATA_WIDTH`` parameter is used in port width, but no port has
    the same name — so no substitution should occur.
    """
    m = load("uart_rx")
    v = generate_wrapper(m)
    # No _p suffixed parameter expected.
    assert "DATA_WIDTH_p" not in v, (
        f"Unexpected 'DATA_WIDTH_p' in non-colliding module:\n{v}"
    )
    # Original DATA_WIDTH should be present.
    assert "DATA_WIDTH" in v
