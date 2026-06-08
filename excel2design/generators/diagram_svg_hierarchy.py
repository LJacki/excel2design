"""Hierarchical SVG block diagram generator (v0.5, SPEC §18).

Draws wrapper rectangle with nested submodule rectangles and connection lines.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from excel2design.core.models import Module, Project, Port
from excel2design.core.connection import match_port, ConnectionKind
from excel2design.utils.clock_colors import clock_color

# Layout constants
FONT_FAMILY = "sans-serif"
FONT_SIZE = 10
TITLE_SIZE = 14
SUB_TITLE_SIZE = 11
WRAPPER_PAD = 40
SUB_PAD = 16
SUB_SPACING = 20
PORT_ROW_H = 16
ARROW_LEN = 20
CORNER_R = 8
MIN_W = 600

COLOR_BG = "#FFFFFF"
COLOR_STROKE = "#888888"
COLOR_SUB_STROKE = "#BBBBBB"
COLOR_TEXT = "#222222"
COLOR_MUTED = "#666666"
COLOR_WIRE = "#999999"


def _sub_rect_w(mod: Module) -> int:
    """Estimate submodule rectangle width based on port names."""
    max_name = max((len(p.name) for p in mod.ports), default=0)
    return max(max_name * 7 + 40, 120)


def _sub_rect_h(mod: Module) -> int:
    """Estimate submodule rectangle height."""
    return max(len(mod.ports) * PORT_ROW_H + 30, 50)


def generate_svg_hierarchy(project: Project, top_sheet: str) -> str:
    """Render a hierarchical SVG diagram with nested submodules."""
    top_mod = project.modules.get(top_sheet)
    if top_mod is None:
        return ""

    instances = project.get_submodules(top_sheet)
    n_inst = len(instances)

    # Layout calculation
    sub_widths = [_sub_rect_w(inst.module) for inst in instances]
    sub_heights = [_sub_rect_h(inst.module) for inst in instances]

    # Arrange submodules in rows (max 3 per row)
    cols = min(n_inst, 3) if n_inst > 0 else 1
    rows = (n_inst + cols - 1) // cols if n_inst > 0 else 1
    max_w = max(sub_widths) if sub_widths else 120
    max_h = max(sub_heights) if sub_heights else 60

    # Wrapper size
    inner_w = cols * (max_w + SUB_SPACING) + SUB_SPACING
    inner_h = rows * (max_h + SUB_SPACING) + SUB_SPACING + 30  # +30 for title
    wrapper_w = inner_w + WRAPPER_PAD * 2
    wrapper_h = inner_h + WRAPPER_PAD * 2

    # Wrapper port area
    n_in = len(top_mod.inputs())
    n_out = len(top_mod.outputs())
    wrapper_h = max(wrapper_h, max(n_in, n_out) * PORT_ROW_H + WRAPPER_PAD * 2)

    canvas_w = wrapper_w + 280  # room for port labels on both sides
    canvas_h = wrapper_h + 60

    # Build SVG
    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "version": "1.1",
        "width": str(canvas_w),
        "height": str(canvas_h),
        "viewBox": f"0 0 {canvas_w} {canvas_h}",
    })
    ET.SubElement(svg, "rect", {
        "x": "0", "y": "0", "width": str(canvas_w), "height": str(canvas_h),
        "fill": COLOR_BG,
    })

    wrapper_x = 140
    wrapper_y = 30

    # Title
    t = ET.SubElement(svg, "text", {
        "x": str(wrapper_x + wrapper_w // 2), "y": str(wrapper_y - 8),
        "font-family": FONT_FAMILY, "font-size": str(TITLE_SIZE),
        "font-weight": "bold", "fill": COLOR_TEXT, "text-anchor": "middle",
    })
    t.text = top_mod.name

    # Wrapper rectangle
    ET.SubElement(svg, "rect", {
        "x": str(wrapper_x), "y": str(wrapper_y),
        "width": str(wrapper_w), "height": str(wrapper_h),
        "rx": str(CORNER_R), "ry": str(CORNER_R),
        "fill": COLOR_BG, "stroke": COLOR_STROKE, "stroke-width": "2",
    })

    # Input ports on left
    for i, p in enumerate(top_mod.inputs()):
        py = wrapper_y + WRAPPER_PAD + i * PORT_ROW_H
        # Label
        t = ET.SubElement(svg, "text", {
            "x": str(wrapper_x - 8), "y": str(py + 11),
            "font-family": FONT_FAMILY, "font-size": str(FONT_SIZE),
            "fill": clock_color(p.clock, is_input=True), "text-anchor": "end",
        })
        t.text = p.name
        # Arrow
        ET.SubElement(svg, "line", {
            "x1": str(wrapper_x - ARROW_LEN - 4), "y1": str(py + 6),
            "x2": str(wrapper_x), "y2": str(py + 6),
            "stroke": clock_color(p.clock, is_input=True), "stroke-width": "1",
        })

    # Output ports on right
    for i, p in enumerate(top_mod.outputs()):
        py = wrapper_y + WRAPPER_PAD + i * PORT_ROW_H
        t = ET.SubElement(svg, "text", {
            "x": str(wrapper_x + wrapper_w + 8), "y": str(py + 11),
            "font-family": FONT_FAMILY, "font-size": str(FONT_SIZE),
            "fill": clock_color(p.clock, is_input=False), "text-anchor": "start",
        })
        t.text = p.name
        ET.SubElement(svg, "line", {
            "x1": str(wrapper_x + wrapper_w), "y1": str(py + 6),
            "x2": str(wrapper_x + wrapper_w + ARROW_LEN + 4), "y2": str(py + 6),
            "stroke": clock_color(p.clock, is_input=False), "stroke-width": "1",
        })

    # Submodules
    for idx, inst in enumerate(instances):
        row = idx // cols
        col = idx % cols
        sx = wrapper_x + SUB_SPACING + col * (max_w + SUB_SPACING)
        sy = wrapper_y + SUB_SPACING + 24 + row * (max_h + SUB_SPACING)

        # Submodule rectangle
        ET.SubElement(svg, "rect", {
            "x": str(sx), "y": str(sy),
            "width": str(max_w), "height": str(max_h),
            "rx": "4", "ry": "4",
            "fill": COLOR_BG, "stroke": COLOR_SUB_STROKE, "stroke-width": "1",
        })

        # Submodule name
        t = ET.SubElement(svg, "text", {
            "x": str(sx + max_w // 2), "y": str(sy + 16),
            "font-family": FONT_FAMILY, "font-size": str(SUB_TITLE_SIZE),
            "font-weight": "bold", "fill": COLOR_TEXT, "text-anchor": "middle",
        })
        t.text = inst.instance_name

        # Submodule ports
        for pi, p in enumerate(inst.module.ports):
            py = sy + 24 + pi * PORT_ROW_H
            if py > sy + max_h - 4:
                break
            color = clock_color(p.clock, is_input=(p.direction.value == "input"))
            # Direction indicator
            arrow = "← " if p.direction.value == "input" else " →"
            label = f"{p.name}{arrow}" if p.direction.value == "input" else f" {arrow}{p.name}"
            align = "start"
            tx = sx + 6
            if p.direction.value == "output":
                align = "end"
                tx = sx + max_w - 6
            t = ET.SubElement(svg, "text", {
                "x": str(tx), "y": str(py + 10),
                "font-family": FONT_FAMILY, "font-size": "9",
                "fill": color, "text-anchor": align,
            })
            t.text = label

    raw = ET.tostring(svg, encoding="unicode")
    out = '<?xml version="1.0" encoding="UTF-8"?>\n' + raw + "\n"
    return _normalise(out)


def _normalise(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.replace("\r\n", "\n").split("\n"))
