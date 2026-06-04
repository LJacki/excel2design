"""SVG block-diagram generator per SPEC §4.3 (v0.4).

Renders a Module as a self-contained, light-themed SVG document using
xml.etree.ElementTree (no Jinja2). The output is byte-stable: no timestamps,
no random sources, deterministic port ordering, LF line endings, no trailing
whitespace, all coordinates are integers.

v0.4 changes:
  * Directional arrows (SVG <marker> arrowheads) replace the old 8px-ticks
  * Input arrows: blue, pointing rightward from label to module edge
  * Output arrows: red, pointing rightward from module edge to label
  * Colors per SPEC §4.3: input #2E86C1, output #E74C3C, inout #9B59B6

Public API:
    generate_svg(module) -> str
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from excel2design.core.models import Module, Port


# ---- Layout constants (all integer px) --------------------------------------

FONT_FAMILY = "sans-serif"
FONT_SIZE = 12
LABEL_GAP = 8          # gap between port label and arrow start
ARROW_LENGTH = 28       # length of the directional arrow line
ROW_HEIGHT = 24        # vertical spacing per port row
SIDE_PAD = 20          # padding inside module on each side
TOP_HEADER = 34        # height of the module-name band
BODY_PAD_TOP = 14
BODY_PAD_BOTTOM = 14
INOUT_STRIP = 32       # height of the inout strip below the body
MIN_CANVAS_W = 400
MIN_CANVAS_H = 180
CORNER_RADIUS = 8

# Average glyph width for sans-serif @ 12px (coarse estimate)
AVG_CHAR_PX = 7
LABEL_BUDGET_PADDING = 12

# Light-theme palette
COLOR_BG = "#FFFFFF"
COLOR_STROKE = "#888888"
COLOR_TEXT = "#222222"
COLOR_MUTED = "#666666"
COLOR_ARROW_IN = "#2E86C1"
COLOR_ARROW_OUT = "#E74C3C"
COLOR_ARROW_INOUT = "#9B59B6"

# Arrowhead marker ID suffix
MARKER_IN = "_arrow_in"
MARKER_OUT = "_arrow_out"


# ---- Width formatting helpers -----------------------------------------------

def _width_str(p: Port) -> str:
    if p.width.is_parameter:
        if p.width.raw == "1":
            return ""
        return f"[{p.width.raw}-1:0]"
    if p.width.msb is None or p.width.msb == 0:
        return ""
    return f"[{p.width.msb}:0]"


def _label_text(p: Port) -> str:
    w = _width_str(p)
    return f"{p.name}{w}"


def _label_width(text: str) -> int:
    return max(1, len(text)) * AVG_CHAR_PX


# ---- Layout computation -----------------------------------------------------

class _Layout:
    """Pre-computed integer coordinates for one Module."""

    def __init__(self, module: Module) -> None:
        self.module = module
        self.inputs = module.inputs()
        self.outputs = module.outputs()
        self.inouts = module.inouts()

        # Longest input / output label determines canvas width.
        self.max_in_w = max((_label_width(_label_text(p)) for p in self.inputs), default=0)
        self.max_out_w = max((_label_width(_label_text(p)) for p in self.outputs), default=0)

        # Body width: label + arrow + gap on each side, centered module body
        label_zone = self.max_in_w + self.max_out_w + ARROW_LENGTH * 2 + LABEL_GAP * 4
        body_w = max(label_zone + SIDE_PAD * 2, MIN_CANVAS_W - LABEL_GAP * 4)
        body_w = max(body_w, 200)

        # Body height
        n_rows = max(len(self.inputs), len(self.outputs), 1)
        body_h = BODY_PAD_TOP + n_rows * ROW_HEIGHT + BODY_PAD_BOTTOM

        # Canvas size
        inout_strip_h = INOUT_STRIP if self.inouts else 0
        canvas_w = max(body_w + LABEL_GAP * 4 + self.max_in_w + self.max_out_w + ARROW_LENGTH * 2,
                       MIN_CANVAS_W)

        # Recalculate: left margin must fit input labels, right margin must fit output labels
        left_margin = self.max_in_w + LABEL_GAP + ARROW_LENGTH + 12
        right_margin = self.max_out_w + LABEL_GAP + ARROW_LENGTH + 12
        canvas_w = max(left_margin + body_w + right_margin, MIN_CANVAS_W)
        canvas_h = max(TOP_HEADER + body_h + inout_strip_h + 12, MIN_CANVAS_H)

        self.canvas_w = canvas_w
        self.canvas_h = canvas_h

        # Module rectangle position
        self.body_x = left_margin
        self.body_y = TOP_HEADER + 6
        self.body_w = body_w
        self.body_h = body_h
        self.inout_strip_h = inout_strip_h
        self.inout_y = self.body_y + self.body_h

        # Edge positions
        self.left_x = self.body_x
        self.right_x = self.body_x + self.body_w
        # First row baseline
        self.row_top = self.body_y + BODY_PAD_TOP + ROW_HEIGHT // 2


# ---- Arrow helpers -----------------------------------------------------------

def _add_markers(svg: ET.Element) -> None:
    """Add <defs><marker> arrowheads for input and output arrows."""
    defs = ET.SubElement(svg, "defs")
    for mid, color in [(MARKER_IN, COLOR_ARROW_IN), (MARKER_OUT, COLOR_ARROW_OUT)]:
        marker = ET.SubElement(defs, "marker", {
            "id": mid.lstrip("_"),
            "markerWidth": "8",
            "markerHeight": "6",
            "refX": "8",
            "refY": "3",
            "orient": "auto",
        })
        ET.SubElement(marker, "path", {
            "d": "M 0,0 L 8,3 L 0,6 Z",
            "fill": color,
        })


def _port_row(
    parent: ET.Element,
    *,
    side: str,
    y: int,
    label_text: str,
    label_x: int,
    label_anchor: str,
    arrow_x1: int,
    arrow_x2: int,
    arrow_color: str,
    marker_end: str | None,
) -> None:
    """Add a port label + directional arrow to `parent`."""
    # Label
    t = ET.SubElement(parent, "text", {
        "x": str(label_x),
        "y": str(y + 4),
        "font-family": FONT_FAMILY,
        "font-size": str(FONT_SIZE),
        "fill": COLOR_TEXT,
        "text-anchor": label_anchor,
    })
    t.text = label_text

    # Arrow line
    arrow = ET.SubElement(parent, "line", {
        "x1": str(arrow_x1),
        "y1": str(y),
        "x2": str(arrow_x2),
        "y2": str(y),
        "stroke": arrow_color,
        "stroke-width": "1.5",
    })
    if marker_end:
        arrow.set("marker-end", f"url(#{marker_end})")


# ---- Public API -------------------------------------------------------------

def generate_svg(module: Module) -> str:
    if not isinstance(module, Module):  # pragma: no cover - defensive
        raise TypeError(f"generate_svg expects Module, got {type(module).__name__}")

    layout = _Layout(module)

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "version": "1.1",
        "width": str(layout.canvas_w),
        "height": str(layout.canvas_h),
        "viewBox": f"0 0 {layout.canvas_w} {layout.canvas_h}",
    })

    # White background
    ET.SubElement(svg, "rect", {
        "x": "0", "y": "0",
        "width": str(layout.canvas_w),
        "height": str(layout.canvas_h),
        "fill": COLOR_BG,
    })

    # Arrowhead markers
    _add_markers(svg)

    # Module name
    title = ET.SubElement(svg, "text", {
        "x": str(layout.canvas_w // 2),
        "y": str(TOP_HEADER // 2 + 8),
        "font-family": FONT_FAMILY,
        "font-size": "14",
        "font-weight": "bold",
        "fill": COLOR_TEXT,
        "text-anchor": "middle",
    })
    title.text = module.name

    # Module body (rounded rect)
    ET.SubElement(svg, "rect", {
        "x": str(layout.body_x),
        "y": str(layout.body_y),
        "width": str(layout.body_w),
        "height": str(layout.body_h),
        "rx": str(CORNER_RADIUS),
        "ry": str(CORNER_RADIUS),
        "fill": COLOR_BG,
        "stroke": COLOR_STROKE,
        "stroke-width": "1.5",
    })

    # Parameters inside the box (if present)
    if module.parameters:
        param_text = ", ".join(f"{p.name}={p.value}" for p in module.parameters)
        pt = ET.SubElement(svg, "text", {
            "x": str(layout.body_x + layout.body_w // 2),
            "y": str(layout.body_y + layout.body_h + 8),
            "font-family": FONT_FAMILY,
            "font-size": "10",
            "fill": COLOR_MUTED,
            "text-anchor": "middle",
            "font-style": "italic",
        })
        pt.text = f"parameters: {param_text}"

    # Input ports (left side)
    for i, p in enumerate(layout.inputs):
        y = layout.row_top + i * ROW_HEIGHT
        label = _label_text(p)
        label_x = layout.left_x - LABEL_GAP - ARROW_LENGTH
        # Arrow: from label right-edge to module left-edge
        arrow_x1 = layout.left_x - ARROW_LENGTH
        arrow_x2 = layout.left_x
        _port_row(
            svg,
            side="left",
            y=y,
            label_text=label,
            label_x=label_x,
            label_anchor="end",
            arrow_x1=arrow_x1,
            arrow_x2=arrow_x2,
            arrow_color=COLOR_ARROW_IN,
            marker_end="arrow_in",
        )

    # Output ports (right side)
    for i, p in enumerate(layout.outputs):
        y = layout.row_top + i * ROW_HEIGHT
        label = _label_text(p)
        label_x = layout.right_x + LABEL_GAP + ARROW_LENGTH
        # Arrow: from module right-edge to label left-edge
        arrow_x1 = layout.right_x
        arrow_x2 = layout.right_x + ARROW_LENGTH
        _port_row(
            svg,
            side="right",
            y=y,
            label_text=label,
            label_x=label_x,
            label_anchor="start",
            arrow_x1=arrow_x1,
            arrow_x2=arrow_x2,
            arrow_color=COLOR_ARROW_OUT,
            marker_end="arrow_out",
        )

    # Inout ports (bottom)
    if layout.inouts:
        n = len(layout.inouts)
        slot = layout.body_w // max(n, 1)
        base_y = layout.inout_y + INOUT_STRIP // 2
        for i, p in enumerate(layout.inouts):
            cx = layout.body_x + slot * i + slot // 2
            label = _label_text(p)
            # Vertical line down from module bottom
            ET.SubElement(svg, "line", {
                "x1": str(cx), "y1": str(layout.inout_y),
                "x2": str(cx), "y2": str(base_y - 6),
                "stroke": COLOR_ARROW_INOUT, "stroke-width": "1.5",
            })
            # Small diamond for inout
            ET.SubElement(svg, "polygon", {
                "points": f"{cx-4},{base_y-2} {cx},{base_y-6} {cx+4},{base_y-2} {cx},{base_y+2}",
                "fill": COLOR_ARROW_INOUT,
            })
            t = ET.SubElement(svg, "text", {
                "x": str(cx),
                "y": str(base_y + FONT_SIZE + 6),
                "font-family": FONT_FAMILY,
                "font-size": str(FONT_SIZE),
                "fill": COLOR_TEXT,
                "text-anchor": "middle",
            })
            t.text = label

    # Empty-state marker
    if not layout.inputs and not layout.outputs and not layout.inouts:
        t = ET.SubElement(svg, "text", {
            "x": str(layout.canvas_w // 2),
            "y": str(layout.body_y + layout.body_h // 2 + 4),
            "font-family": FONT_FAMILY,
            "font-size": str(FONT_SIZE),
            "fill": COLOR_MUTED,
            "text-anchor": "middle",
        })
        t.text = "(no ports)"

    raw = ET.tostring(svg, encoding="unicode")
    out = '<?xml version="1.0" encoding="UTF-8"?>\n' + raw + "\n"
    return _normalise(out)


def _normalise(s: str) -> str:
    out_lines = []
    for line in s.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        out_lines.append(line.rstrip())
    return "\n".join(out_lines)
