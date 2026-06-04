"""Excalidraw block-diagram generator per SPEC §4.4 (v0.4).

Renders a Module as an Excalidraw scene JSON object using plain dicts
(no Jinja2). The output is byte-stable: deterministic port ordering, fixed
seeds, integer coordinates, LF line endings, no trailing whitespace.

v0.4 changes:
  * fontFamily: 5 (Helvetica / "Normal") — replaces fontFamily 1 (Virgil)
  * Port labels rendered on arrow elements (arrow.text field) — single
    element per port, no separate text+arrow, natural alignment
  * Arrow length dynamically sized to fit label text
  * Dynamic rectangle sizing based on port count
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
ARROW_HEIGHT = 30      # arrow element height (room for text)
GAP = 10               # gap between arrow edge and module edge
RECT_PAD = 40          # padding from canvas edge

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


def _arrow_len(label: str) -> int:
    """Arrow length must accommodate the label text at ~13px/char + padding."""
    return max(len(label) * 13 + 30, 100)


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


def _arrow_with_label(
    eid: str,
    label: str,
    x: int, y: int,
    length: int,
    seed: int,
    stroke_color: str,
) -> dict:
    """Create an arrow element with the port label as its text.

    Arrow points rightward (→). The text is rendered along the arrow at
    its midpoint.  Input ports are placed left of the module (arrowhead
    points into module edge), output ports right of the module (arrowhead
    points away).
    """
    el = _base_element(
        eid=eid, etype="arrow",
        x=x, y=y, width=length, height=ARROW_HEIGHT,
        seed=seed, stroke_width=2, roughness=0,
    )
    el["points"] = [[0, ARROW_HEIGHT // 2], [length, ARROW_HEIGHT // 2]]
    el["startArrowhead"] = None
    el["endArrowhead"] = "arrow"
    el["strokeColor"] = stroke_color
    el["text"] = label
    el["originalText"] = label
    el["fontSize"] = FONT_SIZE
    el["fontFamily"] = FONT_FAMILY
    el["roundness"] = {"type": 2}
    el["startBinding"] = None
    el["endBinding"] = None
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

    # Compute arrow lengths
    in_labels = [_port_label(p) for p in inputs]
    out_labels = [_port_label(p) for p in outputs]
    in_lens = [_arrow_len(l) for l in in_labels]
    out_lens = [_arrow_len(l) for l in out_labels]
    max_in_len = max(in_lens, default=0)
    max_out_len = max(out_lens, default=0)

    # Rectangle sizing
    rect_x = max_in_len + GAP + RECT_PAD
    rect_w = max(RECT_MIN_W, RECT_PAD * 2)
    n_rows = max(len(inputs), len(outputs), 1)
    rect_h = max(RECT_MIN_H, n_rows * ROW_SPACING + 80)

    # Canvas sizing
    canvas_w = rect_x + rect_w + max_out_len + GAP + RECT_PAD + 20
    canvas_h = RECT_Y + rect_h + 60

    elements: list[dict] = []

    # ---- Module rectangle -------------------------------------------------
    elements.append(
        _rectangle("rect-module", rect_x, RECT_Y, rect_w, rect_h, seed=100001)
    )

    # ---- Module name above the rect ---------------------------------------
    name_x = rect_x + (rect_w - NAME_TEXT_W) // 2
    name_y = RECT_Y - NAME_TEXT_H - 8
    elements.append(
        _name_text("text-name", module.name, name_x, name_y, seed=100002)
    )

    # ---- Input ports (left side, arrows point → into module) --------------
    n_in = len(inputs)
    in_half = (n_in - 1) * ROW_SPACING // 2 if n_in > 0 else 0
    center_y = RECT_Y + rect_h // 2
    for i, label in enumerate(in_labels):
        arrow_len = in_lens[i]
        ax = rect_x - arrow_len - GAP
        ay = center_y - in_half + i * ROW_SPACING - ARROW_HEIGHT // 2
        elements.append(
            _arrow_with_label(
                f"arrow-in-{i}", label,
                ax, ay, arrow_len,
                seed=200000 + i, stroke_color=COLOR_ARROW_IN,
            )
        )

    # ---- Output ports (right side, arrows point → out of module) ----------
    n_out = len(outputs)
    out_half = (n_out - 1) * ROW_SPACING // 2 if n_out > 0 else 0
    for i, label in enumerate(out_labels):
        arrow_len = out_lens[i]
        ax = rect_x + rect_w + GAP
        ay = center_y - out_half + i * ROW_SPACING - ARROW_HEIGHT // 2
        elements.append(
            _arrow_with_label(
                f"arrow-out-{i}", label,
                ax, ay, arrow_len,
                seed=300000 + i, stroke_color=COLOR_ARROW_OUT,
            )
        )

    # ---- Inout ports (bottom row) -----------------------------------------
    if inouts:
        inout_labels = [_port_label(p) for p in inouts]
        base_y = RECT_Y + rect_h + 24
        total_w = sum(_arrow_len(l) + 12 for l in inout_labels) - 12
        start_x = rect_x + (rect_w - total_w) // 2
        x = start_x
        for i, label in enumerate(inout_labels):
            alen = _arrow_len(label)
            elements.append(
                _arrow_with_label(
                    f"arrow-inout-{i}", label,
                    x, base_y, alen,
                    seed=400000 + i, stroke_color=COLOR_ARROW_INOUT,
                )
            )
            x += alen + 12

    # ---- Scene ------------------------------------------------------------
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
