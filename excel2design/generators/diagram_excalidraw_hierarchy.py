"""Hierarchical Excalidraw diagram with inter-submodule connection arrows."""

from __future__ import annotations

import json
from collections import defaultdict

from excel2design.core.models import Module, Project
from excel2design.utils.clock_colors import clock_color

FONT_FAMILY = 4
FONT_SIZE = 16
TITLE_SIZE = 20
SUB_FONT = 12

COLOR_WIRE = "#999999"


def _base(eid: str, etype: str, x: int, y: int, w: int, h: int,
          seed: int, sw: int = 1, roughness: int = 1) -> dict:
    return {"type": etype, "version": 1, "versionNonce": 0, "isDeleted": False, "id": eid,
            "fillStyle": "hachure", "strokeWidth": sw, "strokeStyle": "solid", "roughness": roughness,
            "opacity": 100, "angle": 0, "x": x, "y": y, "width": w, "height": h, "seed": seed,
            "groupIds": [], "frameId": None,
            "roundness": {"type": 3} if etype == "rectangle" else None,
            "boundElements": [], "updated": 1, "link": None, "locked": False}


def _rect(eid, x, y, w, h, seed, color="#888888"):
    el = _base(eid, "rectangle", x, y, w, h, seed, sw=2)
    el["strokeColor"] = color
    return el


def _text(eid, txt, x, y, w, seed, fs=FONT_SIZE, align="left"):
    el = _base(eid, "text", x, y, w, 20, seed, sw=1, roughness=0)
    el.update(fontSize=fs, fontFamily=FONT_FAMILY, text=txt, textAlign=align,
              verticalAlign="top", containerId=None, originalText=txt, lineHeight=1.25)
    return el


def _arrow(eid, x, y, length, seed, color, dash=False):
    el = _base(eid, "arrow", x, y, length, 1, seed, sw=1, roughness=0)
    el.update(points=[[0, 0], [length, 0]], startArrowhead=None, endArrowhead="arrow",
              strokeColor=color, roundness={"type": 2})
    return el


def generate_excalidraw_hierarchy(project: Project, top_sheet: str) -> str:
    top_mod = project.modules.get(top_sheet)
    if top_mod is None:
        return ""

    instances = project.get_submodules(top_sheet)
    n_inst = len(instances)
    sub_w, sub_h = 240, max(max(len(inst.module.ports) * 18 + 40 for inst in instances), 80) if instances else 80
    cols = min(n_inst, 3) if n_inst > 0 else 1
    rows = (n_inst + cols - 1) // cols if n_inst > 0 else 1
    inner_w = cols * (sub_w + 30) + 10
    inner_h = rows * (sub_h + 30) + 40
    wrapper_w = inner_w + 100
    wrapper_h = max(inner_h + 100, max(len(top_mod.inputs()), len(top_mod.outputs())) * 22 + 40)

    wrap_x, wrap_y, seed = 350, 200, 100000
    elements = []

    elements.append(_text("t-title", top_mod.name, wrap_x + 10, wrap_y - 30, 300, seed, TITLE_SIZE))
    elements.append(_rect("r-wrap", wrap_x, wrap_y, wrapper_w, wrapper_h, seed + 1))

    parent_ports = {p.name for p in top_mod.ports}

    # Parent ports
    for i, p in enumerate(top_mod.inputs()):
        py = wrap_y + 60 + i * 22
        color = clock_color(p.clock, is_input=True)
        elements.append(_text(f"t-in-{i}", p.name, wrap_x - 110, py, 100, seed + 10 + i, align="right"))
        elements.append(_arrow(f"a-in-{i}", wrap_x - 46, py + 8, 46, seed + 100 + i, color))
    for i, p in enumerate(top_mod.outputs()):
        py = wrap_y + 60 + i * 22
        color = clock_color(p.clock, is_input=False)
        elements.append(_text(f"t-out-{i}", p.name, wrap_x + wrapper_w + 10, py, 100, seed + 500 + i))
        elements.append(_arrow(f"a-out-{i}", wrap_x + wrapper_w, py + 8, 46, seed + 600 + i, color))

    port_positions = defaultdict(list)

    for idx, inst in enumerate(instances):
        row, col = idx // cols, idx % cols
        sx = wrap_x + 30 + col * (sub_w + 30)
        sy = wrap_y + 50 + row * (sub_h + 30)
        elements.append(_rect(f"r-sub-{idx}", sx, sy, sub_w, sub_h, seed + 1000 + idx, "#BBBBBB"))
        elements.append(_text(f"t-sub-{idx}", inst.instance_name, sx + 10, sy + 4, sub_w - 20, seed + 2000 + idx, FONT_SIZE, "center"))

        for pi, p in enumerate(inst.module.ports):
            py = sy + 24 + pi * 18
            if py > sy + sub_h - 10:
                break
            color = clock_color(p.clock, is_input=(p.direction.value == "input"))
            if p.direction.value == "input":
                label = f"← {p.name}"
                tx, port_x = sx + 6, sx
            else:
                label = f"{p.name} →"
                tx, port_x = sx + sub_w - 120, sx + sub_w
            elements.append(_text(f"t-sp-{idx}-{pi}", label, tx, py, 120, seed + 3000 + idx * 100 + pi, SUB_FONT))
            if p.name not in parent_ports:
                port_positions[p.name].append((port_x, py + 9, p.direction.value))

    # Internal wire connections
    wire_seed = seed + 10000
    for port_name, positions in port_positions.items():
        if len(positions) >= 2:
            outs = [p for p in positions if p[2] == "output"]
            ins = [p for p in positions if p[2] == "input"]
            all_pts = outs + ins
            for j in range(len(all_pts) - 1):
                x1, y1, _ = all_pts[j]
                x2, y2, _ = all_pts[j + 1]
                length = abs(x2 - x1)
                ax = min(x1, x2)
                elements.append(_arrow(f"w-{port_name}-{j}", ax, y1, length, wire_seed, COLOR_WIRE))
                wire_seed += 1

    scene = {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com",
             "elements": elements, "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"}, "files": {}}
    return json.dumps(scene, indent=2, ensure_ascii=False) + "\n"
