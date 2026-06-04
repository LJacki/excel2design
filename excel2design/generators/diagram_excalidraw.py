"""Excalidraw block-diagram generator per SPEC §4.4 (v0.4).

Renders a Module as an Excalidraw scene JSON object using plain dicts
(no Jinja2). The output is byte-stable: deterministic port ordering, fixed
seeds, integer coordinates, LF line endings, no trailing whitespace.

v0.4 changes:
  * fontFamily: 5 (Helvetica / "Normal") — replaces fontFamily 1 (Virgil)
  * Dynamic text width based on label string length (est. 9px/char)
  * Directional arrow elements connecting port texts to module rectangle
  * Dynamic rectangle sizing based on port count and label widths
  * Arrow colors: input #2E86C1, output #E74C3C

Public API:
    generate_excalidraw(module) -> str
"""

from __future__ import annotations

import json

from excel2design.core.models import Module, Port


# ---- Layout constants (all integer px) --------------------------------------

# Base module rectangle position (upper-left corner)
RECT_X = 250
RECT_Y = 200
RECT_W = 300          # min width, may grow for long labels
RECT_H = 200          # min height, grows with port count

# Per-element dimensions
PORT_TEXT_H = 25       # height of a port-label text element
ARROW_LENGTH = 36      # length of directional arrow elements
NAME_TEXT_W = 200
NAME_TEXT_H = 28
ROW_SPACING = 30       # vertical spacing between ports
INOUT_SPACING = 90     # horizontal spacing for inout ports along the bottom
INOUT_GAP = 36         # distance from rect bottom to inout text

# Font settings (Helvetica / Normal — clean, not hand-drawn)
FONT_SIZE = 20
NAME_FONT_SIZE = 24
FONT_FAMILY = 5        # 5 = Helvetica / Normal (1 = Virgil / hand-drawn, deprecated)

# Colors
COLOR_ARROW_IN = "#2E86C1"
COLOR_ARROW_OUT = "#E74C3C"
COLOR_ARROW_INOUT = "#9B59B6"


# ---- Helpers ----------------------------------------------------------------

def _port_label(p: Port) -> str:
    if p.width.is_parameter:
        if p.width.raw == "1":
            return p.name
        return f"{p.name}[{p.width.raw}-1:0]"
    if p.width.msb is None or p.width.msb == 0:
        return p.name
    return f"{p.name}[{p.width.msb}:0]"


def _text_width(label: str) -> int:
    """Estimate text element width: ~9px per char at fontSize=20, min 60px."""
    return max(len(label) * 9, 60)


# ---- Excalidraw element builders -------------------------------------------

def _base_element(
    *,
    eid: str,
    etype: str,
    x: int,
    y: int,
    width: int,
    height: int,
    seed: int,
    stroke_width: int,
    roughness: int,
) -> dict:
    return {
        "type": etype,
        "version": 1,
        "versionNonce": 0,
        "isDeleted": False,
        "id": eid,
        "fillStyle": "hachure",
        "strokeWidth": stroke_width,
        "strokeStyle": "solid",
        "roughness": roughness,
        "opacity": 100,
        "angle": 0,
        "x": int(x),
        "y": int(y),
        "width": int(width),
        "height": int(height),
        "seed": int(seed),
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3} if etype == "rectangle" else None,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
    }


def _rectangle(eid: str, x: int, y: int, w: int, h: int, seed: int) -> dict:
    return _base_element(
        eid=eid, etype="rectangle",
        x=x, y=y, width=w, height=h,
        seed=seed, stroke_width=2, roughness=1,
    )


def _text(eid: str, text: str, x: int, y: int, seed: int,
          font_size: int = FONT_SIZE) -> dict:
    w = _text_width(text)
    el = _base_element(
        eid=eid, etype="text",
        x=x, y=y, width=w, height=PORT_TEXT_H,
        seed=seed, stroke_width=1, roughness=0,
    )
    el.update({
        "fontSize": int(font_size),
        "fontFamily": FONT_FAMILY,
        "text": text,
        "textAlign": "left",
        "verticalAlign": "top",
        "containerId": None,
        "originalText": text,
        "lineHeight": 1.25,
    })
    return el


def _arrow(
    eid: str,
    x: int, y: int,
    length: int,
    seed: int,
    stroke_color: str,
    direction: str,  # "right" or "left"
) -> dict:
    """Create an arrow element.

    For direction="right": arrow points rightward (→), used for both
      input arrows (text→module) and output arrows (module→text).
      The arrow element is placed at the start point, length determines
      where the arrowhead appears.
    For direction="left": arrow points leftward.
    """
    el = _base_element(
        eid=eid, etype="arrow",
        x=x, y=y, width=length, height=1,
        seed=seed, stroke_width=2, roughness=0,
    )
    if direction == "right":
        el["points"] = [[0, 0], [length, 0]]
        el["startArrowhead"] = None
        el["endArrowhead"] = "arrow"
    else:
        el["points"] = [[length, 0], [0, 0]]
        el["startArrowhead"] = "arrow"
        el["endArrowhead"] = None
    el["strokeColor"] = stroke_color
    el["startBinding"] = None
    el["endBinding"] = None
    el["roundness"] = {"type": 2}
    return el


