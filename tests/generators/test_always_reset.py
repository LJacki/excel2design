"""P0-5 regression: the always-block reset signal must match the per-domain
reset port name, not the hard-coded ``rst_n``.

Prior to the P0-5 fix, ``verilog_wrapper.j2`` emitted ``if (!rst_n) begin``
for every clock domain, even when the design's reset port was named
differently per domain (e.g. ``rst_a_n`` / ``rst_b_n``). This test
constructs a module with two clock domains and two different reset ports
and asserts the generated wrapper uses the right name in each block.
"""

from __future__ import annotations

import re

from excel2design.core.models import (
    Direction, Module, Port, ResetType, SignalType,
)
from excel2design.parsers.width import PortWidth, parse_width
from excel2design.generators.verilog import generate_wrapper


def _make_input(name: str, clock: str | None = None) -> Port:
    return Port(
        name=name,
        direction=Direction.INPUT,
        width=parse_width("1", known_params=set()),
        type=SignalType.WIRE,
        clock=clock,
    )


def _make_output_reg(name: str, clock: str, default: str, reset: ResetType) -> Port:
    return Port(
        name=name,
        direction=Direction.OUTPUT,
        width=parse_width("1", known_params=set()),
        type=SignalType.REG,
        default=default,
        clock=clock,
        reset_type=reset,
    )


def test_always_block_uses_per_domain_reset_name() -> None:
    """Module with clk_a + rst_a_n, clk_b + rst_b_n → wrapper must emit both names."""
    m = Module(
        name="dual_domain",
        parameters=[],
        ports=[
            _make_input("clk_a", clock="clk_a"),
            _make_input("rst_a_n", clock="clk_a"),
            _make_input("clk_b", clock="clk_b"),
            _make_input("rst_b_n", clock="clk_b"),
            _make_output_reg("reg_a", "clk_a", "1'b0", ResetType.ASYNC),
            _make_output_reg("reg_b", "clk_b", "1'b0", ResetType.ASYNC),
        ],
    )
    v = generate_wrapper(m, source_file="test.xlsx", source_sheet="dual_domain")

    # Each clock domain's always block must reference its own reset name.
    # Look for an always block followed by an if (!<reset>) block.
    assert "negedge rst_a_n" in v, "clk_a domain should use rst_a_n"
    assert "negedge rst_b_n" in v, "clk_b domain should use rst_b_n"
    assert "if (!rst_a_n)" in v, "clk_a's if-statement should use rst_a_n"
    assert "if (!rst_b_n)" in v, "clk_b's if-statement should use rst_b_n"

    # And the legacy default must NOT appear as the only reset name.
    # (It would still be legal if there were no rst_*-named ports, but here
    # both rst_a_n and rst_b_n should win over the bare 'rst_n' default.)
    assert "negedge rst_n " not in v and "negedge rst_n," not in v, (
        "wrapper should not emit a bare rst_n block when per-domain resets exist"
    )


def test_always_block_legacy_fallback_when_no_rst_named_port() -> None:
    """If the module has no rst-named port, fall back to literal 'rst_n'."""
    m = Module(
        name="no_rst_port",
        parameters=[],
        ports=[
            _make_input("clk", clock="clk"),
            # Note: no rst_n / rst / reset input
            _make_output_reg("q", "clk", "1'b0", ResetType.ASYNC),
        ],
    )
    v = generate_wrapper(m, source_file="test.xlsx", source_sheet="no_rst_port")
    # Legacy default is fine when nothing better is available.
    assert "negedge rst_n" in v
    assert "if (!rst_n)" in v


def test_sync_reset_does_not_add_negedge() -> None:
    """Sync reset (posedge clk only) must not include the negedge clause."""
    m = Module(
        name="sync_only",
        parameters=[],
        ports=[
            _make_input("clk", clock="clk"),
            _make_input("rst_n", clock="clk"),
            _make_output_reg("q", "clk", "1'b0", ResetType.SYNC),
        ],
    )
    v = generate_wrapper(m, source_file="test.xlsx", source_sheet="sync_only")
    # The clock-only block, not the async one.
    assert re.search(r"always @\(\s*posedge clk\s*\) begin", v), (
        "sync reset block should use posedge clk only"
    )
    assert "negedge" not in v
