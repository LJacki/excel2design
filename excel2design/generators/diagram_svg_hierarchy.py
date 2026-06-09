"""Hierarchical SVG block diagram with inter-submodule connection lines."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict

from excel2design.core.models import Module, Project
from excel2design.utils.clock_colors import clock_color

FONT_FAMILY = "sans-serif"
FONT_SIZE = 10
TITLE_SIZE = 14
SUB_TITLE_SIZE = 11
WRAPPER_PAD = 50
SUB_PAD = 16
SUB_SPACING = 24
PORT_ROW_H = 14
ARROW_LEN = 28
CORNER_R = 8

COLOR_BG = "#FFFFFF"
COLOR_STROKE = "#888888"
COLOR_SUB_STROKE = "#BBBBBB"
COLOR_TEXT = "#222222"
COLOR_WIRE = "#999999"


def _sub_w(mod: Module) -> int:
    return max(max((len(p.name) for p in mod.ports), default=0) * 8 + 40, 150)

def _sub_h(mod: Module) -> int:
    return max(len(mod.ports) * PORT_ROW_H + 36, 60)


def generate_svg_hierarchy(project: Project, top_sheet: str) -> str:
    top_mod = project.modules.get(top_sheet)
    if top_mod is None:
        return ""

    instances = project.get_submodules(top_sheet)
    n_inst = len(instances)

    sub_widths = [_sub_w(inst.module) for inst in instances]
    sub_heights = [_sub_h(inst.module) for inst in instances]
    cols = min(n_inst, 3) if n_inst > 0 else 1
    rows = (n_inst + cols - 1) // cols if n_inst > 0 else 1
    max_w = max(sub_widths) if sub_widths else 200
    max_h = max(sub_heights) if sub_heights else 80

    inner_w = cols * (max_w + SUB_SPACING) + SUB_SPACING
    inner_h = rows * (max_h + SUB_SPACING) + SUB_SPACING + 30

    n_in = len(top_mod.inputs())
    n_out = len(top_mod.outputs())
    wrapper_w = inner_w + WRAPPER_PAD * 2
    wrapper_h = max(inner_h + WRAPPER_PAD * 2, max(n_in, n_out) * PORT_ROW_H + WRAPPER_PAD * 2)

    canvas_w = wrapper_w + 320
    canvas_h = wrapper_h + 80
    wrap_x, wrap_y = 160, 40

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "version": "1.1",
        "width": str(canvas_w), "height": str(canvas_h),
        "viewBox": f"0 0 {canvas_w} {canvas_h}",
    })
    ET.SubElement(svg, "rect", {"x": "0", "y": "0", "width": str(canvas_w), "height": str(canvas_h), "fill": COLOR_BG})
    tt = ET.SubElement(svg, "text", {"x": str(wrap_x + wrapper_w // 2), "y": str(wrap_y - 8),
                                      "font-family": FONT_FAMILY, "font-size": str(TITLE_SIZE),
                                      "font-weight": "bold", "fill": COLOR_TEXT, "text-anchor": "middle"})
    tt.text = top_mod.name

    ET.SubElement(svg, "rect", {"x": str(wrap_x), "y": str(wrap_y), "width": str(wrapper_w), "height": str(wrapper_h),
                                 "rx": str(CORNER_R), "fill": COLOR_BG, "stroke": COLOR_STROKE, "stroke-width": "2"})

    # Parent ports
    parent_ports = {p.name for p in top_mod.ports}
    for i, p in enumerate(top_mod.inputs()):
        py = wrap_y + WRAPPER_PAD + i * PORT_ROW_H
        ET.SubElement(svg, "text", {"x": str(wrap_x - 8), "y": str(py + 10), "font-size": "10",
                                     "fill": clock_color(p.clock, is_input=True), "text-anchor": "end"}).text = p.name
        ET.SubElement(svg, "line", {"x1": str(wrap_x - ARROW_LEN - 4), "y1": str(py + 5),
                                     "x2": str(wrap_x), "y2": str(py + 5),
                                     "stroke": clock_color(p.clock, is_input=True), "stroke-width": "1.5"})
    for i, p in enumerate(top_mod.outputs()):
        py = wrap_y + WRAPPER_PAD + i * PORT_ROW_H
        ET.SubElement(svg, "text", {"x": str(wrap_x + wrapper_w + 8), "y": str(py + 10), "font-size": "10",
                                     "fill": clock_color(p.clock, is_input=False), "text-anchor": "start"}).text = p.name
        ET.SubElement(svg, "line", {"x1": str(wrap_x + wrapper_w), "y1": str(py + 5),
                                     "x2": str(wrap_x + wrapper_w + ARROW_LEN + 4), "y2": str(py + 5),
                                     "stroke": clock_color(p.clock, is_input=False), "stroke-width": "1.5"})

    # Track port positions for connection lines
    port_positions: dict[str, list[tuple[int, int, str]]] = defaultdict(list)  # port_name -> [(x, y, direction)]

    for idx, inst in enumerate(instances):
        row, col = idx // cols, idx % cols
        sx = wrap_x + SUB_SPACING + col * (max_w + SUB_SPACING)
        sy = wrap_y + SUB_SPACING + 28 + row * (max_h + SUB_SPACING)

        ET.SubElement(svg, "rect", {"x": str(sx), "y": str(sy), "width": str(max_w), "height": str(max_h),
                                     "rx": "4", "fill": COLOR_BG, "stroke": COLOR_SUB_STROKE, "stroke-width": "1"})
        t = ET.SubElement(svg, "text", {"x": str(sx + max_w // 2), "y": str(sy + 14),
                                         "font-size": str(SUB_TITLE_SIZE), "font-weight": "bold",
                                         "fill": COLOR_TEXT, "text-anchor": "middle"})
        t.text = inst.instance_name

        for pi, p in enumerate(inst.module.ports):
            py = sy + 22 + pi * PORT_ROW_H
            if py > sy + max_h - 4:
                break
            color = clock_color(p.clock, is_input=(p.direction.value == "input"))
            if p.direction.value == "input":
                tx, align = sx + 6, "start"
                label = f"← {p.name}"
                port_pos = (sx, py + 6)  # left edge
            else:
                tx, align = sx + max_w - 6, "end"
                label = f"{p.name} →"
                port_pos = (sx + max_w, py + 6)  # right edge
            ET.SubElement(svg, "text", {"x": str(tx), "y": str(py + 9), "font-size": "9",
                                         "fill": color, "text-anchor": align}).text = label
            if p.name not in parent_ports:
                port_positions[p.name].append((*port_pos, p.direction.value))

    # Draw internal wire connections
    for port_name, positions in port_positions.items():
        if len(positions) >= 2:
            # Sort: outputs first (source), then inputs (sink)
            outs = [p for p in positions if p[2] == "output"]
            ins = [p for p in positions if p[2] == "input"]
            all_pts = outs + ins
            for j in range(len(all_pts) - 1):
                x1, y1, _ = all_pts[j]
                x2, y2, _ = all_pts[j + 1]
                ET.SubElement(svg, "line", {
                    "x1": str(x1), "y1": str(y1), "x2": str(x2), "y2": str(y2),
                    "stroke": COLOR_WIRE, "stroke-width": "1", "stroke-dasharray": "4,2",
                })
                # Label at midpoint
                mx, my = (x1 + x2) // 2, (y1 + y2) // 2
                lt = ET.SubElement(svg, "text", {"x": str(mx), "y": str(my - 4), "font-size": "8",
                                                  "fill": COLOR_WIRE, "text-anchor": "middle"})
                lt.text = port_name

    raw = ET.tostring(svg, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + raw + "\n"