# ---- Layout helpers ---------------------------------------------------------

def _compute_rect_size(inputs: list[Port], outputs: list[Port]) -> tuple[int, int]:
    """Compute module rectangle W×H based on port count and label lengths."""
    n_rows = max(len(inputs), len(outputs), 1)
    h = max(RECT_H, n_rows * ROW_SPACING + 80)

    # Calculate max label widths
    max_in_len = max((len(_port_label(p)) for p in inputs), default=0)
    max_out_len = max((len(_port_label(p)) for p in outputs), default=0)

    # Width: module name width + port label widths
    min_w = RECT_W
    in_zone = _text_width("X" * max_in_len) + ARROW_LENGTH + 12
    out_zone = _text_width("X" * max_out_len) + ARROW_LENGTH + 12
    w = max(min_w, in_zone + out_zone + 60)
    return w, h


# ---- Public API -------------------------------------------------------------

def generate_excalidraw(module: Module) -> str:
    if not isinstance(module, Module):
        raise TypeError(
            f"generate_excalidraw expects Module, got {type(module).__name__}"
        )

    inputs = module.inputs()
    outputs = module.outputs()
    inouts = module.inouts()

    rect_w, rect_h = _compute_rect_size(inputs, outputs)

    elements: list[dict] = []

    # ---- Module rectangle -------------------------------------------------
    elements.append(
        _rectangle("rect-module", RECT_X, RECT_Y, rect_w, rect_h, seed=100001)
    )

    # ---- Module name above the rect ---------------------------------------
    name_x = RECT_X + (rect_w - NAME_TEXT_W) // 2
    name_y = RECT_Y - NAME_TEXT_H - 8
    elements.append(
        _text("text-name", module.name, name_x, name_y,
              seed=100002, font_size=NAME_FONT_SIZE)
    )

    # ---- Input ports (left side) ------------------------------------------
    # Distribute rows vertically centered on the rect
    n_in = len(inputs)
    in_half_span = 0
    if n_in > 0:
        in_center_y = RECT_Y + RECT_H // 2
        in_half_span = (n_in - 1) * ROW_SPACING // 2

    for i, p in enumerate(inputs):
        label = _port_label(p)
        text_w = _text_width(label)
        text_x = RECT_X - ARROW_LENGTH - text_w - 10
        text_y = RECT_Y + RECT_H // 2 - in_half_span + i * ROW_SPACING - PORT_TEXT_H // 2

        elements.append(
            _text(f"text-in-{i}", label, text_x, text_y, seed=200000 + i)
        )
        # Arrow from text right-edge to module left-edge
        arrow_x = text_x + text_w + 4
        arrow_y = text_y + PORT_TEXT_H // 2
        elements.append(
            _arrow(f"arrow-in-{i}", arrow_x, arrow_y, ARROW_LENGTH,
                   seed=500000 + i, stroke_color=COLOR_ARROW_IN, direction="right")
        )

    # ---- Output ports (right side) ----------------------------------------
    n_out = len(outputs)
    out_half_span = 0
    if n_out > 0:
        out_center_y = RECT_Y + RECT_H // 2
        out_half_span = (n_out - 1) * ROW_SPACING // 2

    for i, p in enumerate(outputs):
        label = _port_label(p)
        text_w = _text_width(label)
        text_x = RECT_X + rect_w + ARROW_LENGTH + 10
        text_y = RECT_Y + RECT_H // 2 - out_half_span + i * ROW_SPACING - PORT_TEXT_H // 2

        # Arrow from module right-edge to text left-edge
        arrow_x = RECT_X + rect_w + 4
        arrow_y = text_y + PORT_TEXT_H // 2
        elements.append(
            _arrow(f"arrow-out-{i}", arrow_x, arrow_y, ARROW_LENGTH,
                   seed=600000 + i, stroke_color=COLOR_ARROW_OUT, direction="right")
        )
        elements.append(
            _text(f"text-out-{i}", label, text_x, text_y, seed=300000 + i)
        )

    # ---- Inout ports (bottom row) -----------------------------------------
    n_inout = len(inouts)
    if n_inout > 0:
        base_y = RECT_Y + rect_h + INOUT_GAP
        for i, p in enumerate(inouts):
            label = _port_label(p)
            text_w = _text_width(label)
            # Center the inout row
            total_w = max(n_inout * text_w + (n_inout - 1) * 20, 1)
            start_x = RECT_X + (rect_w - total_w) // 2
            x = start_x + i * (text_w + 20)
            elements.append(
                _text(f"text-inout-{i}", label, x, base_y, seed=400000 + i)
            )
            # Vertical line + diamond for inout
            cx = x + text_w // 2
            elements.append(
                _arrow(f"arrow-inout-{i}", cx - 2, RECT_Y + rect_h + 2, INOUT_GAP - 6,
                       seed=700000 + i, stroke_color=COLOR_ARROW_INOUT, direction="right")
            )

    scene = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {
            "gridSize": None,
            "viewBackgroundColor": "#ffffff",
        },
        "files": {},
    }
    return json.dumps(scene, indent=2, ensure_ascii=False) + "\n"
