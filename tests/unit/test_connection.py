"""P1-1 unit tests for core/connection.py (v0.5 instance connection algorithm).

Covers:
  - match_port priority 1a: parent port (exact match)
  - match_port priority 1b: parent port (fuzzy suffix match)
  - match_port priority 2: sibling port
  - match_port priority 3: parent parameter
  - match_port fallback: UNCONNECTED
  - _check_width: same width / different width
  - _fuzzy_match: instance suffix rules
"""

from __future__ import annotations

import pytest

from excel2design.core.connection import (
    ConnectionKind, _check_width, _fuzzy_match, match_port,
)
from excel2design.core.models import (
    Direction, Module, Parameter, Port,
)
from excel2design.parsers.width import parse_width


# ---- Test helpers ---------------------------------------------------------


def _p(name: str, direction: Direction, width: str = "1",
        clock: str | None = None, is_reg: bool = False) -> Port:
    return Port(
        name=name,
        direction=direction,
        width=parse_width(width, known_params=set()),
        type=__import__("excel2design.core.models", fromlist=["SignalType"]).SignalType.REG
              if is_reg else __import__("excel2design.core.models", fromlist=["SignalType"]).SignalType.WIRE,
        clock=clock,
    )


# ---- match_port priorities ------------------------------------------------


def test_match_port_priority_1a_parent_exact():
    parent = Module(name="top", ports=[_p("clk", Direction.INPUT)])
    port = _p("clk", Direction.INPUT)
    r = match_port(port, parent, sibling_modules=[], instance_name="u_a")
    assert r.kind == ConnectionKind.PARENT_PORT
    assert r.target_name == "clk"


def test_match_port_priority_1b_parent_fuzzy_suffix():
    parent = Module(name="top", ports=[_p("data_a", Direction.INPUT)])
    # child port is "data" (no suffix); instance is "u_a"
    port = _p("data", Direction.INPUT)
    r = match_port(port, parent, sibling_modules=[], instance_name="u_a")
    assert r.kind == ConnectionKind.PARENT_PORT
    assert r.target_name == "data_a"


def test_match_port_priority_2_sibling_exact():
    parent = Module(name="top", ports=[_p("clk", Direction.INPUT)])
    sibling = Module(name="sib", ports=[_p("data", Direction.OUTPUT)])
    port = _p("data", Direction.INPUT)
    r = match_port(port, parent, sibling_modules=[sibling], instance_name="u_a")
    assert r.kind == ConnectionKind.SIBLING_PORT
    assert r.target_name == "data"


def test_match_port_priority_3_parent_param():
    parent = Module(
        name="top",
        ports=[_p("clk", Direction.INPUT)],
        parameters=[Parameter(name="WIDTH", value="8")],
    )
    port = _p("WIDTH", Direction.INPUT)
    r = match_port(port, parent, sibling_modules=[], instance_name="")
    assert r.kind == ConnectionKind.PARENT_PARAM
    assert r.target_name == "WIDTH"


def test_match_port_unconnected():
    parent = Module(name="top", ports=[_p("clk", Direction.INPUT)])
    port = _p("orphan", Direction.INPUT)
    r = match_port(port, parent, sibling_modules=[], instance_name="u_a")
    assert r.kind == ConnectionKind.UNCONNECTED


# ---- Width check ----------------------------------------------------------


def test_check_width_match_returns_true():
    a = _p("x", Direction.INPUT, width="8")
    b = _p("y", Direction.INPUT, width="8")
    match, note = _check_width(a, b)
    assert match is True
    assert note == ""


def test_check_width_mismatch_returns_false_with_note():
    a = _p("x", Direction.INPUT, width="8")
    b = _p("y", Direction.INPUT, width="16")
    match, note = _check_width(a, b)
    assert match is False
    # The note shows the Verilog-formatted widths.
    assert "[7:0]" in note and "[15:0]" in note


# ---- Fuzzy match ----------------------------------------------------------


def test_fuzzy_match_exact_returns_true():
    assert _fuzzy_match("data", "data") is True


def test_fuzzy_match_strips_a_suffix_when_instance_has_a():
    # parent: "data_a", child: "data", instance: "u_a" → match
    assert _fuzzy_match("data_a", "data", "u_a") is True


def test_fuzzy_match_strips_b_suffix_when_instance_has_b():
    assert _fuzzy_match("data_b", "data", "u_b") is True


def test_fuzzy_match_no_instance_tries_all_suffixes():
    # Without instance name, all common suffixes should be tried.
    assert _fuzzy_match("data_a", "data", "") is True
    assert _fuzzy_match("data_b", "data", "") is True
    assert _fuzzy_match("data_0", "data", "") is True


def test_fuzzy_match_different_base_returns_false():
    assert _fuzzy_match("totally_different", "data", "u_a") is False
