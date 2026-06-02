"""Verilog identifier validation per SPEC §3.5.2.

A valid Verilog identifier:
  - Matches ^[A-Za-z_][A-Za-z0-9_]*$
  - Is NOT a Verilog/SystemVerilog reserved word

Applied to: module names, parameter names, port names.
"""

from __future__ import annotations

import re
from typing import Optional

from excel2design.core.exceptions import IdentifierError


# Comprehensive Verilog + SystemVerilog reserved word list (per IEEE 1800-2017).
VERILOG_KEYWORDS: frozenset[str] = frozenset({
    # Verilog-1995/2001 keywords
    "always", "and", "assign", "automatic", "begin", "buf", "bufif0", "bufif1",
    "case", "casex", "casez", "cell", "cmos", "config", "deassign", "default",
    "defparam", "design", "disable", "edge", "else", "end", "endcase",
    "endconfig", "endfunction", "endgenerate", "endmodule", "endprimitive",
    "endspecify", "endtable", "endtask", "event", "for", "force", "forever",
    "fork", "function", "generate", "genvar", "highz0", "highz1", "if",
    "ifnone", "include", "initial", "inout", "input", "integer", "join",
    "large", "liblist", "library", "localparam", "macromodule", "medium",
    "module", "nand", "negedge", "nmos", "nor", "not", "notif0", "notif1",
    "or", "output", "parameter", "pmos", "posedge", "primitive", "pull0",
    "pull1", "pulldown", "pullup", "rcmos", "real", "realtime", "reg",
    "release", "repeat", "rnmos", "rpmos", "rtran", "rtranif0", "rtranif1",
    "scalared", "small", "specify", "specparam", "strong0", "strong1",
    "supply0", "supply1", "table", "task", "time", "tran", "tranif0",
    "tranif1", "tri", "tri0", "tri1", "triand", "trior", "trireg", "unsigned",
    "use", "vectored", "wait", "wand", "weak0", "weak1", "while", "wire",
    "wor", "xnor", "xor",
    # SystemVerilog additions
    "alias", "always_comb", "always_ff", "always_latch", "assert", "assume",
    "before", "bind", "bins", "binsof", "bit", "break", "byte", "chandle",
    "class", "clocking", "const", "constraint", "context", "continue", "cover",
    "covergroup", "coverpoint", "cross", "deferred", "dist", "do", "endclass",
    "endclocking", "endgroup", "endinterface", "endpackage", "endprogram",
    "endproperty", "endsequence", "enum", "export", "extends", "extern",
    "final", "first_match", "foreach", "forkjoin", "global", "iff", "import",
    "inside", "int", "interface", "intersect", "join_any", "join_none", "let",
    "logic", "longint", "matches", "modport", "new", "null", "package",
    "packed", "priority", "program", "property", "protected", "pure", "rand",
    "randc", "randsequence", "ref", "return", "sequence", "shortint", "shortreal",
    "solve", "static", "string", "struct", "super", "tagged", "this", "throughout",
    "type", "typedef", "union", "unique", "unique0", "var", "virtual", "void",
    "wait_order", "with", "within",
})


_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def is_valid_identifier(name: str) -> bool:
    """Check identifier legality without raising."""
    return bool(_IDENT_RE.match(name)) and name not in VERILOG_KEYWORDS


def check_identifier(
    name: str,
    kind: str,
    sheet: Optional[str] = None,
    row: Optional[int] = None,
    col: Optional[int] = None,
) -> None:
    """Raise IdentifierError if `name` is not a valid Verilog identifier.

    `kind` is a human-readable label for the error message, e.g. "module", "port", "parameter".
    """
    if not name:
        raise IdentifierError(
            sheet or "<unknown>", row or 0, col or 0, name or "(empty)",
            suggestion=f"{kind} 名不能为空",
        )
    if not _IDENT_RE.match(name):
        raise IdentifierError(
            sheet or "<unknown>", row or 0, col or 0, name,
            suggestion=f"{kind} 必须以字母/下划线开头，后接字母/数字/下划线",
        )
    if name in VERILOG_KEYWORDS:
        raise IdentifierError(
            sheet or "<unknown>", row or 0, col or 0, name,
            suggestion=f"{kind} 不能是 Verilog/SystemVerilog 保留字",
        )
