"""Tests for parsers/width.py (SPEC §3.5.3)."""

from __future__ import annotations

import pytest

from excel2design.core.exceptions import PortValidationError, UnknownParameterError
from excel2design.parsers.width import PortWidth, parse_width


# ---- empty / blank → 1 bit -------------------------------------------------

def test_empty_string_defaults_to_1() -> None:
    w = parse_width("", set())
    assert w.raw == "1"
    assert w.msb is None
    assert w.is_parameter is False


def test_whitespace_only_defaults_to_1() -> None:
    w = parse_width("   ", set())
    assert w.raw == "1"
    assert w.msb == 0 or w.msb is None  # default 1-bit


def test_none_input_defaults_to_1() -> None:
    w = parse_width(None, set())  # type: ignore[arg-type]
    assert w.raw == "1"


# ---- pure integer ----------------------------------------------------------

def test_pure_integer_8() -> None:
    w = parse_width("8", set())
    assert w.raw == "8"
    assert w.msb == 7
    assert w.is_parameter is False


def test_pure_integer_1() -> None:
    w = parse_width("1", set())
    assert w.msb == 0
    assert w.is_parameter is False


def test_pure_integer_32() -> None:
    w = parse_width("32", set())
    assert w.msb == 31


def test_zero_raises() -> None:
    with pytest.raises(PortValidationError) as exc_info:
        parse_width("0", set(), sheet="s", row=3, col=3)
    assert "> 0" in exc_info.value.message


def test_negative_raises() -> None:
    """Negative numbers are not pure-digit, so they fall to expression/reject path."""
    with pytest.raises((PortValidationError, ValueError)):
        parse_width("-1", set(), sheet="s", row=3, col=3)


# ---- single parameter ------------------------------------------------------

def test_known_parameter() -> None:
    w = parse_width("DATA_WIDTH", {"DATA_WIDTH"})
    assert w.raw == "DATA_WIDTH"
    assert w.msb is None
    assert w.is_parameter is True


def test_unknown_parameter_raises() -> None:
    with pytest.raises(UnknownParameterError) as exc_info:
        parse_width("WIDTH", set(), sheet="s", row=3, col=3)
    assert exc_info.value.param_name == "WIDTH"


def test_unknown_parameter_in_set_raises() -> None:
    with pytest.raises(UnknownParameterError):
        parse_width("ADDR_WIDTH", {"DATA_WIDTH"}, sheet="s", row=3, col=3)


# ---- expressions -----------------------------------------------------------

def test_expression_known_params() -> None:
    w = parse_width("DATA_WIDTH*2", {"DATA_WIDTH"})
    assert w.is_parameter is True
    assert w.raw == "DATA_WIDTH*2"


def test_expression_addition() -> None:
    w = parse_width("ADDR_WIDTH-1", {"ADDR_WIDTH"})
    assert w.is_parameter is True


def test_expression_divide() -> None:
    w = parse_width("DATA_WIDTH/2", {"DATA_WIDTH"})
    assert w.is_parameter is True


def test_expression_with_parens() -> None:
    w = parse_width("(DATA_WIDTH*2)+1", {"DATA_WIDTH"})
    assert w.is_parameter is True


def test_expression_with_unknown_token() -> None:
    with pytest.raises(UnknownParameterError) as exc_info:
        parse_width("MY_WIDTH*2", {"DATA_WIDTH"}, sheet="s", row=3, col=3)
    assert exc_info.value.param_name == "MY_WIDTH"


def test_expression_illegal_chars() -> None:
    """Characters like brackets/quotes are not in the allowed set."""
    with pytest.raises(PortValidationError) as exc_info:
        parse_width("DATA_WIDTH[7:0]", {"DATA_WIDTH"}, sheet="s", row=3, col=3)
    assert "位宽" in exc_info.value.message


# ---- to_verilog ------------------------------------------------------------

def test_to_verilog_fixed_8() -> None:
    w = parse_width("8", set())
    assert w.to_verilog() == "[7:0]"


def test_to_verilog_fixed_1_omits_brackets() -> None:
    w = parse_width("1", set())
    assert w.to_verilog() == ""


def test_to_verilog_parameter() -> None:
    w = parse_width("DATA_WIDTH", {"DATA_WIDTH"})
    assert w.to_verilog() == "[DATA_WIDTH-1:0]"


def test_to_verilog_expression() -> None:
    w = parse_width("DATA_WIDTH*2", {"DATA_WIDTH"})
    assert w.to_verilog() == "[DATA_WIDTH*2-1:0]"


# ---- error location propagation -------------------------------------------

def test_error_attaches_sheet_row_col() -> None:
    with pytest.raises(PortValidationError) as exc_info:
        parse_width("0", set(), sheet="uart_rx", row=42, col=3)
    err = exc_info.value
    assert err.sheet == "uart_rx"
    assert err.row == 42
    assert err.col == 3
