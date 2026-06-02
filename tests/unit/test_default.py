"""Tests for parsers/default.py (SPEC §3.5.5)."""

from __future__ import annotations

import pytest

from excel2design.parsers.default import DefaultValueError, parse_default


@pytest.mark.parametrize("raw", [None, "", "   ", "\t"])
def test_blank_returns_none(raw) -> None:
    assert parse_default(raw) is None


def test_zero_becomes_1b0() -> None:
    assert parse_default("0") == "1'b0"


def test_one_becomes_1b1() -> None:
    assert parse_default("1") == "1'b1"


def test_binary_literal_passthrough() -> None:
    assert parse_default("8'b0000_0001") == "8'b0000_0001"


def test_hex_literal_passthrough() -> None:
    assert parse_default("8'hFF") == "8'hFF"


def test_octal_literal_passthrough() -> None:
    assert parse_default("8'o17") == "8'o17"


def test_replication_passthrough() -> None:
    assert parse_default("{DATA_WIDTH{1'b0}}") == "{DATA_WIDTH{1'b0}}"


def test_function_call_passthrough() -> None:
    assert parse_default("my_func(x)") == "my_func(x)"


def test_identifier_passthrough() -> None:
    """State-machine enums like IDLE/STREAM are common."""
    assert parse_default("IDLE") == "IDLE"


def test_expression_passthrough() -> None:
    assert parse_default("A + B") == "A + B"


def test_invalid_literal_raises() -> None:
    with pytest.raises(DefaultValueError):
        parse_default("8'bQQ")


def test_chinese_in_replication_raises() -> None:
    with pytest.raises(DefaultValueError):
        parse_default("{数据{1'b0}}")


def test_special_char_raises() -> None:
    with pytest.raises(DefaultValueError):
        parse_default("a;b")
