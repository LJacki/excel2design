"""Verilog wrapper generator per SPEC §5.

Byte-stable per §5.7. v0.4: column-aligned port/parameter declarations.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from excel2design.core.models import Module, Port, ResetType, Project
from excel2design.core.connection import ConnectionKind, match_port, collect_internal_wires


_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
_RESET_TYPE_ORDER = {ResetType.ASYNC: 0, ResetType.NONE: 1, ResetType.SYNC: 2}


@dataclass(frozen=True)
class AlwaysGroup:
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
    groups: dict[tuple[str, ResetType], list[Port]] = defaultdict(list)
    for port in regs_with_default:
        if not port.clock:
            continue
        if port.reset_type == ResetType.NONE:
            continue
        groups[(port.clock, port.reset_type)].append(port)
    sorted_keys = sorted(groups.keys(), key=lambda k: (k[0], _RESET_TYPE_ORDER[k[1]]))
    return [
        AlwaysGroup(clock=ck, reset_type=rt, is_async=(rt == ResetType.ASYNC), regs=groups[(ck, rt)])
        for ck, rt in sorted_keys
    ]


def _detect_reset_per_clock(module: Module) -> str:
    lines: list[str] = []
    input_ports = module.inputs()
    clocks_with_default: set[tuple[str, ResetType]] = set()
    for port in module.regs():
        if port.default and port.clock and port.reset_type != ResetType.NONE:
            clocks_with_default.add((port.clock, port.reset_type))
    all_clocks: set[str] = set()
    for port in module.regs():
        if port.clock:
            all_clocks.add(port.clock)
    target_clocks: set[str] = {c for c, _ in clocks_with_default} | all_clocks

    def _is_reset_candidate(p: Port) -> bool:
        return ("rst" in p.name.lower() or "reset" in p.name.lower()) and p.type.value == "wire"

    for clock in sorted(target_clocks):
        same_domain = [p for p in input_ports if _is_reset_candidate(p) and p.clock == clock]
        any_reset = [p for p in input_ports if _is_reset_candidate(p)]
        prefix = clock.split("_")[0]
        name_match = [
            p for p in any_reset
            if any(part and part in p.name.lower() for part in clock.lower().split("_") if part != prefix)
        ]
        if same_domain:
            chosen = (min(same_domain, key=lambda p: len(p.name)), "explicit clock match")
        elif name_match:
            chosen = (min(name_match, key=lambda p: len(p.name)), "name match")
        elif any_reset:
            chosen = (min(any_reset, key=lambda p: len(p.name)), "fallback")
        else:
            chosen = (None, "no reset port detected")
        rts = {rt for c, rt in clocks_with_default if c == clock}
        rt_str = "/".join(sorted(rt.value for rt in rts)) if rts else "none"
        if chosen[0] is not None:
            lines.append(f"//   {clock} \u2192 {chosen[0].name} ({rt_str})  [{chosen[1]}]")
        else:
            lines.append(f"//   {clock} \u2192 (NO reset port on this domain) ({rt_str})")
    return "\n".join(lines) if lines else "//   (no clock domains detected)"


# ---- Column-aligned port/parameter formatting --------------------------------

def _fmt_params(params) -> list[str]:
    """Return aligned parameter declaration lines.

    Columns: name(padded to max) = value(padded to max), comma
    """
    if not params:
        return []
    max_name = max(len(p.name) for p in params)
    max_val = max(len(str(p.value)) for p in params)
    lines = []
    for p in params:
        if p.width:
            lines.append(f"    parameter [{int(p.width)-1}:0] {p.name:<{max_name}} = {str(p.value):<{max_val}},")
        else:
            lines.append(f"    parameter {p.name:<{max_name}} = {str(p.value):<{max_val}},")
    return lines


def _fmt_ports(ports: list[Port], max_name: int) -> list[str]:
    """Return column-aligned port declaration lines.

    Columns: direction(7) signed(7) type(5) width(w) name({max_name}) ,comment
    """
    if not ports:
        return []
    width_strs = [p.width.to_verilog() for p in ports]
    max_width = max(len(w) for w in width_strs) if width_strs else 0

    lines = []
    for p in ports:
        w = p.width.to_verilog()
        direction = f"{p.direction.value:<7}"
        signed = f"{'signed':<7}" if p.signed else " " * 7
        typ = f"{p.type.value:<5}"
        width_col = f"{w:<{max_width}}" if w else " " * max_width
        comment = f"  // {p.comment}" if p.comment else ""
        lines.append(f"    {direction}{signed}{typ}{width_col} {p.name:<{max_name}},{comment}")
    return lines


def _setup_env() -> Environment:
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
    project: Optional[Project] = None,
) -> str:
    env = _setup_env()
    template = env.get_template("verilog_wrapper.j2")

    input_ports = module.inputs()
    output_ports = module.outputs()
    inout_ports = module.inouts()
    all_ports = input_ports + output_ports + inout_ports
    max_name = max((len(p.name) for p in all_ports), default=0)
    regs_with_default = [p for p in module.regs() if p.default]
    always_groups = _group_regs_by_always(regs_with_default)

    # v0.5: submodule instances and internal wires (optional)
    sub_instances = []
    wire_lines = []
    if project is not None:
        sheet = source_sheet or module.name
        instances = project.get_submodules(sheet, recursive=False)
        wires = collect_internal_wires(project, sheet)

        # Format internal wire declarations with column alignment
        if wires:
            max_wire_name = max(len(w.name) for w in wires)
            max_wire_width = max(len(w.width) for w in wires) if any(w.width for w in wires) else 0
            for w in wires:
                width_col = f"{w.width:<{max_wire_width + 1}}" if w.width else " " * (max_wire_width + 1)
                src_note = f"  // connects {' <-> '.join(w.sources)}" if w.sources else ""
                wire_lines.append(f"    wire {width_col}{w.name:<{max_wire_name}} ;{src_note}")

        for inst in instances:
            ports = []
            # Build sibling module list for internal wire matching
            sibling_mods = [inst2.module for inst2 in instances if inst2 != inst]
            for p in inst.module.ports:
                result = match_port(p, module, sibling_mods)
                conn = result.target_name if result.kind != ConnectionKind.UNCONNECTED else ""
                comment = ""
                if result.kind == ConnectionKind.UNCONNECTED:
                    if p.direction.value == "input":
                        comment = "// TODO: drive this signal"
                    else:
                        comment = "// TODO: no matching port"
                elif not result.width_match:
                    comment = f"// {result.width_note}"
                ports.append({"name": p.name, "connection": conn, "comment": comment})

            # Format instance port lines with column alignment
            max_pn = max(len(p["name"]) for p in ports) if ports else 0
            max_cn = max(len(p["connection"]) for p in ports) if ports else 0
            port_lines = []
            for i, p in enumerate(ports):
                suffix = "," if i < len(ports) - 1 else " "
                cmt = f"  {p['comment']}" if p["comment"] else ""
                port_lines.append(
                    f"        .{p['name']:<{max_pn + 1}} ({p['connection']:<{max_cn}}) {suffix}{cmt}"
                )

            # Build the full instance string
            lines = []
            if inst.module.parameters:
                lines.append(f"    {inst.module.name} #(")
                for i, param in enumerate(inst.module.parameters):
                    comma = "," if i < len(inst.module.parameters) - 1 else ""
                    lines.append(f"        .{param.name}({param.name}){comma}")
                lines.append(f"    ) {inst.instance_name} (")
            else:
                lines.append(f"    {inst.module.name} {inst.instance_name} (")
            lines.extend(port_lines)
            lines.append("    );")
            sub_instances.append("\n".join(lines))

    return template.render(
        module=module,
        source_file=str(source_file) if source_file else "",
        source_sheet=source_sheet or module.source_sheet or "",
        param_lines=_fmt_params(module.parameters),
        input_lines=_fmt_ports(input_ports, max_name),
        output_lines=_fmt_ports(output_ports, max_name),
        inout_lines=_fmt_ports(inout_ports, max_name),
        regs_with_default=regs_with_default,
        always_groups=always_groups,
        wire_lines=wire_lines,
        sub_instances=sub_instances,
    )
