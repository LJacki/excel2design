"""Verilog wrapper generator per SPEC §5.

Byte-stable per §5.7: no random, no timestamp, no env vars, no trailing whitespace.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from excel2design.core.models import Module, Port, ResetType


_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"


# Per SPEC §5.7.6: always blocks sorted by (clock, reset_type).
# Per SPEC §3.5.6: group key is (clock, reset_type).
_RESET_TYPE_ORDER = {ResetType.ASYNC: 0, ResetType.NONE: 1, ResetType.SYNC: 2}


@dataclass(frozen=True)
class AlwaysGroup:
    """One always block: regs sharing (clock, reset_type) tuple."""
    clock: str
    reset_type: ResetType
    is_async: bool
    regs: list[Port]

    @property
    def label(self) -> str:
        if self.reset_type == ResetType.NONE:
            return f"NO-RESET ALWAYS @clk={self.clock}"
        return f"{self.reset_type.value.upper()} RESET ALWAYS @clk={self.clock}"


def _group_regs_by_always(regs_with_default: list[Port]) -> list[AlwaysGroup]:
    """Group regs by (clock, reset_type). Returns sorted list.

    Excludes: regs without a clock declaration, regs with reset_type=NONE
    (those get initial block only, not always).
    """
    groups: dict[tuple[str, ResetType], list[Port]] = defaultdict(list)
    for port in regs_with_default:
        if not port.clock:
            continue
        if port.reset_type == ResetType.NONE:
            continue
        groups[(port.clock, port.reset_type)].append(port)

    sorted_keys = sorted(groups.keys(), key=lambda k: (k[0], _RESET_TYPE_ORDER[k[1]]))
    return [
        AlwaysGroup(
            clock=clock,
            reset_type=rt,
            is_async=(rt == ResetType.ASYNC),
            regs=groups[(clock, rt)],
        )
        for clock, rt in sorted_keys
    ]


def _setup_env() -> Environment:
    # Per SPEC §9 ADR: trim_blocks=True would eat newlines after `{% for %}` and
    # collapse all input ports onto one line. We keep trim_blocks=False and
    # control spacing manually in the template.
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        trim_blocks=False,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        undefined=StrictUndefined,
    )


def generate_wrapper(
    module: Module,
    source_file: Optional[Path | str] = None,
    source_sheet: Optional[str] = None,
) -> str:
    """Generate a Verilog wrapper for `module`."""
    env = _setup_env()
    template = env.get_template("verilog_wrapper.j2")

    # Pre-compute everything the template needs (one pass, no surprises)
    input_ports = module.inputs()
    output_ports = module.outputs()
    inout_ports = module.inouts()
    regs_with_default = [p for p in module.regs() if p.default]
    always_groups = _group_regs_by_always(regs_with_default)

    # Internal wires: wires that are NOT inputs (i.e. inout wires that need
    # an internal `wire` declaration, since inout ports still need them).
    internal_wires = [p for p in module.wires() if p.direction.value != "input"]
    # Internal regs with defaults (declared in port list, but we acknowledge them)
    internal_regs = [p for p in module.regs() if p.default]

    return template.render(
        module=module,
        source_file=str(source_file) if source_file else "",
        source_sheet=source_sheet or module.source_sheet or "",
        module_parameters=module.parameters,
        param_names=", ".join(p.name for p in module.parameters),
        input_ports=input_ports,
        output_ports=output_ports,
        inout_ports=inout_ports,
        internal_wires=internal_wires,
        internal_regs=internal_regs,
        regs_with_default=regs_with_default,
        always_groups=always_groups,
    )
