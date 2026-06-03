"""Excalidraw block-diagram generator per SPEC §4.4.

Renders a Module as an Excalidraw scene JSON object using plain dicts
(no Jinja2). The output is byte-stable: deterministic port ordering, fixed
seeds, integer coordinates, LF line endings, no trailing whitespace.

Public API:
    generate_excalidraw(module) -> str
"""

from __future__ import annotations

import json

from excel2design.core.models import Module, Port


# ---- Layout constants (all integer px) --------------------------------------

# Module rectangle
RECT_X = 250
RECT_Y = 200
RECT_W = 300
RECT_H = 200

# Per-element dimensions
PORT_TEXT_W = 100          # width of a port-label text element
PORT_TEXT_H = 25           # height of a port-label text element
NAME_TEXT_W = 160
NAME_TEXT_H = 25
ROW_SPACING = 30           # vertical spacing between ports
INOUT_SPACING = 80         # horizontal spacing for inout ports along the bottom
INOUT_OFFSET = 30          # distance from rect bottom to inout text

# Inout row baseline (rect bottom edge)
INOUT_BASE_Y = RECT_Y + RECT_H + INOUT_OFFSET

# Font defaults (mirrors Excalidraw's library font)
FONT_SIZE = 20
NAME_FONT_SIZE = 24
FONT_FAMILY = 1            # 1 = Virgil (the hand-written default in Excalidraw)


# ---- Helpers ----------------------------------------------------------------

def _port_label(p: Port) -> str:
    """Return the displayed label for a port: name + optional bit-width.

    Rules match diagram_svg._label_text:
      * 1-bit → omitted
      * fixed width N (>1) → "[MSB:0]"
      * parameterised width → "[RAW-1:0]"
    """
    if p.width.is_parameter:
        if p.width.raw == "1":
            return p.name
        return f"{p.name}[{p.width.raw}-1:0]"
    # P0-3 fix: tolerate msb=None (default 1-bit from blank cell) — mirrors
    # PortWidth.to_verilog() so all 4 outputs handle 1-bit consistently.
    if p.width.msb is None or p.width.msb == 0:
        return p.name
    return f"{p.name}[{p.width.msb}:0]"


def _port_x_positions(n: int, side: str) -> list[int]:
    """Compute evenly spaced x positions for `n` ports on one side.

    Inputs (left side) are right-anchored: their right edge sits on the rect's
    left edge minus a gap. Outputs (right side) are left-anchored: their left
    edge starts past the rect's right edge plus a gap.

    The y positions are computed per-row in the caller; this helper returns
    only x positions for one side.
    """
    gap = 8
    if side == "left":
        right_edge = RECT_X - gap
        # Right-align labels so they end at the rect's left edge.
        return [right_edge - PORT_TEXT_W for _ in range(n)]
    if side == "right":
        left_edge = RECT_X + RECT_W + gap
        return [left_edge for _ in range(n)]
    raise ValueError(f"unknown side: {side!r}")


def _input_y_positions(n: int) -> list[int]:
    """Y positions for input ports, centered vertically on the rect."""
    if n <= 0:
        return []
    # Distribute rows evenly between top and bottom of rect.
    cy = RECT_Y + RECT_H // 2
    half_span = (n - 1) * ROW_SPACING // 2
    return [cy - half_span + i * ROW_SPACING for i in range(n)]


def _output_y_positions(n: int) -> list[int]:
    """Y positions for output ports (mirrors _input_y_positions)."""
    return _input_y_positions(n)


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
    """Return the shared field set for every Excalidraw element."""
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
    el = _base_element(
        eid=eid, etype="text",
        x=x, y=y, width=PORT_TEXT_W, height=PORT_TEXT_H,
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


# ---- Public API -------------------------------------------------------------

def generate_excalidraw(module: Module) -> str:
    """Render `module` as an Excalidraw scene JSON string.

    Byte-stable: same Module in → same bytes out, every time.
    Seeds are derived from element index, never from `random`.
    Coordinates are integers throughout.
    """
    if not isinstance(module, Module):  # defensive runtime guard
        raise TypeError(
            f"generate_excalidraw expects Module, got {type(module).__name__}"
        )

    elements: list[dict] = []

    # ---- Module rectangle (seed 100001 — fixed) ---------------------------
    elements.append(
        _rectangle("rect-module", RECT_X, RECT_Y, RECT_W, RECT_H, seed=100001)
    )

    # ---- Module name above the rect --------------------------------------
    name_x = RECT_X + (RECT_W - NAME_TEXT_W) // 2
    name_y = RECT_Y - NAME_TEXT_H - 8
    elements.append(
        _text(
            "text-name", module.name, name_x, name_y,
            seed=100002, font_size=NAME_FONT_SIZE,
        )
    )

    # ---- Input ports (left side) -----------------------------------------
    inputs = module.inputs()
    in_xs = _port_x_positions(len(inputs), "left")
    in_ys = _input_y_positions(len(inputs))
    # Reserve 200000+ for inputs so we don't collide with module/rect seeds.
    for i, (p, x, y) in enumerate(zip(inputs, in_xs, in_ys)):
        elements.append(
            _text(f"text-in-{i}", _port_label(p), x, y, seed=200000 + i)
        )

    # ---- Output ports (right side) ---------------------------------------
    outputs = module.outputs()
    out_xs = _port_x_positions(len(outputs), "right")
    out_ys = _output_y_positions(len(outputs))
    # 300000+ for outputs.
    for i, (p, x, y) in enumerate(zip(outputs, out_xs, out_ys)):
        elements.append(
            _text(f"text-out-{i}", _port_label(p), x, y, seed=300000 + i)
        )

    # ---- Inout ports (bottom row) ----------------------------------------
    inouts = module.inouts()
    n_inout = len(inouts)
    if n_inout > 0:
        # Center the row horizontally on the rectangle.
        total_w = (n_inout - 1) * INOUT_SPACING + PORT_TEXT_W
        start_x = RECT_X + (RECT_W - total_w) // 2
        # 400000+ for inouts.
        for i, p in enumerate(inouts):
            x = start_x + i * INOUT_SPACING
            y = INOUT_BASE_Y
            elements.append(
                _text(f"text-inout-{i}", _port_label(p), x, y, seed=400000 + i)
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
