"""Default value literal handling per SPEC §3.5.5.

Rules (input → output):
  - empty           → None
  - "0"             → "1'b0"
  - "1"             → "1'b1"
  - "8'hFF"         → "8'hFF"  (has apostrophe — pass through)
  - "{W{1'b0}}"     → "{W{1'b0}}"  (replication — pass through)
  - "my_func(x)"    → "my_func(x)"  (parens, no apostrophe — pass through)

Anything with Chinese or other special characters → ValueError.
"""

from __future__ import annotations

import re

_HEX_RE = re.compile(r"^[0-9A-Fa-f]+$")


class DefaultValueError(ValueError):
    """Raised when a default-value cell is not parseable."""


def parse_default(raw: str | None) -> str | None:
    """Normalize a default value cell to its Verilog form.

    Returns None if the cell is empty.
    Raises DefaultValueError if the value is structurally invalid.
    """
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None

    # Pure integer 0/1 → width-1 bit literal
    if s == "0":
        return "1'b0"
    if s == "1":
        return "1'b1"

    # Replication {W{...}} — check BEFORE literal because replications may
    # contain an apostrophe inside (e.g. "{N{1'b0}}").
    if s.startswith("{"):
        return _validate_replication(s)

    # Verilog literal (has apostrophe) — pass through after character validation
    if "'" in s:
        return _validate_literal(s)

    # Function-call style expr(x) — pass through (no apostrophe, has parens)
    if "(" in s and ")" in s:
        return _validate_identifier_expression(s)

    # Otherwise: must be a plain identifier or simple expression (e.g. "IDLE", "DATA_WIDTH")
    return _validate_identifier_expression(s)


def _validate_literal(s: str) -> str:
    """Verify a Verilog literal like '8'hFF' or '1'b0' or '8'b0000_0001'."""
    if not re.fullmatch(r"[0-9A-Za-z_]+'[bdhoBDHO][0-9A-Fa-f_xXzZ?]+", s):
        raise DefaultValueError(f"default 值 '{s}' 不是合法的 Verilog 字面量")
    return s


def _validate_replication(s: str) -> str:
    """Verify a replication like '{N{1'b0}}' or '{2{DATA_WIDTH}}'."""
    if not s.endswith("}"):
        raise DefaultValueError(f"default 值 '{s}' 看起来像 replication 但缺 '}}'")
    # Reject control chars / Chinese
    if re.search(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]", s):
        raise DefaultValueError(f"default 值 '{s}' 含中文字符")
    return s


def _validate_identifier_expression(s: str) -> str:
    """Verify an identifier or simple expression containing only [A-Za-z0-9_+\-*/()\s]."""
    if not re.fullmatch(r"[A-Za-z0-9_+\-*/()\s]+", s):
        raise DefaultValueError(
            f"default 值 '{s}' 含非法字符（只允许字母/数字/下划线/算符/括号）"
        )
    return s
