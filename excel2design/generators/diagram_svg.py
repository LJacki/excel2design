"""SVG block-diagram generator per SPEC §4.3 (v0.4).

v0.4.1: clock-domain colors + multi-line parameters.
v0.5.1 (P0-4 fix): marker ids use ``hashlib.md5`` (deterministic) instead of
built-in ``hash()`` so SVG output is byte-stable across processes.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET

from excel2design.core.models import Module, Port
from excel2design.utils.clock_colors import clock_color


def _stable_marker_token(ck: str) -> str:
    """Deterministic 8-hex-char token for a clock name (P0-4 fix)."""
    return hashlib.md5(ck.encode("utf-8")).hexdigest()[:8]


# ---- Layout constants -------------------------------------------------------
FONT_FAMILY = "sans-serif"
FONT_SIZE = 12
LABEL_GAP = 8
ARROW_LENGTH = 28
ROW_HEIGHT = 24
SIDE_PAD = 20
TOP_HEADER = 34
BODY_PAD_TOP = 10
BODY_PAD_BOTTOM = 10
INOUT_STRIP = 32
MIN_CANVAS_W = 400
MIN_CANVAS_H = 180
CORNER_RADIUS = 8
AVG_CHAR_PX = 7

COLOR_BG = "#FFFFFF"
COLOR_STROKE = "#888888"
COLOR_TEXT = "#222222"
COLOR_MUTED = "#666666"
# v0.6 Phase 13: dashed border colour for interface-port group container.
COLOR_INTERFACE = "#85C1E9"
COLOR_ARROW_IN = "#2E86C1"
COLOR_ARROW_OUT = "#E74C3C"
COLOR_ARROW_INOUT = "#9B59B6"
# v0.6 Phase 15.4: warning-tone for inout/bidirectional connections
# (multi-driver capable). Distinct from the regular inout colour so the
# viewer can quickly spot ports that may have multiple drivers.
COLOR_INOUT_WARN = "#D35400"


def _width_str(p: Port) -> str:
    if p.width.is_parameter:
        if p.width.raw == "1":
            return ""
        return f"[{p.width.raw}-1:0]"
    if p.width.msb is None or p.width.msb == 0:
        return ""
    return f"[{p.width.msb}:0]"


def _label_text(p: Port) -> str:
    # v0.6 Phase 12: append unpacked array dims (e.g. "data[7:0]") to the label.
    array_suffix = p.to_array_dim_verilog()
    return f"{p.name}{_width_str(p)}{array_suffix}"


def _label_width(text: str) -> int:
    return max(1, len(text)) * AVG_CHAR_PX


# ---- Layout ----------------------------------------------------------------

class _Layout:
    def __init__(self, module: Module) -> None:
        self.module = module
        self.inputs = module.inputs()
        self.outputs = module.outputs()
        self.inouts = module.inouts()

        self.max_in_w = max((_label_width(_label_text(p)) for p in self.inputs), default=0)
        self.max_out_w = max((_label_width(_label_text(p)) for p in self.outputs), default=0)

        body_w = max(self.max_in_w + self.max_out_w + ARROW_LENGTH * 2 + LABEL_GAP * 4 + SIDE_PAD * 2,
                     MIN_CANVAS_W - LABEL_GAP * 4, 200)

        n_rows = max(len(self.inputs), len(self.outputs), 1)
        body_h = BODY_PAD_TOP + n_rows * ROW_HEIGHT + BODY_PAD_BOTTOM

        inout_strip_h = INOUT_STRIP if self.inouts else 0

        left_margin = self.max_in_w + LABEL_GAP + ARROW_LENGTH + 12
        right_margin = self.max_out_w + LABEL_GAP + ARROW_LENGTH + 12
        canvas_w = max(left_margin + body_w + right_margin, MIN_CANVAS_W)
        canvas_h = max(TOP_HEADER + body_h + inout_strip_h + 12, MIN_CANVAS_H)

        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.body_x = left_margin
        self.body_y = TOP_HEADER + 6
        self.body_w = body_w
        self.body_h = body_h
        self.inout_strip_h = inout_strip_h
        self.inout_y = self.body_y + self.body_h
        self.left_x = self.body_x
        self.right_x = self.body_x + self.body_w
        self.row_top = self.body_y + BODY_PAD_TOP + ROW_HEIGHT // 2


# ---- Markers (per clock domain) -------------------------------------------

def _add_markers(svg: ET.Element, module: Module) -> None:
    """Add <defs><marker> — input+output marker per clock domain."""
    clocks = set()
    for p in module.ports:
        if p.clock:
            clocks.add(p.clock)
    defs = ET.SubElement(svg, "defs")
    for ck in sorted(clocks):
        for is_in, color in [(True, clock_color(ck, is_input=True)),
                               (False, clock_color(ck, is_input=False))]:
            sufx = "i" if is_in else "o"
            mid = f"m_{_stable_marker_token(ck)}_{sufx}"
            marker = ET.SubElement(defs, "marker", {
                "id": mid,
                "markerWidth": "8", "markerHeight": "6",
                "refX": "8", "refY": "3", "orient": "auto",
            })
            ET.SubElement(marker, "path", {
                "d": "M 0,0 L 8,3 L 0,6 Z",
                "fill": color,
            })
    # Neutral marker
    for sufx, color in [("i", "#888888"), ("o", "#888888")]:
        nmid = f"m_neutral_{sufx}"
        nmarker = ET.SubElement(defs, "marker", {
            "id": nmid,
            "markerWidth": "8", "markerHeight": "6",
            "refX": "8", "refY": "3", "orient": "auto",
        })
        ET.SubElement(nmarker, "path", {
            "d": "M 0,0 L 8,3 L 0,6 Z",
            "fill": color,
        })


def _marker_id(ck: str | None, is_input: bool) -> str:
    sufx = "i" if is_input else "o"
    if ck:
        return f"m_{_stable_marker_token(ck)}_{sufx}"
    return f"m_neutral_{sufx}"


def _port_row(parent, *, y, label_text, label_x, label_anchor,
              arrow_x1, arrow_x2, clock_val, is_input):
    color = clock_color(clock_val, is_input=is_input)
    mid = _marker_id(clock_val, is_input)
    t = ET.SubElement(parent, "text", {
        "x": str(label_x), "y": str(y + 4),
        "font-family": FONT_FAMILY, "font-size": str(FONT_SIZE),
        "fill": COLOR_TEXT, "text-anchor": label_anchor,
    })
    t.text = label_text
    arrow = ET.SubElement(parent, "line", {
        "x1": str(arrow_x1), "y1": str(y),
        "x2": str(arrow_x2), "y2": str(y),
        "stroke": color, "stroke-width": "1.5",
    })
    arrow.set("marker-end", f"url(#{mid})")


# ---- Public API ------------------------------------------------------------

def generate_svg(module: Module) -> str:
    layout = _Layout(module)

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "version": "1.1",
        "width": str(layout.canvas_w),
        "height": str(layout.canvas_h),
        "viewBox": f"0 0 {layout.canvas_w} {layout.canvas_h}",
    })
    ET.SubElement(svg, "rect", {
        "x": "0", "y": "0",
        "width": str(layout.canvas_w), "height": str(layout.canvas_h),
        "fill": COLOR_BG,
    })

    _add_markers(svg, module)

    # Module name
    t = ET.SubElement(svg, "text", {
        "x": str(layout.canvas_w // 2), "y": str(TOP_HEADER // 2 + 8),
        "font-family": FONT_FAMILY, "font-size": "14", "font-weight": "bold",
        "fill": COLOR_TEXT, "text-anchor": "middle",
    })
    t.text = module.name

    # Module body
    ET.SubElement(svg, "rect", {
        "x": str(layout.body_x), "y": str(layout.body_y),
        "width": str(layout.body_w), "height": str(layout.body_h),
        "rx": str(CORNER_RADIUS), "ry": str(CORNER_RADIUS),
        "fill": COLOR_BG, "stroke": COLOR_STROKE, "stroke-width": "1.5",
    })

    # Input ports
    for i, p in enumerate(layout.inputs):
        y = layout.row_top + i * ROW_HEIGHT
        label = _label_text(p)
        label_x = layout.left_x - LABEL_GAP - ARROW_LENGTH
        ax1 = layout.left_x - ARROW_LENGTH
        ax2 = layout.left_x
        _port_row(svg, y=y, label_text=label, label_x=label_x,
                  label_anchor="end", arrow_x1=ax1, arrow_x2=ax2,
                  clock_val=p.clock, is_input=True)

    # Output ports
    for i, p in enumerate(layout.outputs):
        y = layout.row_top + i * ROW_HEIGHT
        label = _label_text(p)
        label_x = layout.right_x + LABEL_GAP + ARROW_LENGTH
        ax1 = layout.right_x
        ax2 = layout.right_x + ARROW_LENGTH
        _port_row(svg, y=y, label_text=label, label_x=label_x,
                  label_anchor="start", arrow_x1=ax1, arrow_x2=ax2,
                  clock_val=p.clock, is_input=False)

    # Inout ports
    if layout.inouts:
        n = len(layout.inouts)
        slot = layout.body_w // max(n, 1)
        base_y = layout.inout_y + INOUT_STRIP // 2
        # v0.6 Phase 15.4: collect inout x-centres for the optional
        # group rect (drawn when ≥2 inout ports — a hint that the
        # designer should double-check for multi-driver conflicts).
        inout_cx: list[int] = []
        for i, p in enumerate(layout.inouts):
            cx = layout.body_x + slot * i + slot // 2
            inout_cx.append(cx)
            label = _label_text(p)
            # v0.6 Phase 15.4: inout ports get a thicker line (2.5 vs 1.5)
            # and the warning-tone colour, signalling that the port is
            # bidirectional and may have multiple drivers.
            ET.SubElement(svg, "line", {
                "x1": str(cx), "y1": str(layout.inout_y),
                "x2": str(cx), "y2": str(base_y - 6),
                "stroke": COLOR_INOUT_WARN, "stroke-width": "2.5",
            })
            ET.SubElement(svg, "polygon", {
                "points": f"{cx-4},{base_y-2} {cx},{base_y-6} {cx+4},{base_y-2} {cx},{base_y+2}",
                "fill": COLOR_INOUT_WARN,
            })
            t = ET.SubElement(svg, "text", {
                "x": str(cx), "y": str(base_y + FONT_SIZE + 6),
                "font-family": FONT_FAMILY, "font-size": str(FONT_SIZE),
                "fill": COLOR_TEXT, "text-anchor": "middle",
            })
            t.text = label
        # v0.6 Phase 15.4: enclose ≥2 inout ports in a dashed warning
        # rect so the viewer knows to look for multi-driver hazards.
        if len(inout_cx) >= 2:
            min_cx = min(inout_cx)
            max_cx = max(inout_cx)
            pad = 6
            ET.SubElement(svg, "rect", {
                "x": str(min_cx - slot // 2 + pad // 2),
                "y": str(layout.inout_y - pad),
                "width": str(max_cx - min_cx + slot - pad),
                "height": str(INOUT_STRIP + 2 * pad),
                "fill": "none",
                "stroke": COLOR_INOUT_WARN,
                "stroke-width": "1.2",
                "stroke-dasharray": "3,2",
                "rx": "3", "ry": "3",
            })

    if not layout.inputs and not layout.outputs and not layout.inouts:
        t = ET.SubElement(svg, "text", {
            "x": str(layout.canvas_w // 2),
            "y": str(layout.body_y + layout.body_h // 2 + 4),
            "font-family": FONT_FAMILY, "font-size": str(FONT_SIZE),
            "fill": COLOR_MUTED, "text-anchor": "middle",
        })
        t.text = "(no ports)"

    # v0.6 Phase 13: dashed group container around interface ports.
    # A single dashed box is drawn around all is_interface=True ports
    # (across inputs, outputs, and inouts) for visual grouping.
    iface_ports = [p for p in module.ports if p.is_interface]
    if iface_ports:
        iface_names = {p.name for p in iface_ports}
        ys = []
        for i, p in enumerate(layout.inputs):
            if p.name in iface_names:
                ys.append(layout.row_top + i * ROW_HEIGHT)
        for i, p in enumerate(layout.outputs):
            if p.name in iface_names:
                ys.append(layout.row_top + i * ROW_HEIGHT)
        for i, p in enumerate(layout.inouts):
            if p.name in iface_names:
                ys.append(layout.inout_y + INOUT_STRIP // 2)
        if ys:
            pad = 8
            ET.SubElement(svg, "rect", {
                "x": str(layout.body_x + pad // 2),
                "y": str(min(ys) - ROW_HEIGHT // 2),
                "width": str(layout.body_w - pad),
                "height": str((max(ys) - min(ys)) + ROW_HEIGHT),
                "fill": "none",
                "stroke": COLOR_INTERFACE,
                "stroke-width": "1.2",
                "stroke-dasharray": "4,3",
                "rx": "4", "ry": "4",
            })

    raw = ET.tostring(svg, encoding="unicode")
    out = '<?xml version="1.0" encoding="UTF-8"?>\n' + raw + "\n"
    return _normalise(out)


def _normalise(s: str) -> str:
    out_lines = []
    for line in s.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        out_lines.append(line.rstrip())
    return "\n".join(out_lines)
