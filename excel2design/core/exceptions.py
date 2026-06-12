"""Exception hierarchy per SPEC §3.4 (v0.5).

Three layers: ExcelParseError (physical), SemanticError (logical), RenderError (generation).
v0.5 adds: HierarchyError family (OrphanChildError, RecursiveHierarchyError, EmptyHierarchyError).
"""

from __future__ import annotations

from typing import Optional


# ---- Physical / parse layer -------------------------------------------------

class ExcelParseError(Exception):
    """Physical parse failure — malformed Excel, missing markers, bad cells."""

    def __init__(
        self,
        message: str,
        *,
        sheet: Optional[str] = None,
        row: Optional[int] = None,
        col: Optional[int] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.sheet = sheet
        self.row = row
        self.col = col
        self.suggestion = suggestion


class MarkerMissingError(ExcelParseError):
    def __init__(self, sheet: str, marker_name: str) -> None:
        super().__init__(
            f"缺少标记行 '{marker_name}'",
            sheet=sheet,
            suggestion=f"请确保 sheet '{sheet}' 中有 '{marker_name}' 这一行",
        )
        self.marker_name = marker_name


class HeaderMismatchError(ExcelParseError):
    def __init__(self, sheet: str, row: int, expected: list[str], got: list[str]) -> None:
        super().__init__(
            f"表头不匹配: 期望 {expected}, 实际 {got}",
            sheet=sheet,
            row=row,
            suggestion="请检查表头列名是否正确",
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
    def __init__(self, sheet: str, row: int, col: int) -> None:
        super().__init__(
            f"检测到 Excel 公式",
            sheet=sheet,
            row=row,
            col=col,
            suggestion="请将公式替换为纯文本或数值",
        )


class UnsupportedCellTypeError(ExcelParseError):
    def __init__(self, sheet: str, row: int, col: int, type_name: str) -> None:
        super().__init__(
            f"不支持的单元格类型: {type_name}",
            sheet=sheet,
            row=row,
            col=col,
            suggestion="只支持 str / int / float / bool / None 类型",
        )
        self.type_name = type_name


# ---- Logical / semantic layer -----------------------------------------------

class SemanticError(Exception):
    """Logical error — bad data that passed physical parsing."""


class PortValidationError(SemanticError):
    def __init__(
        self,
        message: str,
        *,
        sheet: Optional[str] = None,
        row: Optional[int] = None,
        col: Optional[int] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        self.sheet = sheet
        self.row = row
        self.col = col
        self.suggestion = suggestion
        # Build a human-readable prefix
        loc = ""
        if sheet:
            loc += f"[sheet: {sheet}"
            if row:
                loc += f", row {row}"
                if col:
                    loc += f", col {col}"
            loc += "] "
        super().__init__(f"{loc}{message}")
        self.message = message


class IdentifierError(SemanticError):
    def __init__(
        self,
        sheet: str,
        row: int,
        col: int,
        name: str,
        suggestion: str,
    ) -> None:
        super().__init__(f"非法的 identifier '{name}': {suggestion}")
        self.sheet = sheet
        self.row = row
        self.col = col
        self.name = name
        self.message = f"非法的 identifier '{name}': {suggestion}"


class UnknownParameterError(SemanticError):
    def __init__(self, sheet: str, row: int, param_name: str, col: int | None = None) -> None:
        super().__init__(
            f"位宽表达式引用了未声明的 parameter '{param_name}'",
        )
        self.sheet = sheet
        self.row = row
        self.col = col
        self.param_name = param_name


class DuplicatePortError(SemanticError):
    def __init__(self, sheet: str, name: str, rows: list[int]) -> None:
        super().__init__(
            f"端口名 '{name}' 重复出现在行 {rows}",
        )
        self.name = name
        self.rows = rows


class ModuleNotFoundError(SemanticError):
    def __init__(self, name: str, available: list[str]) -> None:
        super().__init__(
            f"模块 '{name}' 不存在。可用模块: {available}",
        )
        self.name = name
        self.available = available


# ---- Generation layer (output side) ---------------------------------------

class RenderError(Exception):
    """Template/structure generation failed."""
    pass


# ---- v0.5: Hierarchy exceptions (SPEC §19.1) -------------------------------

class HierarchyError(Exception):
    """Base class for hierarchy-related errors."""
    pass


class OrphanChildError(HierarchyError):
    """A child sheet references a parent that doesn't exist."""
    def __init__(self, sheet: str, parent: str) -> None:
        super().__init__(f"子模块 sheet '{sheet}' 的父模块 '{parent}' 不存在")
        self.sheet = sheet
        self.parent = parent


class RecursiveHierarchyError(HierarchyError):
    """Circular reference detected in sheet names."""
    def __init__(self, sheet: str, path: list[str]) -> None:
        super().__init__(f"检测到循环引用: {' -> '.join(path)} -> {sheet}")
        self.sheet = sheet
        self.path = path


class EmptyHierarchyError(HierarchyError):
    """No top-level module found (all sheets have '.' prefix)."""
    def __init__(self) -> None:
        super().__init__("没有顶层模块（所有 sheet 名都含 '.'）")


# ---- v0.6 Phase 14: Naming conflict warning (SPEC §21) -------------------

class NamingConflictWarning(UserWarning):
    """A parameter name collides with a port name (case-insensitive).

    v0.6 mitigation: the generator will suffix the parameter with ``_p`` in
    the emitted Verilog (e.g. ``parameter WIDTH_p = 8``) and rewrite every
    in-text reference (width expressions, default literals) to use the
    suffixed name. The port itself keeps its original identifier.
    """

    def __init__(self, sheet: str, names: list[str]) -> None:
        quoted = ", ".join(f"'{n}'" for n in names)
        super().__init__(
            f"[sheet: {sheet}] parameter 和 port 重名（case-insensitive）: {quoted}。"
            f"Verilog 输出将自动给 parameter 加 '_p' 后缀以避免编译错误。"
        )
        self.sheet = sheet
        self.names = names
