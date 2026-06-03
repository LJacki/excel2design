"""SVG block-diagram generator per SPEC §4.3.

Renders a Module as a self-contained, light-themed SVG document using
xml.etree.ElementTree (no Jinja2). The output is byte-stable: no timestamps,
no random sources, deterministic port ordering, LF line endings, no trailing
whitespace, all coordinates are integers.

Public API:
    generate_svg(module) -> str
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from excel2design.core.models import Module, Port


# ---- Layout constants (all integer px) --------------------------------------

FONT_FAMILY = "sans-serif"
FONT_SIZE = 12
LABEL_GAP = 6          # gap between port tick and label text
ROW_HEIGHT = 22        # vertical spacing per port row
SIDE_PAD = 16          # padding inside module on each side
TOP_HEADER = 30        # height of the module-name band
BODY_PAD_TOP = 12
BODY_PAD_BOTTOM = 12
INOUT_STRIP = 30       # height of the inout strip below the body
MIN_CANVAS_W = 360
MIN_CANVAS_H = 160
CORNER_RADIUS = 8

# Label width budget for "name + bit-width". We measure roughly with a fixed
# character budget per port label and choose the canvas width from the longest.
AVG_CHAR_PX = 7        # rough average glyph width for sans-serif @ 12px
LABEL_BUDGET_PADDING = 8  # extra pixels around the longest label

# Light-theme palette
COLOR_BG = "#FFFFFF"
COLOR_STROKE = "#888888"
COLOR_TEXT = "#222222"
COLOR_MUTED = "#666666"


# ---- Width formatting helpers -----------------------------------------------

def _width_str(p: Port) -> str:
    """Return the bit-width string for label rendering.

    Rules (matching diagram_html.PortView):
      * 1-bit → omitted (empty string)
      * fixed width N (>1) → "[MSB:0]"   e.g. 8 → "[7:0]"
      * parameterised width W → "[W-1:0]" e.g. DATA_WIDTH → "[DATA_WIDTH-1:0]"
    """
    if p.width.is_parameter:
        if p.width.raw == "1":
            return ""  # shouldn't happen, but stay safe
        return f"[{p.width.raw}-1:0]"
    # P0-3 fix: tolerate msb=None (default 1-bit from blank cell) — mirrors
    # PortWidth.to_verilog() so all 4 outputs handle 1-bit consistently.
    if p.width.msb is None or p.width.msb == 0:
        return ""
    return f"[{p.width.msb}:0]"


def _label_text(p: Port) -> str:
    """Port label = name + bit-width (width omitted for 1-bit)."""
    w = _width_str(p)
    return f"{p.name}{w}"


def _label_width(text: str) -> int:
    """Rough integer label width in pixels.

    We use a fixed average character width; this is intentionally a coarse
    estimate because pixel-perfect font metrics would require a font shaper
    dependency. SPEC §4.3 only mandates a sans-serif font, not exact metrics.
    """
    return max(1, len(text)) * AVG_CHAR_PX


# ---- Layout computation -----------------------------------------------------

class _Layout:
    """Pre-computed integer coordinates for one Module."""

    def __init__(self, module: Module) -> None:
        self.module = module
        self.inputs = module.inputs()
        self.outputs = module.outputs()
        self.inouts = module.inouts()

        # Longest input / output label determines left/right half-width.
        self.max_in_w = max((_label_width(_label_text(p)) for p in self.inputs), default=0)
        self.max_out_w = max((_label_width(_label_text(p)) for p in self.outputs), default=0)

        # Body interior: the part between the two side pads. We split it so
        # that input + output labels both fit on their side of the rect.
        # If a side has no ports, give it a small nominal width.
        left_half = self.max_in_w + SIDE_PAD + LABEL_GAP + 12
        right_half = self.max_out_w + SIDE_PAD + LABEL_GAP + 12
        body_w = max(left_half + right_half, MIN_CANVAS_W - 2 * SIDE_PAD)

        # Body height: tall enough for max(input, output) rows.
        n_rows = max(len(self.inputs), len(self.outputs), 1)
        body_h = BODY_PAD_TOP + n_rows * ROW_HEIGHT + BODY_PAD_BOTTOM

        # Canvas size.
        inout_strip_h = INOUT_STRIP if self.inouts else 0
        canvas_w = max(body_w + 2 * SIDE_PAD, MIN_CANVAS_W)
        canvas_h = max(TOP_HEADER + body_h + inout_strip_h, MIN_CANVAS_H)

        # Module rectangle (rounded). Insets from the canvas.
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.body_x = SIDE_PAD
        self.body_y = SIDE_PAD + TOP_HEADER
        self.body_w = canvas_w - 2 * SIDE_PAD
        self.body_h = body_h
        self.inout_strip_h = inout_strip_h
        self.inout_y = self.body_y + self.body_h

        # Edge positions (input port tick on left edge, output on right).
        self.left_x = self.body_x
        self.right_x = self.body_x + self.body_w
        # First row baseline.
        self.row_top = self.body_y + BODY_PAD_TOP + ROW_HEIGHT // 2


# ---- Element construction helpers -------------------------------------------

def _tick_and_label(
    parent: ET.Element,
    *,
    side: str,
    cx: int,
    cy: int,
    text: str,
    text_anchor: str,
    text_x: int,
) -> None:
    """Append a port tick (short horizontal line) and label to `parent`."""
    if side == "left":
        # Tick points rightward into the body.
        x1, x2 = cx - 8, cx
    else:
        # Tick points leftward into the body (port exits from right edge).
        x1, x2 = cx, cx + 8
    ET.SubElement(parent, "line", {
        "x1": str(x1), "y1": str(cy),
        "x2": str(x2), "y2": str(cy),
        "stroke": COLOR_STROKE, "stroke-width": "1",
    })
    # Small port pin (square) at the connection point.
    ET.SubElement(parent, "rect", {
        "x": str(x2 - 2), "y": str(cy - 2),
        "width": "4", "height": "4",
        "fill": COLOR_BG, "stroke": COLOR_STROKE, "stroke-width": "1",
    })
    # Label
    t = ET.SubElement(parent, "text", {
        "x": str(text_x), "y": str(cy + 4),  # +4 to vertically center on baseline
        "font-family": FONT_FAMILY,
        "font-size": str(FONT_SIZE),
        "fill": COLOR_TEXT,
        "text-anchor": text_anchor,
    })
    t.text = text


# ---- Public API -------------------------------------------------------------

def generate_svg(module: Module) -> str:
    """Render `module` as a self-contained SVG string (declaration included).

    Byte-stable: same Module in → same bytes out, every time.
    """
    if not isinstance(module, Module):  # pragma: no cover - defensive
        raise TypeError(f"generate_svg expects Module, got {type(module).__name__}")

    layout = _Layout(module)

    # Root <svg> element.
    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "version": "1.1",
        "width": str(layout.canvas_w),
        "height": str(layout.canvas_h),
        "viewBox": f"0 0 {layout.canvas_w} {layout.canvas_h}",
    })

    # White background.
    ET.SubElement(svg, "rect", {
        "x": "0", "y": "0",
        "width": str(layout.canvas_w),
        "height": str(layout.canvas_h),
        "fill": COLOR_BG,
    })

    # Module name (centered above the body).
    title = ET.SubElement(svg, "text", {
        "x": str(layout.canvas_w // 2),
        "y": str(SIDE_PAD + TOP_HEADER // 2 + 6),
        "font-family": FONT_FAMILY,
        "font-size": str(FONT_SIZE + 2),
        "font-weight": "bold",
        "fill": COLOR_TEXT,
        "text-anchor": "middle",
    })
    title.text = module.name

    # Module body (rounded rect, rx=8 per SPEC §4.3).
    ET.SubElement(svg, "rect", {
        "x": str(layout.body_x),
        "y": str(layout.body_y),
        "width": str(layout.body_w),
        "height": str(layout.body_h),
        "rx": str(CORNER_RADIUS),
        "ry": str(CORNER_RADIUS),
        "fill": COLOR_BG,
        "stroke": COLOR_STROKE,
        "stroke-width": "1",
    })

    # Input ports (left side, stacked vertically in Excel order).
    for i, p in enumerate(layout.inputs):
        cy = layout.row_top + i * ROW_HEIGHT
        # Label is right-anchored so it ends at the edge.
        text_x = layout.left_x - LABEL_GAP - 8
        _tick_and_label(
            svg,
            side="left",
            cx=layout.left_x,
            cy=cy,
            text=_label_text(p),
            text_anchor="end",
            text_x=text_x,
        )

    # Output ports (right side, stacked vertically in Excel order).
    for i, p in enumerate(layout.outputs):
        cy = layout.row_top + i * ROW_HEIGHT
        # Label is left-anchored so it starts past the edge.
        text_x = layout.right_x + LABEL_GAP + 8
        _tick_and_label(
            svg,
            side="right",
            cx=layout.right_x,
            cy=cy,
            text=_label_text(p),
            text_anchor="start",
            text_x=text_x,
        )

    # Inout ports (bottom, distributed horizontally).
    if layout.inouts:
        # Center the inout row inside the body width.
        n = len(layout.inouts)
        slot = layout.body_w // max(n, 1)
        base_y = layout.inout_y + INOUT_STRIP // 2
        for i, p in enumerate(layout.inouts):
            cx = layout.body_x + slot * i + slot // 2
            # Tick points downward from the body bottom edge.
            ET.SubElement(svg, "line", {
                "x1": str(cx), "y1": str(layout.inout_y),
                "x2": str(cx), "y2": str(base_y),
                "stroke": COLOR_STROKE, "stroke-width": "1",
            })
            ET.SubElement(svg, "rect", {
                "x": str(cx - 2), "y": str(layout.inout_y - 2),
                "width": "4", "height": "4",
                "fill": COLOR_BG, "stroke": COLOR_STROKE, "stroke-width": "1",
            })
            t = ET.SubElement(svg, "text", {
                "x": str(cx),
                "y": str(base_y + FONT_SIZE + 4),
                "font-family": FONT_FAMILY,
                "font-size": str(FONT_SIZE),
                "fill": COLOR_TEXT,
                "text-anchor": "middle",
            })
            t.text = _label_text(p)

    # If there are no ports at all, place a muted empty-state marker.
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

    # Serialise. ElementTree uses LF in tostring (it inserts \n between tags).
    raw = ET.tostring(svg, encoding="unicode")
    # Prepend the XML declaration (on its own line) — SPEC requires a complete
    # self-contained SVG file, declaration included.
    out = '<?xml version="1.0" encoding="UTF-8"?>\n' + raw + "\n"
    return _normalise(out)


def _normalise(s: str) -> str:
    """Enforce LF line endings and strip trailing whitespace per line."""
    out_lines = []
    for line in s.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        out_lines.append(line.rstrip())
    return "\n".join(out_lines)
