"""Shared layout for hierarchy diagrams (P1-5 fix).

Both the SVG and Excalidraw hierarchy generators used to duplicate the
same algorithms for:
  - cols/rows grid placement of sub-module boxes
  - inner canvas / wrapper size computation
  - per-submodule port position collection (for the inter-submodule wire lines)
  - sorting and pairing of wire endpoints

This module extracts those algorithms into a single ``HierarchyLayout``
dataclass that the two renderers can consume as pre-computed coordinates
plus a list of ``Wire`` records. The renderers themselves only need to
translate the layout into their respective element types (ET for SVG,
dict for Excalidraw).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from excel2design.core.models import Project


@dataclass(frozen=True)
class SubLayout:
    """A single sub-module's box and its rendered port positions."""
    instance_name: str          # "u_a"
    sheet_name: str             # "top.u_a"
    box_x: int
    box_y: int
    box_w: int
    box_h: int
    # Per port: (port_name, label_text, color_hex, x, y, direction)
    ports: list[tuple[str, str, str, int, int, str]] = field(default_factory=list)


@dataclass(frozen=True)
class Wire:
    """An inter-submodule internal wire (P1-5: shared by both renderers)."""
    name: str
    endpoints: list[tuple[int, int, str]]   # (x, y, direction)
    # After sorting, endpoints are guaranteed to be [output..., input...] —
    # renderers can iterate `endpoints` and draw one segment per consecutive
    # pair without re-implementing the outs-first sort.


@dataclass(frozen=True)
class HierarchyLayout:
    """Pre-computed layout for a hierarchy diagram (P1-5).

    Produced by :func:`compute_hierarchy_layout`; consumed by the two
    hierarchy renderers in this package. All sizes are in the renderer's
    native unit (SVG user units, Excalidraw pixels — the two happen to
    share a value scale).
    """
    top_name: str
    canvas_w: int
    canvas_h: int
    wrap_x: int
    wrap_y: int
    wrapper_w: int
    wrapper_h: int
    # Top module ports (label_text, color, x, y, is_input).
    top_inputs: list[tuple[str, str, int, int]] = field(default_factory=list)
    top_outputs: list[tuple[str, str, int, int]] = field(default_factory=list)
    sub_layouts: list[SubLayout] = field(default_factory=list)
    wires: list[Wire] = field(default_factory=list)


def compute_hierarchy_layout(
    project: Project,
    top_sheet: str,
    *,
    sub_w: int = 240,
    sub_h_per_port: int = 18,
    sub_h_base: int = 40,
    sub_h_min: int = 80,
    sub_spacing: int = 30,
    wrapper_pad: int = 100,
    port_row_h: int = 22,
    port_y_start: int = 60,
    parent_label_offset: int = 110,
    arrow_len: int = 46,
    wrap_x: int = 350,
    wrap_y: int = 200,
) -> Optional[HierarchyLayout]:
    """Compute layout for a top-down hierarchy diagram (P1-5).

    Returns ``None`` if ``top_sheet`` is missing from the project.

    The two existing renderers use slightly different numbers (SVG: 240px
    boxes, 30px spacing, port_y_start 50+wrap_y+28; Excalidraw: 240px
    boxes, 30px spacing, port_y_start wrap_y+60). The defaults above
    match Excalidraw; the SVG renderer is kept byte-stable by passing
    its own values to this function.
    """
    top_mod = project.modules.get(top_sheet)
    if top_mod is None:
        return None

    instances = project.get_submodules(top_sheet, recursive=False)
    n_inst = len(instances)

    # Box sizes
    if instances:
        sub_h = max(max(len(inst.module.ports) * sub_h_per_port + sub_h_base
                          for inst in instances), sub_h_min)
    else:
        sub_h = sub_h_min

    cols = min(n_inst, 3) if n_inst > 0 else 1
    rows = (n_inst + cols - 1) // cols if n_inst > 0 else 1
    inner_w = cols * (sub_w + sub_spacing) + sub_spacing
    inner_h = rows * (sub_h + sub_spacing) + sub_spacing
    wrapper_w = inner_w + wrapper_pad
    wrapper_h = max(inner_h + wrapper_pad,
                    max(len(top_mod.inputs()), len(top_mod.outputs())) * port_row_h + wrapper_pad)

    canvas_w = wrapper_w + 2 * parent_label_offset + arrow_len + 40
    canvas_h = wrapper_h + 80

    # Top-module inputs/outputs: (label, color, x, y)
    from excel2design.utils.clock_colors import clock_color
    top_inputs = []
    for i, p in enumerate(top_mod.inputs()):
        py = wrap_y + port_y_start + i * port_row_h
        color = clock_color(p.clock, is_input=True)
        top_inputs.append((p.name, color, wrap_x - arrow_len - 4, py))

    top_outputs = []
    for i, p in enumerate(top_mod.outputs()):
        py = wrap_y + port_y_start + i * port_row_h
        color = clock_color(p.clock, is_input=False)
        top_outputs.append((p.name, color, wrap_x + wrapper_w + 4, py))

    # Per-submodule port positions
    from excel2design.utils.clock_colors import clock_color as _cc
    parent_port_names = {p.name for p in top_mod.ports}
    sub_layouts: list[SubLayout] = []
    port_positions: dict[str, list[tuple[int, int, str]]] = defaultdict(list)

    for idx, inst in enumerate(instances):
        row, col = idx // cols, idx % cols
        sx = wrap_x + sub_spacing + col * (sub_w + sub_spacing)
        sy = wrap_y + sub_spacing + row * (sub_h + sub_spacing)
        sub_ports: list[tuple[str, str, str, int, int, str]] = []
        for pi, p in enumerate(inst.module.ports):
            py = sy + sub_h_base - 16 + pi * sub_h_per_port
            if py > sy + sub_h - 4:
                break
            color = _cc(p.clock, is_input=(p.direction.value == "input"))
            if p.direction.value == "input":
                label = f"← {p.name}"
                tx, port_x = sx + 6, sx
            else:
                label = f"{p.name} →"
                tx, port_x = sx + sub_w - 6, sx + sub_w
            sub_ports.append((p.name, label, color, tx, py, p.direction.value))
            if p.name not in parent_port_names:
                port_positions[p.name].append((port_x, py, p.direction.value))
        sub_layouts.append(SubLayout(
            instance_name=inst.instance_name,
            sheet_name=inst.module.source_sheet or inst.module.name,
            box_x=sx, box_y=sy, box_w=sub_w, box_h=sub_h,
            ports=sub_ports,
        ))

    # Build wires with sorted endpoints (outs first, then ins)
    wires: list[Wire] = []
    for name, positions in port_positions.items():
        if len(positions) >= 2:
            outs = [p for p in positions if p[2] == "output"]
            ins = [p for p in positions if p[2] == "input"]
            wires.append(Wire(name=name, endpoints=outs + ins))

    return HierarchyLayout(
        top_name=top_mod.name,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        wrap_x=wrap_x,
        wrap_y=wrap_y,
        wrapper_w=wrapper_w,
        wrapper_h=wrapper_h,
        top_inputs=top_inputs,
        top_outputs=top_outputs,
        sub_layouts=sub_layouts,
        wires=wires,
    )
