"""Tests for utils/identifier.py (SPEC §3.5.2)."""

from __future__ import annotations

import pytest

from excel2design.core.exceptions import IdentifierError
from excel2design.utils.identifier import (
    VERILOG_KEYWORDS,
    check_identifier,
    is_valid_identifier,
)


# ---- is_valid_identifier (no-exception path) ------------------------------

@pytest.mark.parametrize("name", ["clk", "rst_n", "_x", "axi_awaddr", "Data0", "_", "a__b"])
def test_valid_identifiers(name: str) -> None:
    assert is_valid_identifier(name)


@pytest.mark.parametrize("name", ["", "1abc", "9x", "a-b", "a b", "a.b", "a$b", "rst_n[0]"])
def test_invalid_format(name: str) -> None:
    assert not is_valid_identifier(name)


@pytest.mark.parametrize("name", ["reg", "wire", "input", "output", "module", "always", "logic"])
def test_reserved_words_rejected(name: str) -> None:
    assert not is_valid_identifier(name)
    assert name in VERILOG_KEYWORDS


# ---- check_identifier (raises with location) -------------------------------

def test_check_passes_for_valid() -> None:
    check_identifier("clk", "port", sheet="uart_rx", row=8, col=1)


def test_check_raises_for_empty() -> None:
    with pytest.raises(IdentifierError) as exc_info:
        check_identifier("", "port", sheet="uart_rx", row=8, col=1)
    assert "不能为空" in str(exc_info.value)
    assert exc_info.value.sheet == "uart_rx"
    assert exc_info.value.row == 8
    assert exc_info.value.col == 1


def test_check_raises_for_bad_format() -> None:
    with pytest.raises(IdentifierError) as exc_info:
        check_identifier("1bad", "port", sheet="axi", row=3, col=1)
    assert "1bad" in str(exc_info.value)
    assert "字母" in str(exc_info.value)  # suggestion present


def test_check_raises_for_reserved_word() -> None:
    with pytest.raises(IdentifierError) as exc_info:
        check_identifier("reg", "port", sheet="axi", row=3, col=1)
    assert "保留字" in str(exc_info.value)


def test_check_attaches_location() -> None:
    """Error location must propagate to (sheet, row, col)."""
    with pytest.raises(IdentifierError) as exc_info:
        check_identifier("wire", "port", sheet="uart_rx", row=42, col=3)
    err = exc_info.value
    assert err.sheet == "uart_rx"
    assert err.row == 42
    assert err.col == 3
    assert err.name == "wire"


def test_check_default_sheet_name() -> None:
    """When no sheet given, the error should still be readable."""
    with pytest.raises(IdentifierError) as exc_info:
        check_identifier("reg", "module")
    assert exc_info.value.sheet is not None  # fallback
