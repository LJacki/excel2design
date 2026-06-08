"""Multi-file project output generator (v0.5, SPEC §15.4).

Orchestrates the complete output: .vh, .f, all .v wrappers, all diagrams.
"""

from __future__ import annotations

from pathlib import Path

from excel2design.core.models import Project
from excel2design.generators.defines import generate_vh, generate_f
from excel2design.generators.verilog import generate_wrapper
from excel2design.generators.diagram_html import generate_html
from excel2design.generators.diagram_svg import generate_svg
from excel2design.generators.diagram_svg_hierarchy import generate_svg_hierarchy
from excel2design.generators.diagram_excalidraw import generate_excalidraw


def generate_all(project: Project, output_dir: Path | str) -> list[Path]:
    """Generate all project files into the standard directory structure.

    Returns list of all generated file paths.
    """
    output_dir = Path(output_dir)
    generated: list[Path] = []

    for top_name in project.top_modules:
        top_mod = project.modules.get(top_name)
        if top_mod is None:
            continue

        base = output_dir / top_name

        # define/
        define_dir = base / "define"
        define_dir.mkdir(parents=True, exist_ok=True)
        if project.defines:
            vh_path = define_dir / f"{top_name}.vh"
            vh_path.write_text(generate_vh(project.defines, top_name), encoding="utf-8")
            generated.append(vh_path)

        # filelist/
        fl_dir = base / "filelist"
        fl_dir.mkdir(parents=True, exist_ok=True)
        fl_path = fl_dir / f"{top_name}.f"
        fl_path.write_text(generate_f(project.walk_bfs(), top_name), encoding="utf-8")
        generated.append(fl_path)

        # rtl/
        rtl_dir = base / "rtl"
        rtl_dir.mkdir(parents=True, exist_ok=True)
        for sheet_name in project.walk_bfs():
            mod = project.modules.get(sheet_name)
            if mod is None:
                continue
            short_name = sheet_name.rsplit(".", 1)[-1] if "." in sheet_name else sheet_name
            v = generate_wrapper(mod, project=project, source_sheet=sheet_name)
            v_path = rtl_dir / f"{short_name}.v"
            v_path.write_text(v, encoding="utf-8")
            generated.append(v_path)

        # doc/
        doc_dir = base / "doc"
        doc_dir.mkdir(parents=True, exist_ok=True)
        for sheet_name in project.walk_bfs():
            mod = project.modules.get(sheet_name)
            if mod is None:
                continue
            short_name = sheet_name.rsplit(".", 1)[-1] if "." in sheet_name else sheet_name

            html_path = doc_dir / f"{short_name}.html"
            html_path.write_text(generate_html(mod), encoding="utf-8")

            svg_path = doc_dir / f"{short_name}.svg"
            svg_path.write_text(generate_svg(mod), encoding="utf-8")

            exc_path = doc_dir / f"{short_name}.excalidraw"
            exc_path.write_text(generate_excalidraw(mod), encoding="utf-8")

            generated.extend([html_path, svg_path, exc_path])

        # Generate hierarchy diagram if there are submodules
        if project.hierarchy:
            hier_svg = generate_svg_hierarchy(project, top_name)
            if hier_svg:
                hier_path = doc_dir / f"{top_name}_hierarchy.svg"
                hier_path.write_text(hier_svg, encoding="utf-8")
                generated.append(hier_path)

    return generated
