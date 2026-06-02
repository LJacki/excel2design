"""Exception hierarchy for excel2design.

Three-layer classification (per SPEC §3.4):
  ExcelParseError  — physical layer: cell types, missing columns, markers, merged cells
  SemanticError    — logical layer: duplicate ports, illegal identifiers, unresolved params
  RenderError      — generation layer: template failures, out-of-bounds coordinates

Every exception carries (sheet, row, col, suggestion) where applicable so the CLI
can render a precise error message.
"""

from __future__ import annotations

from typing import Optional


class ExcelParseError(Exception):
    """Base for all parsing/validation errors. Carries precise location info."""

    def __init__(
        self,
        message: str,
        sheet: Optional[str] = None,
        row: Optional[int] = None,
        col: Optional[int] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.sheet = sheet
        self.row = row  # 1-based
        self.col = col  # 1-based (A=1)
        self.suggestion = suggestion

    def __str__(self) -> str:
        loc_parts = []
        if self.sheet is not None:
            loc_parts.append(f"sheet: {self.sheet}")
        if self.row is not None:
            loc_parts.append(f"row {self.row}")
        if self.col is not None:
            loc_parts.append(f"col {self.col}")
        loc = ", ".join(loc_parts)
        prefix = f"[{loc}] " if loc else ""
        msg = f"{prefix}{self.message}"
        if self.suggestion:
            msg += f"\n       ↳ 建议: {self.suggestion}"
        return msg


# ---- Physical layer (Excel format) ----------------------------------------

class MarkerMissingError(ExcelParseError):
    """Required section marker not found."""

    def __init__(self, sheet: str, marker_name: str) -> None:
        super().__init__(
            f"必需的 marker 缺失: '{marker_name}'",
            sheet=sheet,
            suggestion=f"在 sheet 中添加一行: # === {marker_name} ===",
        )
        self.marker_name = marker_name


class HeaderMismatchError(ExcelParseError):
    """Table header columns don't match the expected schema."""

    def __init__(self, sheet: str, row: int, expected: list[str], got: list[str]) -> None:
        super().__init__(
            f"表头列不匹配，期望 {expected}，实际 {got}",
            sheet=sheet,
            row=row,
            suggestion="对照 docs/SPEC.md §2.4/2.5 的列定义修正表头",
        )
        self.expected = expected
        self.got = got


class MergedCellError(ExcelParseError):
    """Detected merged cells in a region we don't support."""

    def __init__(self, sheet: str, cell_range: str) -> None:
        super().__init__(
            f"检测到合并单元格: {cell_range}",
            sheet=sheet,
            suggestion="取消合并（v0.3 不支持合并单元格）",
        )
        self.cell_range = cell_range


class FormulaCellError(ExcelParseError):
    """A cell contains an Excel formula."""

    def __init__(self, sheet: str, row: int, col: int) -> None:
        super().__init__(
            "单元格包含公式",
            sheet=sheet, row=row, col=col,
            suggestion="v0.3 不支持公式，请改用纯值或 parameter 名",
        )


class UnsupportedCellTypeError(ExcelParseError):
    """A cell's value type is not in the whitelist (str/int/float/bool/None)."""

    def __init__(self, sheet: str, row: int, col: int, type_name: str) -> None:
        super().__init__(
            f"不支持的单元格类型: {type_name}",
            sheet=sheet, row=row, col=col,
            suggestion="请将单元格改为文本或数字",
        )
        self.type_name = type_name


# ---- Semantic layer (logical validation) ----------------------------------

class SemanticError(ExcelParseError):
    """Logical/structural errors after the Excel is read successfully."""


class PortValidationError(SemanticError):
    """Port-level validation failed (bad direction, width, etc)."""


class IdentifierError(SemanticError):
    """Name is not a valid Verilog identifier (regex fail or reserved word)."""

    def __init__(self, sheet: str, row: int, col: int, name: str,
                 suggestion: Optional[str] = None) -> None:
        if suggestion is None:
            suggestion = "identifier 必须以字母/下划线开头，后接字母/数字/下划线，且不能是 Verilog 保留字"
        super().__init__(
            f"非法 identifier: '{name}'",
            sheet=sheet, row=row, col=col,
            suggestion=suggestion,
        )
        self.name = name


class UnknownParameterError(SemanticError):
    """Port width expression references a parameter that isn't declared in this module."""

    def __init__(self, sheet: str, port_row: int, param_name: str) -> None:
        super().__init__(
            f"位宽引用了未声明的 parameter: '{param_name}'",
            sheet=sheet, row=port_row,
            suggestion="在 '# === PARAMETERS ===' 段先声明该 parameter",
        )
        self.param_name = param_name


class DuplicatePortError(SemanticError):
    """Two or more ports share the same name within one module."""

    def __init__(self, sheet: str, name: str, rows: list[int]) -> None:
        super().__init__(
            f"端口名重复: '{name}' (出现于第 {', '.join(map(str, rows))} 行)",
            sheet=sheet, suggestion="同一模块内端口名必须唯一",
        )
        self.name = name
        self.rows = rows


# ---- Module-level (not row-level) -----------------------------------------

class ModuleNotFoundError(ExcelParseError):
    """Requested sheet/module does not exist in the workbook."""

    def __init__(self, name: str, available: list[str]) -> None:
        super().__init__(
            f"模块 '{name}' 不存在",
            suggestion=f"可用的模块: {', '.join(available) if available else '(无)'}",
        )
        self.name = name
        self.available = available


# ---- Generation layer (output side) ---------------------------------------

class RenderError(Exception):
    """Template/structure generation failed. Not derived from ExcelParseError
    because there is no Excel location to attach."""
