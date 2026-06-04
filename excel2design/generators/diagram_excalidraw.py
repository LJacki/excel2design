"""Excalidraw block-diagram generator per SPEC §4.4 (v0.4).

Renders a Module as an Excalidraw scene JSON object using plain dicts
(no Jinja2). The output is byte-stable: deterministic port ordering, fixed
seeds, integer coordinates, LF line endings, no trailing whitespace.

v0.4 changes:
  * fontFamily: 5 (Helvetica / "Normal") — replaces fontFamily 1 (Virgil)
  * Text elements bound to arrow elements via containerId — text always
    visible and follows arrow when moved in Excalidraw.
  * Uniform arrow lengths within each direction group (all inputs same
    length, all outputs same length), sized to longest label.
  * Dynamic rectangle sizing based on port count.
  * Arrow colors: input #2E86C1, output #E74C3C, inout #9B59B6

Public API:
    generate_excalidraw(module) -> str
"""

from __future__ import annotations

import json

from excel2design.core.models import Module, Port


# ---- Layout constants (all integer px) --------------------------------------

RECT_Y = 200
RECT_MIN_W = 250
RECT_MIN_H = 180
NAME_TEXT_W = 200
NAME_TEXT_H = 28
ROW_SPACING = 32       # vertical spacing between port rows
ARROW_H = 4            # arrow element height (thin line)
TEXT_H = 28            # label text element height
GAP = 8                # gap between elements
RECT_PAD = 40          # padding from canvas edge
UNIFORM_PAD = 50       # extra arrow length beyond text width (~4 chars)

# Font settings (Helvetica / Normal — clean, not hand-drawn)
FONT_SIZE = 20
NAME_FONT_SIZE = 24
FONT_FAMILY = 5        # 5 = Helvetica / Normal

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


def _text_w(label: str) -> int:
    """Estimate text element width: ~12px per char at fontSize=20, min 60px."""
    return max(len(label) * 12, 60)


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


def _name_text(eid: str, text: str, x: int, y: int, seed: int) -> dict:
    el = _base_element(
        eid=eid, etype="text",
        x=x, y=y, width=NAME_TEXT_W, height=NAME_TEXT_H,
        seed=seed, stroke_width=1, roughness=0,
    )
    el.update({
        "fontSize": NAME_FONT_SIZE,
        "fontFamily": FONT_FAMILY,
        "text": text,
        "textAlign": "center",
        "verticalAlign": "top",
        "containerId": None,
        "originalText": text,
        "lineHeight": 1.25,
    })
    return el


