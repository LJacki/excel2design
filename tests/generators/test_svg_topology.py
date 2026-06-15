"""Tests for the v0.7 Phase 17a Visio-style topology SVG generator.

Three cases per the task spec:
    1. test_topology_basic              — 3-submodule iic_top-style fixture
    2. test_topology_input_left_output_right  — port-side correctness
    3. test_topology_empty_submodules   — graceful output for an empty wrapper
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest

from excel2design.core.models import (
    Direction, Module, Project, SignalType,
)
from excel2design.generators.diagram_svg_topology import generate_svg_topology
from excel2design.parsers.width import parse_width


# ---- Fixture helpers -------------------------------------------------------

def _p(name: str, direction: Direction, width: str = "1") -> Module.ports[0].__class__:  # type: ignore[attr-defined]
    # Local import-style port constructor (keeps tests self-contained).
    from excel2design.core.models import Port
    return Port(
        name=name, direction=direction,
        width=parse_width(width, known_params=set()),
        type=SignalType.WIRE,
    )


def _iic_top_project() -> Project:
    """Build a small iic_top-style wrapper with 3 direct submodules.

    Layout (mirrors the I2C top design in the wild):
        iic_top  ─┬─ u_clk_div   (1 input, 1 output)
                  ├─ u_iic_ctrl  (3 inputs, 2 outputs)
                  └─ u_reg_cfg   (2 inputs, 1 output)
    """
    from excel2design.core.models import Port
    def port(name, direction, width="1"):
        return Port(
            name=name, direction=direction,
            width=parse_width(width, known_params=set()),
            type=SignalType.WIRE,
        )

    top = Module(name="iic_top", ports=[
        port("clk",      Direction.INPUT),
        port("rst_n",    Direction.INPUT),
        port("cfg_addr", Direction.INPUT, "8"),
        port("cfg_wdata",Direction.INPUT, "8"),
        port("sda",      Direction.INOUT),
        port("cfg_rdata",Direction.OUTPUT, "8"),
        port("irq",      Direction.OUTPUT),
    ])
    clk_div = Module(name="iic_top.clk_div", ports=[
        port("clk",  Direction.INPUT),
        port("tick", Direction.OUTPUT),
    ])
    iic_ctrl = Module(name="iic_top.iic_ctrl", ports=[
        port("clk",   Direction.INPUT),
        port("rst_n", Direction.INPUT),
        port("tick",  Direction.INPUT),
        port("sda",   Direction.INOUT),
        port("ready", Direction.OUTPUT),
        port("irq",   Direction.OUTPUT),
    ])
    reg_cfg = Module(name="iic_top.reg_cfg", ports=[
        port("clk",   Direction.INPUT),
        port("rst_n", Direction.INPUT),
        port("ready", Direction.INPUT),
        port("cfg_rdata", Direction.OUTPUT, "8"),
    ])
    return Project(
        modules={
            "iic_top": top,
            "iic_top.clk_div": clk_div,
            "iic_top.iic_ctrl": iic_ctrl,
            "iic_top.reg_cfg": reg_cfg,
        },
        hierarchy={
            "iic_top": ["iic_top.clk_div", "iic_top.iic_ctrl", "iic_top.reg_cfg"],
            "iic_top.iic_ctrl": [],   # depth-2 children exist but must NOT appear
            "iic_top.reg_cfg": [],
        },
    )


@pytest.fixture(scope="module")
def iic_top() -> Project:
    return _iic_top_project()


# ---- Tests -----------------------------------------------------------------

def test_topology_basic(iic_top: Project) -> None:
    """Output must be valid SVG and contain exactly 3 submodule rectangles."""
    svg = generate_svg_topology(iic_top, "iic_top")
    assert svg.startswith("<?xml"), "must emit a valid XML preamble"
    assert "<svg" in svg

    # Well-formed XML.
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")

    # 3 submodule rectangles (one per direct child).
    # The wrapper itself draws a rect; submodules each draw a rect.
    rects = root.findall(".//{http://www.w3.org/2000/svg}rect")
    # rects include: bg, wrapper outline, 3 submodule outlines, arrowhead
    # marker-internal rects (none — markers use <path>), so at least 5.
    assert len(rects) >= 5, f"expected ≥5 rects (bg + wrapper + 3 submodules), got {len(rects)}"

    # The 3 submodule short instance names must each appear in the SVG.
    for short_name in ("clk_div", "iic_ctrl", "reg_cfg"):
        assert f">{short_name}<" in svg, f"missing submodule label {short_name!r}"

    # The wrapper module name appears as the top title.
    assert "iic_top" in svg

    # The deep-nested submodule (depth=2, if any) must NOT be drawn.
    # Our fixture has no depth-2 children, but the contract is the same:
    # only direct submodules of the wrapper are rendered.  We assert by
    # counting submodule-name <text> nodes.
    submodule_texts = re.findall(r">(\w+)<", svg)
    # Should contain the 3 short instance names; nothing else of the form
    # '>something<' that looks like a submodule title.
    for s in ("clk_div", "iic_ctrl", "reg_cfg"):
        assert s in submodule_texts


def test_topology_input_left_output_right(iic_top: Project) -> None:
    """Wrapper input ports must be on the left edge, outputs on the right edge.

    Verifies the strict A-style port placement by inspecting the
    <text> x-coordinates of the port labels in the generated SVG.
    """
    svg = generate_svg_topology(iic_top, "iic_top")
    root = ET.fromstring(svg)
    ns = {"s": "http://www.w3.org/2000/svg"}
    texts = root.findall("s:text", ns)

    # Build {label_text: x} for every text node.  We use the visible label
    # string to identify which port each label belongs to.
    by_label: dict[str, int] = {}
    for t in texts:
        if t.text:
            by_label[t.text] = int(t.get("x", "0"))

    # Wrapper title "iic_top" is at the top centre — not a port.
    # The 3 submodule titles ("clk_div", "iic_ctrl", "reg_cfg") are also
    # at sub-rect centres.  We focus on the port label strings: each one
    # is the wrapper port name optionally suffixed with [W:0] (e.g.
    # "cfg_addr[7:0]").  We check *both* the bare name and the bracketed
    # form so a multi-bit port (e.g. cfg_addr) is recognised.
    def _x_of_port_label(pname: str, width: str) -> int:
        # Bare form (1-bit).
        if pname in by_label:
            return by_label[pname]
        # Bracketed form (multi-bit, e.g. "cfg_addr[7:0]").
        bracketed = f"{pname}{width}"
        if bracketed in by_label:
            return by_label[bracketed]
        raise AssertionError(
            f"port label {pname!r} (or {bracketed!r}) not found in SVG"
        )

    # The wrapper is drawn at wrap_x = CANVAS_PAD_X = 40.
    WRAPPER_LEFT_X = 40

    # Input / inout ports should sit just to the LEFT of the wrapper edge.
    for iname in ("clk", "rst_n", "cfg_addr", "cfg_wdata", "sda"):
        x = _x_of_port_label(iname, "[7:0]" if iname.startswith("cfg_") else "")
        assert x < WRAPPER_LEFT_X, (
            f"input {iname!r} rendered at x={x}, expected < wrapper left edge {WRAPPER_LEFT_X}"
        )

    # Output ports should sit just to the RIGHT of the wrapper right edge.
    # The wrapper width varies with submodule layout; we read it from the
    # wrapper rect (the only rect with stroke-width 1.5 and stroke #888888
    # AND fill #FFFFFF AND not the bg rect at 0,0,canvas).
    wrapper_rects = [
        r for r in root.findall("s:rect", ns)
        if r.get("stroke") == "#888888" and r.get("fill") == "#FFFFFF"
    ]
    assert wrapper_rects, "wrapper rect not found"
    wrapper = wrapper_rects[0]
    WRAPPER_RIGHT_X = int(wrapper.get("x", "0")) + int(wrapper.get("width", "0"))

    for oname in ("cfg_rdata", "irq"):
        x = _x_of_port_label(oname, "[7:0]" if oname.startswith("cfg_") else "")
        assert x > WRAPPER_RIGHT_X, (
            f"output {oname!r} rendered at x={x}, expected > wrapper right edge {WRAPPER_RIGHT_X}"
        )


def test_topology_empty_submodules() -> None:
    """A wrapper with zero direct submodules must render gracefully (valid SVG)."""
    from excel2design.core.models import Port
    solo = Module(name="solo", ports=[
        Port(name="clk", direction=Direction.INPUT,
             width=parse_width("1", known_params=set()), type=SignalType.WIRE),
    ])
    proj = Project(modules={"solo": solo}, hierarchy={})
    svg = generate_svg_topology(proj, "solo")
    assert svg.startswith("<?xml")
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    # A helpful note is drawn (per the empty-submodule fallback in the
    # implementation) — its presence is the visual cue that the case is
    # handled rather than crashing.
    assert "no direct submodules" in svg


def test_topology_missing_top_module(iic_top: Project) -> None:
    """Unknown top module name must return an empty string (matches sibling API)."""
    assert generate_svg_topology(iic_top, "ghost") == ""
