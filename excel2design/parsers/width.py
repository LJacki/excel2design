"""Port width parsing per SPEC §3.5.3.

Three outcomes:
  - empty / blank  → default 1-bit (PortWidth{raw='1', msb=None, is_parameter=False})
  - pure integer   → fixed width, msb = n-1
  - parameter name or expression → must reference declared params
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from excel2design.core.exceptions import PortValidationError, UnknownParameterError


# A parameter reference is an identifier.
_PARAM_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Allowed expression characters: identifiers, digits, + - * / ( ) whitespace.
_EXPR_RE = re.compile(r"^[A-Za-z_0-9+\-*/()\s]+$")


@dataclass(frozen=True)
class PortWidth:
    """Parsed port width."""
    raw: str                       # Original string, kept verbatim for output
    msb: Optional[int]             # MSB index for fixed widths; None for parameterised
    is_parameter: bool             # True if width depends on a parameter

    def to_verilog(self) -> str:
        """Return the Verilog bit-index expression, e.g. '[7:0]' or '[DATA_WIDTH-1:0]'.

        For width=1 (msb=0 OR msb=None with default 1-bit), returns '' (no bit-index).
        """
        if not self.is_parameter and (self.msb == 0 or self.msb is None):
            return ""
        if self.is_parameter:
            return f"[{self.raw}-1:0]"
        # fixed
        return f"[{self.msb}:0]"


def parse_width(
    raw: str | None,
    known_params: set[str],
    sheet: str = "<unknown>",
    row: int = 0,
    col: int = 0,
) -> PortWidth:
    """Parse a width cell value.

    Raises:
        PortValidationError: width is non-empty but neither integer nor a
                             recognised expression.
        UnknownParameterError: width expression references a parameter that
                               isn't declared in `known_params`.
    """
    s = (raw or "").strip()
    if not s:
        return PortWidth(raw="1", msb=None, is_parameter=False)

    # Pure integer (positive, decimal)
    if s.isdigit():
        n = int(s)
        if n <= 0:
            raise PortValidationError(
                f"位宽必须 > 0，得到 {n}",
                sheet=sheet, row=row, col=col,
                suggestion="位宽列请填正整数或 parameter 名",
            )
        return PortWidth(raw=s, msb=n - 1, is_parameter=False)

    # Single identifier
    if _PARAM_RE.fullmatch(s):
        if s in known_params:
            return PortWidth(raw=s, msb=None, is_parameter=True)
        raise UnknownParameterError(sheet, row, s)

    # Expression like "DATA_WIDTH*2" or "ADDR_WIDTH-1"
    # Must contain at least one identifier or operator (not just "-1" which is a literal).
    if _EXPR_RE.match(s) and not s.lstrip("-+").isdigit():
        tokens = set(_PARAM_RE.findall(s))
        unknown = {t for t in tokens if not t.isdigit() and t not in known_params}
        if not unknown:
            return PortWidth(raw=s, msb=None, is_parameter=True)
        # Report the first unknown token
        raise UnknownParameterError(sheet, row, sorted(unknown)[0])

    # Reject anything with illegal characters or empty token
    raise PortValidationError(
        f"位宽 '{s}' 既不是纯数字也不引用已知 parameter",
        sheet=sheet, row=row, col=col,
        suggestion="位宽列请填整数（如 8）或 parameter 名/表达式（如 DATA_WIDTH、DATA_WIDTH*2）",
    )
