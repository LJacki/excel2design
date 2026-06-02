"""excel2design — Excel module port tables to box diagrams and Verilog wrapper.

Top-level convenience imports. The full API surface is intentionally small;
specialised users should import from the submodules.
"""

from __future__ import annotations

from excel2design.core.exceptions import (
    DuplicatePortError,
    ExcelParseError,
    FormulaCellError,
    HeaderMismatchError,
    IdentifierError,
    MarkerMissingError,
    MergedCellError,
    ModuleNotFoundError,
    PortValidationError,
    RenderError,
    SemanticError,
    UnknownParameterError,
    UnsupportedCellTypeError,
)
from excel2design.core.models import (
    Direction,
    Module,
    Parameter,
    ParamType,
    Port,
    ResetType,
    SignalType,
)
from excel2design.parsers.excel import get_module, parse_workbook

__version__ = "0.3.0"

__all__ = [
    # Version
    "__version__",
    # Parsing
    "parse_workbook",
    "get_module",
    # Models
    "Module",
    "Port",
    "Parameter",
    "Direction",
    "SignalType",
    "ResetType",
    "ParamType",
    # Exceptions
    "ExcelParseError",
    "MarkerMissingError",
    "HeaderMismatchError",
    "MergedCellError",
    "FormulaCellError",
    "UnsupportedCellTypeError",
    "SemanticError",
    "PortValidationError",
    "IdentifierError",
    "UnknownParameterError",
    "DuplicatePortError",
    "ModuleNotFoundError",
    "RenderError",
]