def _arrow(eid: str, x: int, y: int, length: int, seed: int,
           stroke_color: str) -> dict:
    """A simple arrow element (no text — text is a bound child)."""
    el = _base_element(
        eid=eid, etype="arrow",
        x=x, y=y, width=length, height=ARROW_H,
        seed=seed, stroke_width=2, roughness=0,
    )
    el["points"] = [[0, ARROW_H // 2], [length, ARROW_H // 2]]
    el["startArrowhead"] = None
    el["endArrowhead"] = "arrow"
    el["strokeColor"] = stroke_color
    el["roundness"] = {"type": 2}
    el["startBinding"] = None
    el["endBinding"] = None
    return el


def _bound_text(eid: str, text: str, x: int, y: int,
                container_id: str, seed: int) -> dict:
    """A text element bound to a container arrow via containerId."""
    w = _text_w(text)
    el = _base_element(
        eid=eid, etype="text",
        x=x, y=y, width=w, height=TEXT_H,
        seed=seed, stroke_width=1, roughness=0,
    )
    el.update({
        "fontSize": FONT_SIZE,
        "fontFamily": FONT_FAMILY,
        "text": text,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": container_id,
        "originalText": text,
        "lineHeight": 1.25,
    })
    return el


# ---- Public API -------------------------------------------------------------

def generate_excalidraw(module: Module) -> str:
    if not isinstance(module, Module):
        raise TypeError(
            f"generate_excalidraw expects Module, got {type(module).__name__}"
        )

    inputs = module.inputs()
    outputs = module.outputs()
    inouts = module.inouts()

    # Uniform arrow lengths: all inputs same, all outputs same
    in_labels = [_port_label(p) for p in inputs]
    out_labels = [_port_label(p) for p in outputs]
    max_in_text_w = max((_text_w(l) for l in in_labels), default=0)
    max_out_text_w = max((_text_w(l) for l in out_labels), default=0)
    uniform_in_len = max_in_text_w + UNIFORM_PAD if in_labels else 0
    uniform_out_len = max_out_text_w + UNIFORM_PAD if out_labels else 0

    # Rectangle sizing — position accounts for left-side arrows
    rect_x = max(uniform_in_len + GAP + RECT_PAD, RECT_PAD)
    rect_w = max(RECT_MIN_W, max_in_text_w + max_out_text_w)
    n_rows = max(len(inputs), len(outputs), 1)
    rect_h = max(RECT_MIN_H, n_rows * ROW_SPACING + 80)

    elements: list[dict] = []
    seed_base = 100000

    # ---- Module rectangle -------------------------------------------------
    elements.append(
        _rectangle("rect-module", rect_x, RECT_Y, rect_w, rect_h,
                   seed=seed_base + 1)
    )

    # ---- Module name above the rect ---------------------------------------
    name_x = rect_x + (rect_w - NAME_TEXT_W) // 2
    name_y = RECT_Y - NAME_TEXT_H - 8
    elements.append(
        _name_text("text-name", module.name, name_x, name_y, seed=seed_base + 2)
    )

    # ---- Input ports (left side) ------------------------------------------
    n_in = len(inputs)
    in_half = (n_in - 1) * ROW_SPACING // 2 if n_in > 0 else 0
    center_y = RECT_Y + rect_h // 2
    for i, label in enumerate(in_labels):
        arrow_id = f"arrow-in-{i}"
        text_id = f"text-in-{i}"
        ax = rect_x - uniform_in_len - GAP
        ay = center_y - in_half + i * ROW_SPACING
        # Arrow
        elements.append(
            _arrow(arrow_id, ax, ay, uniform_in_len,
                   seed=seed_base + 10 + i, stroke_color=COLOR_ARROW_IN)
        )
        # Text bound to arrow, centered within it
        tw = _text_w(label)
        tx = ax + (uniform_in_len - tw) // 2
        ty = ay - TEXT_H - 2
        elements.append(
            _bound_text(text_id, label, tx, ty, arrow_id, seed=seed_base + 100 + i)
        )

    # ---- Output ports (right side) ----------------------------------------
    n_out = len(outputs)
    out_half = (n_out - 1) * ROW_SPACING // 2 if n_out > 0 else 0
    for i, label in enumerate(out_labels):
        arrow_id = f"arrow-out-{i}"
        text_id = f"text-out-{i}"
        ax = rect_x + rect_w + GAP
        ay = center_y - out_half + i * ROW_SPACING
        elements.append(
            _arrow(arrow_id, ax, ay, uniform_out_len,
                   seed=seed_base + 200 + i, stroke_color=COLOR_ARROW_OUT)
        )
        tw = _text_w(label)
        tx = ax + (uniform_out_len - tw) // 2
        ty = ay - TEXT_H - 2
        elements.append(
            _bound_text(text_id, label, tx, ty, arrow_id, seed=seed_base + 300 + i)
        )

    # ---- Inout ports (bottom row) -----------------------------------------
    if inouts:
        inout_labels = [_port_label(p) for p in inouts]
        base_ay = RECT_Y + rect_h + 32
        total_w = sum(_text_w(l) + 16 for l in inout_labels) - 16
        x = rect_x + (rect_w - total_w) // 2
        for i, label in enumerate(inout_labels):
            tw = _text_w(label)
            elements.append(
                _bound_text(f"text-inout-{i}", label, x, base_ay,
                            "", seed=seed_base + 400 + i)
            )
            x += tw + 16

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
