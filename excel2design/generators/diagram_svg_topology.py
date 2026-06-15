"""v0.7 Phase 17a — Visio-style flat topology SVG.

Renders a wrapper module's direct submodules in a horizontal grid (auto-wrap
when ≥5), with all wrapper-level ports placed strictly on the outside
(inputs/inouts on the left, outputs on the right) and routed with simple
horizontal + arrowed lines.

Constraints (Jack, 2026-06-15):
- 横排子模块，≥5 自动换行（2-3-4 网格）
- input/inout 在模块左侧，output 在模块右侧
- 端口顺序 = Excel 原序
- 端口名 + 位宽标签画在线上方（不是穿线）
- 仅画 wrapper 顶层端口 ↔ 直接子模块（depth=1）的连线
- 连线为水平直线 + 箭头
- 不画 sibling 连线、不递归子模块

接口与 ``generate_svg_hierarchy`` 一致：``(project, top_module) -> str``。
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from excel2design.core.models import Direction, Module, Project, SubmoduleInstance


# ---- Layout constants (v0.7 Phase 17a) ------------------------------------

FONT_FAMILY = "Comic Shanns, sans-serif"
FONT_SIZE_PORT = 10
FONT_SIZE_SUB = 10
FONT_SIZE_MODULE = 12
STROKE_W_MODULE = 1.5
STROKE_W_LINE = 1.5

PORT_ROW_H = 14
HEADER_H = 22
SIDE_PAD = 30       # left/right margin inside the module box (above the body)
TOP_PAD = 6         # gap between module rect and port rows
BOTTOM_PAD = 6
MODULE_GAP_X = 60   # horizontal gap between sub-module boxes
MODULE_GAP_Y = 40   # vertical gap between rows of sub-module boxes
WRAPPER_PAD = 50    # padding inside the wrapper around the submodule grid
WIRE_GAP = 30       # horizontal distance from wrapper port to first submodule
ARROW_LEN = 10      # arrowhead length (visual)

MIN_MOD_W = 90      # 17a.2: 模块宽度 = max(端口名长度, 90)  (approx via char count)
MIN_MOD_H_PAD = 80  # 17a.2: 模块高度 = max(端口数, 4) * PORT_ROW_H + 80

CANVAS_PAD_X = 40
CANVAS_PAD_Y = 60

COLOR_BG = "#FFFFFF"
COLOR_STROKE = "#888888"
COLOR_TEXT = "#222222"
COLOR_ARROW_IN = "#2E86C1"
COLOR_ARROW_OUT = "#E74C3C"

# Approximate average char width for Comic Shanns fallback (sans-serif ~6.5px
# at 10pt). Used only for sizing — actual rendering uses the real font.
AVG_CHAR_PX = 7


# ---- Helpers ---------------------------------------------------------------

def _width_str(p) -> str:
    """Return ``[W:0]`` style suffix (or empty for scalar 1-bit)."""
    return p.width.to_verilog()


def _label_text(p) -> str:
    """Port label rendered above the wire, e.g. ``data[7:0]``."""
    return f"{p.name}{_width_str(p)}"


def _label_px(p) -> int:
    """Approximate label width in pixels (used to size submodule boxes)."""
    return max(1, len(_label_text(p))) * AVG_CHAR_PX


def _left_ports(mod: Module) -> list:
    """Ports rendered on the left side of a module: inputs + inouts (Excel order)."""
    return [p for p in mod.ports if p.direction in (Direction.INPUT, Direction.INOUT)]


def _right_ports(mod: Module) -> list:
    """Ports rendered on the right side: outputs (Excel order)."""
    return [p for p in mod.ports if p.direction == Direction.OUTPUT]


def _mod_w(mod: Module) -> int:
    """17a.2: 模块宽度 = max(端口名长度, 90).  Approximated in pixels."""
    max_label = max((_label_px(p) for p in mod.ports), default=0)
    return max(max_label, MIN_MOD_W)


def _mod_h(mod: Module) -> int:
    """17a.2: 模块高度 = max(端口数, 4) * PORT_ROW_H + 80."""
    n_ports = max(len(mod.ports), 4)
    return n_ports * PORT_ROW_H + MIN_MOD_H_PAD


def _grid(n: int) -> tuple[int, int]:
    """Pick (cols, rows) for n submodules per the 2-3-4 auto-wrap rule.

    - n <= 4  → 1 row, n cols
    - n == 5  → 3 + 2  (cols=3, rows=2)
    - n == 6  → 3 + 3  (cols=3, rows=2)
    - n == 7  → 4 + 3  (cols=4, rows=2)
    - n == 8  → 4 + 4  (cols=4, rows=2)
    - n >= 9  → 4 cols, ceil(n/4) rows
    """
    if n <= 4:
        return max(n, 1), 1
    if n <= 6:
        return 3, 2
    if n <= 8:
        return 4, 2
    return 4, (n + 3) // 4


# ---- Markers (arrow heads) -------------------------------------------------

def _add_markers(svg: ET.Element) -> None:
    """Add reusable arrowhead markers (one per direction/colour)."""
    defs = ET.SubElement(svg, "defs")
    for mid, color in (
        ("arrow_in", COLOR_ARROW_IN),
        ("arrow_out", COLOR_ARROW_OUT),
    ):
        m = ET.SubElement(defs, "marker", {
            "id": mid,
            "markerWidth": "10", "markerHeight": "8",
            "refX": "9", "refY": "4",
            "orient": "auto-start-reverse",
            "markerUnits": "strokeWidth",
        })
        ET.SubElement(m, "path", {
            "d": "M 0,0 L 10,4 L 0,8 Z",
            "fill": color,
        })


# ---- Drawing primitives ---------------------------------------------------

def _draw_module(svg: ET.Element, *, x: int, y: int, w: int, h: int,
                 title: str, sub_label: str | None) -> None:
    """Draw a single module rectangle + its top title + (optional) inner label."""
    ET.SubElement(svg, "rect", {
        "x": str(x), "y": str(y),
        "width": str(w), "height": str(h),
        "rx": "4", "ry": "4",
        "fill": COLOR_BG, "stroke": "#000000",
        "stroke-width": str(STROKE_W_MODULE),
    })
    # Module name above the rectangle (17a.5: 模块名 12px, 顶部居中)
    t = ET.SubElement(svg, "text", {
        "x": str(x + w // 2), "y": str(y - 6),
        "font-family": FONT_FAMILY,
        "font-size": str(FONT_SIZE_MODULE),
        "font-weight": "bold",
        "fill": COLOR_TEXT,
        "text-anchor": "middle",
    })
    t.text = title
    if sub_label:
        st = ET.SubElement(svg, "text", {
            "x": str(x + w // 2), "y": str(y + h // 2 + 4),
            "font-family": FONT_FAMILY,
            "font-size": str(FONT_SIZE_SUB),
            "fill": COLOR_TEXT,
            "text-anchor": "middle",
        })
        st.text = sub_label


def _draw_port(svg: ET.Element, *, side: str, x: int, y: int,
               p) -> None:
    """Draw a port label + connecting tick on the given module side.

    side: "left"  → label just left of x, tick goes right
          "right" → label just right of x, tick goes left
    The y is the wire centerline; the label is drawn *above* the wire
    (17a.3: 端口名 + 位宽标签在线上方).
    """
    label = _label_text(p)
    if side == "left":
        # Tick: short horizontal line from module edge going left a few px.
        tick_x1 = x
        tick_x2 = x - 4
        # Label above the tick, right-aligned to the tick start.
        tx, anchor = x - 6, "end"
    else:  # right
        tick_x1 = x
        tick_x2 = x + 4
        tx, anchor = x + 6, "start"

    ET.SubElement(svg, "line", {
        "x1": str(tick_x1), "y1": str(y),
        "x2": str(tick_x2), "y2": str(y),
        "stroke": "#000000", "stroke-width": "1",
    })
    t = ET.SubElement(svg, "text", {
        "x": str(tx), "y": str(y - 3),
        "font-family": FONT_FAMILY,
        "font-size": str(FONT_SIZE_PORT),
        "fill": COLOR_TEXT,
        "text-anchor": anchor,
    })
    t.text = label


# ---- Public API ------------------------------------------------------------

def generate_svg_topology(project: Project, top_module: str) -> str:
    """Render a Visio-style flat topology for ``top_module``.

    Returns a complete SVG document as a UTF-8 string.  Returns an empty
    string when ``top_module`` is not present in ``project.modules`` (mirrors
    the behaviour of ``generate_svg_hierarchy``).
    """
    top_mod = project.modules.get(top_module)
    if top_mod is None:
        return ""

    # Direct submodules only (depth=1) per 17a.4.
    instances = [s for s in project.get_submodules(top_module, recursive=False)]

    # Per-submodule sizing.
    sub_sizes: list[tuple[str, int, int]] = [
        (inst.instance_name, _mod_w(inst.module), _mod_h(inst.module))
        for inst in instances
    ]

    n = len(instances)
    cols, rows = _grid(n) if n else (1, 1)

    # Use a uniform per-row width = max submodule width in the largest row,
    # and a uniform per-row height = max submodule height in the largest row.
    # Simpler: a single uniform cell (max w, max h) — easier alignment, fits
    # 17a.2 "横排" intent.
    if sub_sizes:
        cell_w = max(w for _, w, _ in sub_sizes)
        cell_h = max(h for _, _, h in sub_sizes)
    else:
        cell_w, cell_h = 200, 120

    grid_w = cols * cell_w + (cols - 1) * MODULE_GAP_X if cols > 0 else 0
    grid_h = rows * cell_h + (rows - 1) * MODULE_GAP_Y if rows > 0 else 0

    n_in = len(_left_ports(top_mod))   # input + inout
    n_out = len(_right_ports(top_mod))  # output
    side_rows = max(n_in, n_out, 1)

    # Wrapper box: encloses the submodule grid with padding.
    wrapper_w = grid_w + WRAPPER_PAD * 2
    wrapper_h = max(grid_h + WRAPPER_PAD * 2, side_rows * PORT_ROW_H + WRAPPER_PAD * 2)

    # Canvas: leave room for wrapper ports on the left/right of the wrapper.
    canvas_w = wrapper_w + CANVAS_PAD_X * 2
    canvas_h = wrapper_h + CANVAS_PAD_Y * 2
    wrap_x = CANVAS_PAD_X
    wrap_y = CANVAS_PAD_Y

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "version": "1.1",
        "width": str(canvas_w),
        "height": str(canvas_h),
        "viewBox": f"0 0 {canvas_w} {canvas_h}",
    })
    ET.SubElement(svg, "rect", {
        "x": "0", "y": "0",
        "width": str(canvas_w), "height": str(canvas_h),
        "fill": COLOR_BG,
    })
    _add_markers(svg)

    # Wrapper outline
    ET.SubElement(svg, "rect", {
        "x": str(wrap_x), "y": str(wrap_y),
        "width": str(wrapper_w), "height": str(wrapper_h),
        "rx": "8", "ry": "8",
        "fill": COLOR_BG,
        "stroke": COLOR_STROKE,
        "stroke-width": "1.5",
    })

    # ---- Submodule cells (drawn first so wires sit on top) ---------------
    sub_pos: list[tuple[int, int, int, int, SubmoduleInstance]] = []  # (x, y, w, h, inst)
    for idx, (name, w, h) in enumerate(sub_sizes):
        row, col = idx // cols, idx % cols
        sx = wrap_x + WRAPPER_PAD + col * (cell_w + MODULE_GAP_X)
        sy = wrap_y + WRAPPER_PAD + row * (cell_h + MODULE_GAP_Y)
        # Uniform cell — draw inner rect at the actual size, centred.
        x = sx + (cell_w - w) // 2
        y = sy + (cell_h - h) // 2
        _draw_module(svg, x=x, y=y, w=w, h=h, title=name, sub_label=None)
        sub_pos.append((x, y, w, h, instances[idx]))

    # ---- Wrapper-level ports + wires (depth=1) ---------------------------
    # Ports on the wrapper are drawn on the outside of the wrapper rect.
    # We only draw wires for ports that match a submodule's port (by name
    # and direction) — this is the "直接子模块" connection in 17a.4.
    # Build name → submodule-edge endpoint lookup for direct children.
    # A wrapper input is consumed by any submodule with a port of the same
    # name that is an input on the submodule.  Symmetric for outputs.
    sub_name_to_inst: dict[str, SubmoduleInstance] = {
        inst.instance_name: inst for inst in instances
    }
    # Index submodule ports by (name, direction) for quick lookup.
    sub_port_index: dict[tuple[str, str], list[tuple[int, int, str]]] = {}
    for x, y, w, h, inst in sub_pos:
        # Left-side ports (input/inout): edge = (x, y_for_port)
        n_left = len(_left_ports(inst.module))
        for i, p in enumerate(_left_ports(inst.module)):
            py = y + HEADER_H + TOP_PAD + i * PORT_ROW_H + 4
            sub_port_index.setdefault((p.name, p.direction.value), []).append(
                (x, py, inst.instance_name)
            )
        # Right-side ports (output): edge = (x + w, y_for_port)
        for i, p in enumerate(_right_ports(inst.module)):
            py = y + HEADER_H + TOP_PAD + i * PORT_ROW_H + 4
            sub_port_index.setdefault((p.name, p.direction.value), []).append(
                (x + w, py, inst.instance_name)
            )

    # Draw wrapper input/inout ports (left side of wrapper).
    left_ports = _left_ports(top_mod)
    for i, p in enumerate(left_ports):
        py = wrap_y + WRAPPER_PAD // 2 + i * PORT_ROW_H
        # Limit to wrapper height range.
        py = min(py, wrap_y + wrapper_h - 14)
        # Port tick + label on wrapper outer left edge.
        port_x = wrap_x
        _draw_port(svg, side="left", x=port_x, y=py, p=p)
        # Wire: horizontal from wrapper edge to the matching submodule input
        # port, with an arrow pointing INTO the submodule (▶).
        matches = sub_port_index.get((p.name, "input")) or sub_port_index.get(
            (p.name, "inout")
        )
        if not matches:
            continue
        for sub_edge_x, sub_edge_y, _inst_name in matches:
            # Wire starts a few px left of the submodule edge (so the arrow
            # points at the tick we drew on the submodule).
            x1 = port_x - 2
            x2 = sub_edge_x - 4
            ET.SubElement(svg, "line", {
                "x1": str(x1), "y1": str(py),
                "x2": str(x2), "y2": str(sub_edge_y),
                "stroke": COLOR_ARROW_IN, "stroke-width": str(STROKE_W_LINE),
                "marker-end": "url(#arrow_in)",
            })

    # Draw wrapper output ports (right side of wrapper).
    right_ports = _right_ports(top_mod)
    for i, p in enumerate(right_ports):
        py = wrap_y + WRAPPER_PAD // 2 + i * PORT_ROW_H
        py = min(py, wrap_y + wrapper_h - 14)
        port_x = wrap_x + wrapper_w
        _draw_port(svg, side="right", x=port_x, y=py, p=p)
        matches = sub_port_index.get((p.name, "output"))
        if not matches:
            continue
        for sub_edge_x, sub_edge_y, _inst_name in matches:
            x1 = port_x + 2
            x2 = sub_edge_x + 4
            ET.SubElement(svg, "line", {
                "x1": str(x1), "y1": str(py),
                "x2": str(x2), "y2": str(sub_edge_y),
                "stroke": COLOR_ARROW_OUT, "stroke-width": str(STROKE_W_LINE),
                "marker-end": "url(#arrow_out)",
            })

    # Top wrapper title.
    title_t = ET.SubElement(svg, "text", {
        "x": str(wrap_x + wrapper_w // 2),
        "y": str(wrap_y - 12),
        "font-family": FONT_FAMILY,
        "font-size": str(FONT_SIZE_MODULE + 2),
        "font-weight": "bold",
        "fill": COLOR_TEXT,
        "text-anchor": "middle",
    })
    title_t.text = top_mod.name

    # Empty-submodule fallback (17a.7 test 3): emit a helpful note.
    if n == 0:
        note = ET.SubElement(svg, "text", {
            "x": str(wrap_x + wrapper_w // 2),
            "y": str(wrap_y + wrapper_h // 2 + 4),
            "font-family": FONT_FAMILY,
            "font-size": str(FONT_SIZE_PORT),
            "fill": COLOR_TEXT,
            "text-anchor": "middle",
        })
        note.text = "(no direct submodules)"

    raw = ET.tostring(svg, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + raw + "\n"
