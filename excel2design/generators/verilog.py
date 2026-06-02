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


def _detect_reset_per_clock(module: Module) -> str:
    """For each (clock, reset_type) used in always groups, find the most likely
    input reset port.

    Heuristic: look for input ports whose name contains 'rst' or 'reset',
    and pick the one that's:
      - on the same clock domain (same `clock` field if set), OR
      - the closest by name match if no clock binding
    Returns a multi-line string like:
        //   clk_a → rst_a_n (async)
        //   clk_b → rst_b_n (async)
        //   clk_c → (no reset)
    """
    lines: list[str] = []
    input_ports = module.inputs()

    # Collect all (clock, reset_type) tuples used by always groups
    clocks_with_default: set[tuple[str, ResetType]] = set()
    for port in module.regs():
        if port.default and port.clock and port.reset_type != ResetType.NONE:
            clocks_with_default.add((port.clock, port.reset_type))

    # Also include clocks that have regs without default (e.g. clk_c with no reset)
    all_clocks: set[str] = set()
    for port in module.regs():
        if port.clock:
            all_clocks.add(port.clock)
    # Merge
    target_clocks: set[str] = {c for c, _ in clocks_with_default} | all_clocks

    def _is_reset_candidate(p: Port) -> bool:
        name = p.name.lower()
        return ("rst" in name or "reset" in name) and p.type.value == "wire"

    for clock in sorted(target_clocks):
        # 1st choice: reset candidate explicitly tagged with this clock domain
        same_domain = [p for p in input_ports if _is_reset_candidate(p) and p.clock == clock]
        # 2nd choice: any reset candidate (fallback — common when user leaves the
        # clock column blank on reset ports)
        any_reset = [p for p in input_ports if _is_reset_candidate(p)]
        # 3rd choice: name-similarity hint (rst_a_n ~ clk_a, rst_b ~ clk_b, etc.)
        prefix = clock.split("_")[0]  # e.g. "clk" from "clk_a"
        name_match = [
            p for p in any_reset
            if any(part and part in p.name.lower() for part in clock.lower().split("_") if part != prefix)
        ]

        chosen: tuple[Optional[Port], str]  # (port, source_label)
        if same_domain:
            chosen = (min(same_domain, key=lambda p: len(p.name)), "explicit clock match")
        elif name_match:
            chosen = (min(name_match, key=lambda p: len(p.name)), "name match")
        elif any_reset:
            chosen = (min(any_reset, key=lambda p: len(p.name)), "fallback (any reset port)")
        else:
            chosen = (None, "no reset port detected")

        # Determine reset type for this clock
        rts = {rt for c, rt in clocks_with_default if c == clock}
        rt_str = "/".join(sorted(rt.value for rt in rts)) if rts else "none"

        if chosen[0] is not None:
            lines.append(f"//   {clock} → {chosen[0].name} ({rt_str})  [{chosen[1]}]")
        else:
            lines.append(f"//   {clock} → (NO reset port on this domain) ({rt_str})")

    return "\n".join(lines) if lines else "//   (no clock domains detected)"


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
        reset_map=_detect_reset_per_clock(module),
    )
