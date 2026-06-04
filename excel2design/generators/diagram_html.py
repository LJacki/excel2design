"""HTML block-diagram generator per SPEC §4.2.

Renders a Module as a self-contained, light-themed HTML document. The output is
byte-stable: no timestamps, no random sources, deterministic port ordering, LF
line endings, no trailing whitespace.

Public API:
    generate_html(module) -> str
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from excel2design.core.models import Module, Port, SignalType
from excel2design.utils.clock_colors import clock_color


# Template lives next to this module under excel2design/templates/.
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_TEMPLATE_NAME = "diagram_html.j2"


# ---- View-model for the template -------------------------------------------
#
# We pre-compute presentation-only fields (width_str, type_class) on the
# Python side so the Jinja2 template stays a thin renderer. This also keeps
# the "width=1 → omit bit-index" rule out of the template.

@dataclass(frozen=True)
class PortView:
    """Template-friendly view of a Port; one per input/output/inout slot."""

    name: str
    direction: Any            # Direction enum; the template reads .value
    type: SignalType          # enum; template reads .value and uses it as a key
    width_str: str            # e.g. "[7:0]" / "[DATA_WIDTH-1:0]" / "" (omitted for 1-bit)
    type_class: str           # "wire" | "reg" | "logic"
    default: str | None
    clock: str | None
    signed: bool
    comment: str | None
    arrow_color: str          # clock-domain color for the arrow

    @classmethod
    def from_port(cls, p: Port) -> "PortView":
        # width_str: omit for 1-bit, else "[MSB:0]" (fixed) or "[RAW-1:0]" (param).
        if p.width.is_parameter:
            if p.width.raw == "1":
                width_str = ""          # shouldn't happen (1-bit isn't parameter), but safe
            else:
                width_str = f"[{p.width.raw}-1:0]"
        else:
            # P0-3 fix: tolerate msb=None (default 1-bit from blank cell) — mirrors
            # PortWidth.to_verilog() so all 4 outputs handle 1-bit consistently.
            if p.width.msb is None or p.width.msb == 0:
                width_str = ""
            else:
                width_str = f"[{p.width.msb}:0]"
        return cls(
            name=p.name,
            direction=p.direction,
            type=p.type,
            width_str=width_str,
            type_class=p.type.value,
            default=p.default,
            clock=p.clock,
            signed=p.signed,
            comment=p.comment,
            arrow_color=clock_color(p.clock),
        )


# ---- Jinja2 environment (lazy) ---------------------------------------------
#
# trim_blocks + lstrip_blocks + keep_trailing_newline are mandated by SPEC §5.7
# (byte-stable output). We additionally set autoescape=False because the output
# is HTML, not a generic text template, and our content is escaped upstream
# (or comes from trusted Excel cells). We DO want autoescape to be off here
# because Excel cell values may legitimately contain `<`, `>`, `&` in comments
# — but we still want them rendered literally as the user wrote them.
# (Engineering comments in this domain are not untrusted HTML.)

@lru_cache(maxsize=1)
def _get_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,
        undefined=StrictUndefined,
    )
    return env


# ---- Public API -------------------------------------------------------------

def generate_html(module: Module) -> str:
    """Render `module` as a self-contained HTML document string.

    Byte-stable: same Module in → same bytes out, every time.
    """
    if not isinstance(module, Module):  # pragma: no cover - defensive
        raise TypeError(f"generate_html expects Module, got {type(module).__name__}")

    inputs = [PortView.from_port(p) for p in module.inputs()]
    outputs = [PortView.from_port(p) for p in module.outputs()]
    inouts = [PortView.from_port(p) for p in module.inouts()]

    env = _get_env()
    template = env.get_template(_TEMPLATE_NAME)
    rendered = template.render(
        module=module,
        inputs=inputs,
        outputs=outputs,
        inouts=inouts,
    )
    # Defensive normalisation: collapse CRLF→LF, strip trailing whitespace per line.
    return _normalise(rendered)


def _normalise(s: str) -> str:
    """Enforce LF line endings and strip trailing whitespace per line (SPEC §5.7.2)."""
    out_lines = []
    for line in s.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        out_lines.append(line.rstrip())
    return "\n".join(out_lines)
