"""Instance connection algorithm (v0.5, SPEC §17).

Matches submodule ports to parent ports or sibling ports, detects
width mismatches, and generates internal wire declarations.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from excel2design.core.models import Module, Port


class ConnectionKind(Enum):
    PARENT_PORT = "parent_port"
    SIBLING_PORT = "sibling_port"
    PARENT_PARAM = "parent_param"
    UNCONNECTED = "unconnected"


@dataclass
class ConnectionResult:
    """Result of matching a single submodule port."""
    kind: ConnectionKind
    target_name: str = ""           # name of the signal to connect to
    target_port: Optional[Port] = None
    width_match: bool = True        # True if widths match exactly
    width_note: str = ""            # human-readable mismatch description


def match_port(
    port: Port,
    parent_module: Module,
    sibling_modules: list[Module],
    instance_name: str = "",
) -> ConnectionResult:
    """Match a submodule port to a connection target.

    Priority (SPEC §17.1):
      1. Parent module has a port with the same name
      2. A sibling module has a port with the same name
      3. Parent module has a parameter with the same name

    instance_name: used for fuzzy suffix matching (e.g. adc_a → prefer _a).
    """
    # Priority 1: parent port (exact match, then fuzzy with instance suffix)
    for parent_port in parent_module.ports:
        if parent_port.name == port.name or _fuzzy_match(parent_port.name, port.name, instance_name):
            # v0.6 Phase 12: when both ports are arrays, prefer shape-matched ones
            # to avoid silently truncating a 2-D port to a 1-D connection.
            if port.array_dim or parent_port.array_dim:
                if port.array_dim != parent_port.array_dim:
                    continue  # skip shape-mismatched parent
            wm = _check_width(port, parent_port)
            return ConnectionResult(
                kind=ConnectionKind.PARENT_PORT,
                target_name=parent_port.name,
                target_port=parent_port,
                width_match=wm[0],
                width_note=wm[1],
            )

    # Priority 2: sibling port
    for sibling in sibling_modules:
        for sib_port in sibling.ports:
            if sib_port.name == port.name:
                if port.array_dim or sib_port.array_dim:
                    if port.array_dim != sib_port.array_dim:
                        continue  # skip shape-mismatched sibling
                wm = _check_width(port, sib_port)
                return ConnectionResult(
                    kind=ConnectionKind.SIBLING_PORT,
                    target_name=sib_port.name,
                    target_port=sib_port,
                    width_match=wm[0],
                    width_note=wm[1],
                )

    # Priority 3: parent parameter
    for param in parent_module.parameters:
        if param.name == port.name:
            return ConnectionResult(
                kind=ConnectionKind.PARENT_PARAM,
                target_name=param.name,
            )

    return ConnectionResult(kind=ConnectionKind.UNCONNECTED)


def _check_width(a: Port, b: Port) -> tuple[bool, str]:
    """Compare two ports' widths. Returns (match: bool, note: str)."""
    wa = a.width.to_verilog()
    wb = b.width.to_verilog()
    if wa == wb:
        return True, ""
    return False, f"width mismatch — {a.name}:{wa} vs {b.name}:{wb}"


def _fuzzy_match(parent_name: str, child_name: str, instance: str = "") -> bool:
    """Check if parent port name matches child port after stripping
    instance suffix. When instance is given (e.g. adc_a), only try
    that specific suffix."""
    import re
    if parent_name == child_name:
        return True
    if instance and "_" in instance:
        suffix = "_" + instance.rsplit("_", 1)[-1]
        base = re.sub(re.escape(suffix) + "$", "", parent_name)
        if base == child_name:
            return True
    else:
        for pat in [r"_a$", r"_b$", r"_c$", r"_d$", r"_0$", r"_1$", r"_2$", r"_3$"]:
            if re.sub(pat, "", parent_name) == child_name:
                return True
    return False
