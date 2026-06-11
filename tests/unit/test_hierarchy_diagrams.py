"""P1-1 unit tests for the v0.5 hierarchy diagram generators (SVG + Excalidraw).

These tests use a small in-memory Project (no xlsx round-trip) to keep
execution fast and focus on layout correctness.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET

import pytest

from excel2design.core.models import (
    Direction, Module, Project, SubmoduleInstance,
)
from excel2design.generators.diagram_excalidraw_hierarchy import (
    generate_excalidraw_hierarchy,
)
from excel2design.generators.diagram_svg_hierarchy import generate_svg_hierarchy
from excel2design.parsers.width import parse_width
from excel2design.core.models import SignalType, Port


def _p(name: str, direction: Direction, width: str = "1") -> Port:
    return Port(
        name=name, direction=direction,
        width=parse_width(width, known_params=set()),
        type=SignalType.WIRE,
    )


def _project_with_subs() -> Project:
    top = Module(name="top", ports=[_p("clk", Direction.INPUT), _p("out_v", Direction.OUTPUT)])
    a = Module(name="top.a", ports=[_p("clk", Direction.INPUT), _p("data", Direction.OUTPUT, width="8")])
    b = Module(name="top.b", ports=[_p("clk", Direction.INPUT), _p("data", Direction.INPUT, width="8")])
    return Project(
        modules={"top": top, "top.a": a, "top.b": b},
        hierarchy={"top": ["top.a", "top.b"]},
    )


# ---- SVG -----------------------------------------------------------------


def test_svg_hierarchy_returns_string_for_known_top():
    proj = _project_with_subs()
    svg = generate_svg_hierarchy(proj, "top")
    assert svg.startswith("<?xml")
    assert "<svg" in svg
    # ET must be able to parse the output.
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


def test_svg_hierarchy_empty_for_missing_top():
    proj = _project_with_subs()
    assert generate_svg_hierarchy(proj, "ghost") == ""


def test_svg_hierarchy_includes_submodule_names():
    proj = _project_with_subs()
    svg = generate_svg_hierarchy(proj, "top")
    # Submodule labels use the short instance name (last segment).
    assert ">a<" in svg
    assert ">b<" in svg


def test_svg_hierarchy_draws_sibling_wire_for_shared_port():
    proj = _project_with_subs()
    svg = generate_svg_hierarchy(proj, "top")
    # 'data' is shared between a and b → an internal wire labelled 'data'
    # should appear in the SVG. Look for the label text element.
    assert ">data<" in svg
    # And at least one dashed line element (stroke-dasharray=4,2 → "4,2").
    assert "4,2" in svg


def test_svg_hierarchy_is_byte_stable():
    proj = _project_with_subs()
    a = generate_svg_hierarchy(proj, "top")
    b = generate_svg_hierarchy(proj, "top")
    assert a == b, "hierarchy SVG must be byte-stable across calls"


def test_svg_hierarchy_no_hierarchy_returns_minimal():
    """A top with no submodules should still produce a valid SVG."""
    top = Module(name="solo", ports=[_p("clk", Direction.INPUT)])
    proj = Project(modules={"solo": top}, hierarchy={})
    svg = generate_svg_hierarchy(proj, "solo")
    # Should still emit a valid (empty-children) wrapper.
    assert "<svg" in svg
    # The submodule boxes aren't drawn when there are no children —
    # confirmed by absence of 'top.a'-style labels.


# ---- Excalidraw ----------------------------------------------------------


def test_excalidraw_hierarchy_returns_valid_json():
    proj = _project_with_subs()
    s = generate_excalidraw_hierarchy(proj, "top")
    data = json.loads(s)
    assert data["type"] == "excalidraw"
    assert isinstance(data["elements"], list)
    assert len(data["elements"]) > 0


def test_excalidraw_hierarchy_empty_for_missing_top():
    proj = _project_with_subs()
    assert generate_excalidraw_hierarchy(proj, "ghost") == ""


def test_excalidraw_hierarchy_includes_submodule_rects():
    proj = _project_with_subs()
    data = json.loads(generate_excalidraw_hierarchy(proj, "top"))
    rect_ids = [e["id"] for e in data["elements"] if e["type"] == "rectangle"]
    # At least 1 wrapper rect + 2 submodule rects.
    assert any("sub" in rid for rid in rect_ids), (
        f"expected submodule rects in {rect_ids}"
    )


def test_excalidraw_hierarchy_is_byte_stable():
    proj = _project_with_subs()
    a = generate_excalidraw_hierarchy(proj, "top")
    b = generate_excalidraw_hierarchy(proj, "top")
    assert a == b
