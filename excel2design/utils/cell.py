"""Cell value coercion per SPEC §3.5.1.

Whitelist: str / int / float / bool / None
Anything else (datetime, formula, custom types) is an error.

Special handling:
  - bool: True/False → "1"/"0"  (Excel 0/1 sometimes auto-converts to bool)
  - int: passed through as decimal string
  - float: passed through; we'll accept it for width columns and downstream
           validation will reject non-integer widths.
  - str: stripped
  - None: ""  (indistinguishable from genuinely empty cell)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from excel2design.core.exceptions import (
    FormulaCellError,
    UnsupportedCellTypeError,
)

if TYPE_CHECKING:
    from openpyxl.cell.cell import Cell


def cell_to_str(cell: "Cell") -> str:
    """Coerce an openpyxl Cell to a normalized string.

    Raises:
        FormulaCellError: if the cell contains a formula.
        UnsupportedCellTypeError: if the value type is not in the whitelist.
    """
    # Detect formula cells BEFORE reading .value
    # openpyxl exposes data_type: 'n' (number), 's' (string), 'b' (bool),
    # 'd' (date), 'f' (formula), 'e' (error), None (empty)
    if cell.data_type == "f":
        raise FormulaCellError(
            sheet=cell.parent.title if cell.parent is not None else "<unknown>",
            row=cell.row,
            col=cell.column,
        )

    v = cell.value
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        # Width columns often contain 8.0; convert to int-like string when whole
        if v.is_integer():
            return str(int(v))
        return str(v)
    if isinstance(v, str):
        return v.strip()
    # Anything else (datetime, custom objects) is an error
    raise UnsupportedCellTypeError(
        sheet=cell.parent.title if cell.parent is not None else "<unknown>",
        row=cell.row,
        col=cell.column,
        type_name=type(v).__name__,
    )


def is_blank(cell: "Cell") -> bool:
    """Return True if the cell is effectively empty (no value, formula, or whitespace-only)."""
    if cell.data_type == "f":
        return False  # A formula is never "blank"
    v = cell.value
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == ""
    return False
