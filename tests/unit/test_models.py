"""Tests for core/models.py (SPEC §3)."""

from __future__ import annotations

import pytest

from excel2design.core.exceptions import PortValidationError
from excel2design.core.models import (
    Direction,
    Module,
    Parameter,
    ParamType,
    Port,
    ResetType,
    SignalType,
)
from excel2design.parsers.width import PortWidth


def make_port(
    name: str = "clk",
    direction: Direction = Direction.INPUT,
    type: SignalType = SignalType.WIRE,
    reset_type: ResetType = ResetType.SYNC,
    clock: str | None = None,
    default: str | None = None,
    signed: bool = False,
) -> Port:
    return Port(
        name=name,
        direction=direction,
        width=PortWidth(raw="1", msb=0, is_parameter=False),
        type=type,
        default=default,
        clock=clock,
        reset_type=reset_type,
        signed=signed,
    )


# ---- Direction parsing ----------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("input", Direction.INPUT),
    ("output", Direction.OUTPUT),
    ("inout", Direction.INOUT),
    ("INPUT", Direction.INPUT),
    (" Output ", Direction.OUTPUT),
])
def test_direction_parse_valid(raw: str, expected: Direction) -> None:
    assert Direction.parse(raw) == expected


@pytest.mark.parametrize("raw", ["", "io", "bidir", "in_out", None])
def test_direction_parse_invalid(raw) -> None:
    with pytest.raises(PortValidationError):
        Direction.parse(raw)  # type: ignore[arg-type]


# ---- SignalType default inference -----------------------------------------

def test_signal_type_output_defaults_to_reg() -> None:
    t = SignalType.parse("", Direction.OUTPUT)
    assert t == SignalType.REG


def test_signal_type_input_defaults_to_wire() -> None:
    t = SignalType.parse("", Direction.INPUT)
    assert t == SignalType.WIRE


def test_signal_type_inout_defaults_to_wire() -> None:
    t = SignalType.parse("", Direction.INOUT)
    assert t == SignalType.WIRE


def test_signal_type_explicit() -> None:
    assert SignalType.parse("logic", Direction.INPUT) == SignalType.LOGIC
    assert SignalType.parse("WIRE", Direction.OUTPUT) == SignalType.WIRE


def test_signal_type_invalid() -> None:
    with pytest.raises(PortValidationError):
        SignalType.parse("register", Direction.INPUT)


# ---- ResetType default + parse --------------------------------------------

def test_reset_type_default_is_sync() -> None:
    assert ResetType.parse("") == ResetType.SYNC


def test_reset_type_case_insensitive() -> None:
    assert ResetType.parse("ASYNC") == ResetType.ASYNC


def test_reset_type_invalid() -> None:
    with pytest.raises(PortValidationError):
        ResetType.parse("level")


# ---- Module classification helpers ---------------------------------------

def test_module_inputs_outputs() -> None:
    m = Module(name="m", ports=[
        make_port("clk", Direction.INPUT),
        make_port("rst_n", Direction.INPUT),
        make_port("data", Direction.OUTPUT, SignalType.REG),
    ])
    assert len(m.inputs()) == 2
    assert len(m.outputs()) == 1
    assert len(m.inouts()) == 0


def test_module_regs_and_wires() -> None:
    m = Module(name="m", ports=[
        make_port("clk", Direction.INPUT, SignalType.WIRE),
        make_port("data", Direction.OUTPUT, SignalType.REG),
        make_port("flag", Direction.OUTPUT, SignalType.LOGIC),
    ])
    assert len(m.regs()) == 2
    assert len(m.wires()) == 1


def test_module_async_sync_none_regs() -> None:
    m = Module(name="m", ports=[
        make_port("a", Direction.OUTPUT, SignalType.REG, ResetType.ASYNC),
        make_port("b", Direction.OUTPUT, SignalType.REG, ResetType.SYNC),
        make_port("c", Direction.OUTPUT, SignalType.REG, ResetType.NONE),
        make_port("d", Direction.OUTPUT, SignalType.LOGIC, ResetType.ASYNC),
    ])
    assert len(m.async_regs()) == 2
    assert len(m.sync_regs()) == 1
    assert len(m.no_reset_regs()) == 1


def test_module_primary_clock_most_common() -> None:
    m = Module(name="m", ports=[
        make_port("a", clock="clk"),
        make_port("b", clock="clk2"),
        make_port("c", clock="clk"),
        make_port("d", clock="clk"),
    ])
    assert m.primary_clock() == "clk"


def test_module_primary_clock_tie_returns_first() -> None:
    """When clocks tie, the first in Excel order wins."""
    m = Module(name="m", ports=[
        make_port("a", clock="clk_a"),
        make_port("b", clock="clk_b"),
    ])
    assert m.primary_clock() == "clk_a"


def test_module_primary_clock_no_clocks() -> None:
    m = Module(name="m", ports=[make_port("a")])
    assert m.primary_clock() is None


def test_module_parameter_names() -> None:
    m = Module(name="m", parameters=[
        Parameter(name="WIDTH", value="8"),
        Parameter(name="DEPTH", value="16"),
    ])
    assert m.parameter_names() == {"WIDTH", "DEPTH"}


# ---- Port dataclass smoke ------------------------------------------------

def test_port_signed_flag() -> None:
    p = make_port(signed=True)
    assert p.signed is True


def test_port_ordering_preserved() -> None:
    """Module.ports should preserve Excel insertion order."""
    m = Module(name="m", ports=[
        make_port("a"),
        make_port("b"),
        make_port("c"),
    ])
    assert [p.name for p in m.ports] == ["a", "b", "c"]
# ---- v0.6 Phase 12.1: Port.array_dim field & helpers ----------------------

def test_port_array_dim_default_none() -> None:
    """A port constructed without array_dim must default to None (backward-compat)."""
    p = make_port("scalar_port")
    assert p.array_dim is None
    assert p.total_array_elements == 1
    assert p.to_array_dim_verilog() == ""


def test_port_total_array_elements_1d() -> None:
    """[(7, 0)] → 8 elements total."""
    p = make_port("array_port")
    p.array_dim = [(7, 0)]
    assert p.total_array_elements == 8
    assert p.to_array_dim_verilog() == "[7:0]"


def test_port_total_array_elements_2d() -> None:
    """[(3, 0), (1, 0)] → 4 × 2 = 8 elements total."""
    p = make_port("port_array_2d")
    p.array_dim = [(3, 0), (1, 0)]
    assert p.total_array_elements == 8
    assert p.to_array_dim_verilog() == "[3:0][1:0]"


def test_port_total_array_elements_empty_list() -> None:
    """Empty list is treated as scalar (total = 1)."""
    p = make_port("scalar_port")
    p.array_dim = []
    assert p.total_array_elements == 1
    assert p.to_array_dim_verilog() == ""


def test_port_total_array_elements_single_dim_equal() -> None:
    """hi == lo → exactly 1 element in that dim."""
    p = make_port("array_port")
    p.array_dim = [(3, 3), (7, 0)]
    assert p.total_array_elements == 8


def test_port_to_array_dim_verilog_no_leading_space_when_none() -> None:
    """to_array_dim_verilog returns '' (no leading space) for scalar ports."""
    p = make_port("array_port")
    assert p.to_array_dim_verilog() == ""
