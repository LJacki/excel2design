"""Verilog wrapper generator per SPEC §5.

Byte-stable per §5.7. v0.4: column-aligned port/parameter declarations.
v0.6 Phase 14: parameter/port naming conflict → parameter gets ``_p`` suffix.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from excel2design.core.models import Module, Parameter, Port, ResetType, Project
from excel2design.core.connection import ConnectionKind, match_port
from excel2design.parsers.excel import find_param_port_conflicts


_TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "templates"
_RESET_TYPE_ORDER = {ResetType.ASYNC: 0, ResetType.NONE: 1, ResetType.SYNC: 2}

# v0.6 Phase 14: parameter/port name-collision mitigation.
# Word-boundary regex; case-insensitive. Only identifiers [A-Za-z_][A-Za-z0-9_]*
# are eligible for substitution (we must not touch digits/literals).
_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_P_SUFFIX = "_p"


def _substitute_param_refs(text: str, name_map: dict[str, str]) -> str:
    """Replace whole-word parameter references in ``text`` per ``name_map``.

    Keys in ``name_map`` are case-insensitive. The replacement uses the
    original (un-suffixed) casing of the *value* passed in by the caller
    — typically the key with ``_p`` appended.

    Example: ``"[WIDTH-1:0]"`` with ``{"WIDTH": "WIDTH_p"}`` →
    ``"[WIDTH_p-1:0]"``.
    """
    if not text or not name_map:
        return text
    lower_map = {k.lower(): v for k, v in name_map.items()}

    def _repl(match: re.Match) -> str:
        token = match.group(0)
        replacement = lower_map.get(token.lower())
        return replacement if replacement is not None else token

    return _IDENTIFIER_RE.sub(_repl, text)


def _build_param_name_map(module: Module) -> dict[str, str]:
    """Return ``{original_param_name: suffixed_name}`` for conflicting params.

    Only parameters whose name (case-insensitive) collides with a port name
    are included. Original casing of the key is preserved; the value is the
    same name with ``_p`` appended (e.g. ``WIDTH`` → ``WIDTH_p``).
    """
    conflicts = find_param_port_conflicts(module.parameters, module.ports)
    return {name: f"{name}{_P_SUFFIX}" for name in conflicts}


@dataclass(frozen=True)
class AlwaysGroup:
    clock: str
    reset_type: ResetType
    is_async: bool
    reset_name: str = "rst_n"   # P0-5 fix: per-group reset signal name
    reset_note: str = ""        # diagnostic: explicit/name match/fallback/no port
    regs: list[Port] = field(default_factory=list)

    @property
    def label(self) -> str:
        if self.reset_type == ResetType.NONE:
            return f"NO-RESET ALWAYS @clk={self.clock}"
        return f"{self.reset_type.value.upper()} RESET ALWAYS @clk={self.clock}"


def _group_regs_by_always(
    regs_with_default: list[Port],
    reset_names: Optional[dict[str, str]] = None,
) -> list[AlwaysGroup]:
    """Group regs by (clock, reset_type) and pick a reset name for each group.

    P0-5 fix: the chosen reset name is propagated to the template instead of
    hard-coding ``rst_n`` (the previous behaviour silently produced wrong
    always blocks for designs whose reset port is named differently per
    clock domain — e.g. ``rst_a_n`` / ``rst_b_n``).
    """
    reset_names = reset_names or {}
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
            clock=ck,
            reset_type=rt,
            is_async=(rt == ResetType.ASYNC),
            reset_name=reset_names.get(ck, "rst_n"),
            regs=groups[(ck, rt)],
        )
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
            lines.append(f"//   {clock} → {chosen[0].name} ({rt_str})  [{chosen[1]}]")
        else:
            lines.append(f"//   {clock} → (NO reset port on this domain) ({rt_str})")
    return "\n".join(lines) if lines else "//   (no clock domains detected)"


def _resolve_reset_names_per_clock(
    module: Module, regs_with_default: list[Port]
) -> dict[str, str]:
    """Pick a reset port name for every clock domain (P0-5 fix).

    Returns ``{clock_name: reset_port_name}`` for each clock that appears in
    the reg-with-default list. Falls back to ``"rst_n"`` when no candidate
    is found (legacy default — keeps single-clock designs working even
    when no ``rst``-named port is declared).
    """
    input_ports = module.inputs()

    def _is_reset_candidate(p: Port) -> bool:
        return ("rst" in p.name.lower() or "reset" in p.name.lower()) and p.type.value == "wire"

    clocks = {p.clock for p in regs_with_default if p.clock}
    any_reset = [p for p in input_ports if _is_reset_candidate(p)]
    result: dict[str, str] = {}
    for clock in sorted(clocks):
        same_domain = [p for p in input_ports if _is_reset_candidate(p) and p.clock == clock]
        prefix = clock.split("_")[0]
        name_match = [
            p for p in any_reset
            if any(part and part in p.name.lower() for part in clock.lower().split("_") if part != prefix)
        ]
        if same_domain:
            result[clock] = min(same_domain, key=lambda p: len(p.name)).name
        elif name_match:
            result[clock] = min(name_match, key=lambda p: len(p.name)).name
        elif any_reset:
            result[clock] = min(any_reset, key=lambda p: len(p.name)).name
        else:
            result[clock] = "rst_n"
    return result


# ---- Column-aligned port/parameter formatting --------------------------------

# P1-3 fix: the +1 padding between an aligned name and a parenthesis / comma
# is now a named constant. The original magic +1 appeared in 5+ f-strings
# across this file; keeping it here makes the SPEC §17.6 alignment rule
# explicit and easy to change in one place.
_ALIGN_PAD = 1


def _fmt_params(params, name_map: dict[str, str] | None = None) -> list[str]:
    """Return aligned parameter declaration lines.

    Columns: name(padded to max) = value(padded to max), comma

    v0.6 Phase 14: ``name_map`` maps original parameter name → suffixed
    name (e.g. ``WIDTH`` → ``WIDTH_p``). When present, conflicting params
    are emitted with the suffix; the *value* column is also rewritten so
    that any internal references use the new identifier.
    """
    if not params:
        return []
    nm: dict[str, str] = name_map or {}
    # Display the suffixed name (or the original if not in map).
    display_names = [nm.get(p.name, p.name) for p in params]
    max_name = max(len(n) for n in display_names)
    # Values can also reference the parameter (rare, but possible).
    display_values = [_substitute_param_refs(str(p.value), nm) for p in params]
    max_val = max(len(v) for v in display_values)
    lines = []
    n = len(params)
    for i, p in enumerate(params):
        suffix = "," if i < n - 1 else ""
        disp_name = display_names[i]
        disp_value = display_values[i]
        if p.width:
            lines.append(
                f"    parameter [{int(p.width)-1}:0] "
                f"{disp_name:<{max_name + _ALIGN_PAD}} = {disp_value:<{max_val}}{suffix}"
            )
        else:
            lines.append(
                f"    parameter {disp_name:<{max_name + _ALIGN_PAD}} = {disp_value:<{max_val}}{suffix}"
            )
    return lines


def _fmt_ports(ports: list[Port], max_name: int, is_last_group: bool = False) -> list[str]:
    """Return column-aligned port declaration lines.

    is_last_group: True if no more port groups follow (outputs after inputs, etc.)

    v0.6 Phase 13: if a port has ``is_interface=True``, append
    ``// interface`` annotation so that downstream tools / humans can
    easily identify interface-grouped members without parsing the
    spreadsheet.
    """
    if not ports:
        return []
    width_strs = [p.width.to_verilog() for p in ports]
    max_width = max(len(w) for w in width_strs) if width_strs else 0

    lines = []
    n = len(ports)
    for i, p in enumerate(ports):
        w = p.width.to_verilog()
        direction = f"{p.direction.value:<7}"
        typ = f"{p.type.value:<5}"
        signed = f"{'signed':<7}" if p.signed else " " * 7
        width_col = f"{w:<{max_width}}" if w else " " * max_width
        comment = f"  // {p.comment}" if p.comment else ""
        # Phase 13: interface annotation
        iface_note = "  // interface" if p.is_interface else ""
        is_last_overall = is_last_group and (i == n - 1)
        suffix = "" if is_last_overall else ","
        lines.append(f"    {direction}{typ}{signed}{width_col} {p.name:<{max_name}}{suffix}{comment}{iface_note}")
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

    # v0.6 Phase 14: build name_map of conflicting parameter names.
    # Any width expression or default value referencing a conflicting
    # parameter must be rewritten to use the suffixed identifier so the
    # emitted Verilog compiles. The original Parameter/Port objects are
    # not mutated; we substitute on the fly via _substitute_param_refs.
    name_map = _build_param_name_map(module)

    def _renamed_width(p: Port):
        """Return a (string, dataclass) pair for the port's width expression.

        The PortWidth object is reused when the substitution is a no-op;
        a new PortWidth is constructed when the raw string changed (so the
        existing ``to_verilog()`` can format ``[<raw>-1:0]`` correctly).
        """
        if not name_map:
            return p.width
        new_raw = _substitute_param_refs(p.width.raw, name_map)
        if new_raw == p.width.raw:
            return p.width
        from excel2design.parsers.width import PortWidth
        return PortWidth(raw=new_raw, msb=p.width.msb, is_parameter=p.width.is_parameter)

    def _renamed_default(d: Optional[str]) -> Optional[str]:
        if d is None or not name_map:
            return d
        return _substitute_param_refs(d, name_map)

    def _apply_suffix_to_port(p: Port) -> Port:
        """Return a copy of ``p`` with width/default rewritten per name_map."""
        new_width = _renamed_width(p)
        new_default = _renamed_default(p.default)
        if new_width is p.width and new_default is p.default:
            return p
        return Port(
            name=p.name,
            direction=p.direction,
            width=new_width,
            type=p.type,
            default=new_default,
            clock=p.clock,
            reset_type=p.reset_type,
            signed=p.signed,
            is_interface=p.is_interface,
            comment=p.comment,
        )

    # Apply suffix to every port whose width/default may reference a
    # conflicting parameter. This is a no-op for ports that don't reference
    # the renamed parameter (their raw width strings are untouched).
    if name_map:
        new_ports = [_apply_suffix_to_port(p) for p in module.ports]
        module = Module(
            name=module.name,
            ports=new_ports,
            parameters=module.parameters,
            source_file=module.source_file,
            source_sheet=module.source_sheet,
        )
        input_ports = module.inputs()
        output_ports = module.outputs()
        inout_ports = module.inouts()
        all_ports = input_ports + output_ports + inout_ports
        regs_with_default = [p for p in module.regs() if p.default]

    # P0-5 fix: compute per-clock reset port names and pass them to the
    # always-group builder so the template can emit the right signal.
    reset_names = _resolve_reset_names_per_clock(module, regs_with_default)
    always_groups = _group_regs_by_always(regs_with_default, reset_names)

    # v0.5: submodule instances and internal wires (optional)
    sub_instances = []
    wire_lines = []
    if project is not None:
        sheet = source_sheet or module.name
        instances = project.get_submodules(sheet, recursive=False)

        # First pass: compute all connections, tracking sibling wires
        all_connections: list[dict] = []  # per-instance port connections
        sibling_wires: dict[str, dict] = {}  # port_name -> {drivers: [...], sinks: [...]}

        for inst in instances:
            sibling_mods = [inst2.module for inst2 in instances if inst2 != inst]
            ports = []
            for p in inst.module.ports:
                result = match_port(p, module, sibling_mods, inst.instance_name)
                conn = result.target_name if result.kind != ConnectionKind.UNCONNECTED else ""
                comment = ""
                if result.kind == ConnectionKind.UNCONNECTED:
                    if p.direction.value == "input":
                        comment = "// TODO: drive this signal"
                    else:
                        comment = "// TODO: no matching port"
                elif not result.width_match:
                    comment = f"// {result.width_note}"
                elif result.kind == ConnectionKind.SIBLING_PORT:
                    # Track sibling wire — determine if driver or sink
                    if p.direction.value == "output":
                        sibling_wires.setdefault(p.name, {"drivers": [], "sinks": [], "width": p.width.to_verilog()})
                        sibling_wires[p.name]["drivers"].append(inst.instance_name)
                    else:
                        sibling_wires.setdefault(p.name, {"drivers": [], "sinks": [], "width": p.width.to_verilog()})
                        sibling_wires[p.name]["sinks"].append(inst.instance_name)
                ports.append({"name": p.name, "connection": conn, "comment": comment})
            all_connections.append({"inst": inst, "ports": ports})

        # Generate internal wire declarations from actual connections
        if sibling_wires:
            max_wn = max(len(n) for n in sibling_wires)
            max_ww = max(len(w["width"]) for w in sibling_wires.values()) if any(w["width"] for w in sibling_wires.values()) else 0
            for name, info in sibling_wires.items():
                wcol = f"{info['width']:<{max_ww + 1}}" if info["width"] else " " * (max_ww + 1)
                drivers_str = ", ".join(info["drivers"])
                sinks_str = ", ".join(info["sinks"])
                note = f"  // {drivers_str} → {sinks_str}" if drivers_str and sinks_str else ""
                wire_lines.append(f"wire {wcol}{name:<{max_wn}} ;{note}")

        # Generate instance blocks
        for conn_data in all_connections:
            inst = conn_data["inst"]
            ports = conn_data["ports"]
            max_pn = max(len(p["name"]) for p in ports) if ports else 0
            max_cn = max(len(p["connection"]) for p in ports) if ports else 0
            port_lines = []
            for i, p in enumerate(ports):
                suffix = "," if i < len(ports) - 1 else " "
                cmt = f"  {p['comment']}" if p["comment"] else ""
                port_lines.append(
                    f"    .{p['name']:<{max_pn + 1}} ({p['connection']:<{max_cn}}) {suffix}{cmt}"
                )

            lines = []
            if inst.module.parameters:
                lines.append(f"{inst.module.name} #(")
                max_pn_p = max(len(p.name) for p in inst.module.parameters)
                pn_pad = max(max_pn, max_pn_p)  # align ) column with ports
                for i, param in enumerate(inst.module.parameters):
                    comma = "," if i < len(inst.module.parameters) - 1 else " "
                    lines.append(
                        f"    .{param.name:<{pn_pad + 1}} ({param.name:<{max_cn}}) {comma}"
                    )
                lines.append(f") {inst.instance_name} (")
            else:
                lines.append(f"{inst.module.name} {inst.instance_name} (")
            lines.extend(port_lines)
            lines.append(");")
            sub_instances.append("\n".join(lines))

    return template.render(
        module=module,
        source_file=str(source_file) if source_file else "",
        source_sheet=source_sheet or module.source_sheet or "",
        param_lines=_fmt_params(module.parameters, name_map),
        input_lines=_fmt_ports(input_ports, max_name, is_last_group=not bool(output_ports or inout_ports)),
        output_lines=_fmt_ports(output_ports, max_name, is_last_group=not bool(inout_ports)),
        inout_lines=_fmt_ports(inout_ports, max_name, is_last_group=True),
        regs_with_default=regs_with_default,
        always_groups=always_groups,
        wire_lines=wire_lines,
        sub_instances=sub_instances,
    )
