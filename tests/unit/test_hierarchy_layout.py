"""P1-5 unit tests for generators/hierarchy_layout.py.

This module is the shared layout engine for the v0.5 hierarchy diagram
generators (SVG + Excalidraw). The existing renderers keep their own
internal layout code to preserve byte-stable golden outputs, but new
renderers can use ``compute_hierarchy_layout`` directly. These tests
verify the shared module's outputs are geometrically correct.
"""

from __future__ import annotations

import pytest

from excel2design.core.models import (
    Direction, Module, Project, SignalType,
)
from excel2design.generators.hierarchy_layout import (
    HierarchyLayout, SubLayout, Wire, compute_hierarchy_layout,
)
from excel2design.parsers.width import parse_width


def _p(name: str, direction: Direction, width: str = "1") -> object:
    from excel2design.core.models import Port
    return Port(
        name=name, direction=direction,
        width=parse_width(width, known_params=set()),
        type=SignalType.WIRE,
    )


def _project_with_subs() -> Project:
    top = Module(name="top", ports=[
        _p("clk", Direction.INPUT),
        _p("out_v", Direction.OUTPUT),
    ])
    a = Module(name="top.a", ports=[
        _p("clk", Direction.INPUT),
        _p("shared", Direction.OUTPUT, width="8"),
    ])
    b = Module(name="top.b", ports=[
        _p("clk", Direction.INPUT),
        _p("shared", Direction.INPUT, width="8"),
    ])
    return Project(
        modules={"top": top, "top.a": a, "top.b": b},
        hierarchy={"top": ["top.a", "top.b"]},
    )


def test_compute_layout_returns_none_for_missing_top():
    proj = _project_with_subs()
    assert compute_hierarchy_layout(proj, "ghost") is None


def test_compute_layout_returns_hierarchy_layout_for_known_top():
    proj = _project_with_subs()
    layout = compute_hierarchy_layout(proj, "top")
    assert isinstance(layout, HierarchyLayout)
    assert layout.top_name == "top"
    assert layout.canvas_w > 0
    assert layout.canvas_h > 0


def test_compute_layout_has_one_sublayout_per_submodule():
    proj = _project_with_subs()
    layout = compute_hierarchy_layout(proj, "top")
    names = [s.instance_name for s in layout.sub_layouts]
    assert names == ["a", "b"]
    for sl in layout.sub_layouts:
        assert isinstance(sl, SubLayout)
        assert sl.box_w > 0 and sl.box_h > 0


def test_compute_layout_top_inputs_outputs_recorded():
    proj = _project_with_subs()
    layout = compute_hierarchy_layout(proj, "top")
    # Top has 1 input (clk) and 1 output (out_v).
    assert len(layout.top_inputs) == 1
    assert layout.top_inputs[0][0] == "clk"
    assert len(layout.top_outputs) == 1
    assert layout.top_outputs[0][0] == "out_v"


def test_compute_layout_wires_have_outputs_first():
    """P1-5: wires sort outputs first so renderers can iterate endpoints
    and draw one segment per pair without re-implementing the sort."""
    proj = _project_with_subs()
    layout = compute_hierarchy_layout(proj, "top")
    # 'shared' is shared between a (output) and b (input).
    assert len(layout.wires) == 1
    w = layout.wires[0]
    assert isinstance(w, Wire)
    assert w.name == "shared"
    # First endpoint is from a (output), second from b (input).
    assert w.endpoints[0][2] == "output"
    assert w.endpoints[1][2] == "input"


def test_compute_layout_no_subs_returns_empty_sublayouts():
    """A top with no submodules produces an empty sub_layouts list."""
    top = Module(name="solo", ports=[_p("clk", Direction.INPUT)])
    proj = Project(modules={"solo": top}, hierarchy={})
    layout = compute_hierarchy_layout(proj, "solo")
    assert layout.sub_layouts == []
    assert layout.wires == []
    # canvas is still valid
    assert layout.canvas_w > 0


def test_compute_layout_skip_parent_port_names():
    """If a sub port name matches a parent port, no wire is generated."""
    top = Module(name="top", ports=[_p("clk", Direction.INPUT)])
    a = Module(name="top.a", ports=[_p("clk", Direction.INPUT), _p("clk", Direction.OUTPUT)])
    b = Module(name="top.b", ports=[_p("clk", Direction.INPUT), _p("clk", Direction.INPUT)])
    proj = Project(
        modules={"top": top, "top.a": a, "top.b": b},
        hierarchy={"top": ["top.a", "top.b"]},
    )
    layout = compute_hierarchy_layout(proj, "top")
    # 'clk' is a parent port → no internal wire.
    assert layout.wires == []


def test_compute_layout_is_deterministic():
    """Two calls with the same project must produce the same layout."""
    proj = _project_with_subs()
    a = compute_hierarchy_layout(proj, "top")
    b = compute_hierarchy_layout(proj, "top")
    assert a.canvas_w == b.canvas_w
    assert a.canvas_h == b.canvas_h
    assert a.wrapper_w == b.wrapper_w
    assert a.wrapper_h == b.wrapper_h
    assert len(a.sub_layouts) == len(b.sub_layouts)
    for sa, sb in zip(a.sub_layouts, b.sub_layouts):
        assert (sa.box_x, sa.box_y, sa.box_w, sa.box_h) == (
            sb.box_x, sb.box_y, sb.box_w, sb.box_h
        )
    assert len(a.wires) == len(b.wires)
    for wa, wb in zip(a.wires, b.wires):
        assert wa.name == wb.name
        assert wa.endpoints == wb.endpoints
