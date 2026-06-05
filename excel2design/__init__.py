"""excel2design — Excel module port tables to box diagrams and Verilog wrapper.

Top-level convenience imports. The full API surface is intentionally small;
specialised users should import from the submodules.
"""

from __future__ import annotations

from excel2design.core.exceptions import (
    DuplicatePortError,
    EmptyHierarchyError,
    ExcelParseError,
    FormulaCellError,
    HeaderMismatchError,
    HierarchyError,
    IdentifierError,
    MarkerMissingError,
    MergedCellError,
    ModuleNotFoundError,
    OrphanChildError,
    PortValidationError,
    RecursiveHierarchyError,
    RenderError,
    SemanticError,
    UnknownParameterError,
    UnsupportedCellTypeError,
)
from excel2design.core.models import (
    Define,
    Direction,
    Module,
    Parameter,
    ParamType,
    Port,
    Project,
    ResetType,
    SignalType,
    SubmoduleInstance,
)
from excel2design.parsers.excel import get_module, parse_workbook

__version__ = "0.5.0-dev"

__all__ = [
    "__version__",
    # Parsing
    "parse_workbook",
    "get_module",
    # Models
    "Module", "Port", "Parameter", "Define", "Project", "SubmoduleInstance",
    "Direction", "SignalType", "ResetType", "ParamType",
    # Exceptions
    "ExcelParseError", "MarkerMissingError", "HeaderMismatchError",
    "MergedCellError", "FormulaCellError", "UnsupportedCellTypeError",
    "SemanticError", "PortValidationError", "IdentifierError",
    "UnknownParameterError", "DuplicatePortError", "ModuleNotFoundError",
    "RenderError", "HierarchyError", "OrphanChildError",
    "RecursiveHierarchyError", "EmptyHierarchyError",
]
