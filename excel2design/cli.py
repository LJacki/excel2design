"""excel2design CLI — entry point per SPEC §6.

Usage:
    excel2design parse <excel> [--json]
    excel2design diagram <excel> <module> [--format {html,svg,excalidraw,all}] [--output <dir>]
    excel2design wrapper <excel> <module> [--output <file>]
    excel2design all <excel> <module> [--output <dir>]

Exit codes (per SPEC §6):
    0 — success
    2 — Excel file not found
    3 — module/sheet not found
    4 — parsing error
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from excel2design.core.exceptions import (
    DuplicatePortError,
    ExcelParseError,
    MarkerMissingError,
    ModuleNotFoundError,
    PortValidationError,
)
from excel2design.parsers.excel import get_module, parse_workbook
from excel2design.generators.diagram_html import generate_html
from excel2design.generators.diagram_svg import generate_svg
from excel2design.generators.diagram_excalidraw import generate_excalidraw
from excel2design.generators.verilog import generate_wrapper


# ---- Error handling -------------------------------------------------------

class _ErrorRenderer:
    """Render an exception as a click-style error message with location."""

    @staticmethod
    def render(exc: BaseException) -> str:
        if isinstance(exc, ExcelParseError):
            return str(exc)  # has nice formatted output already
        return f"{type(exc).__name__}: {exc}"


def _handle_errors(ctx: click.Context, exc: BaseException) -> None:
    """Top-level error handler. Prints error and sets exit code."""
    click.echo(_ErrorRenderer.render(exc), err=True)
    if isinstance(exc, FileNotFoundError):
        ctx.exit(2)
    elif isinstance(exc, ModuleNotFoundError):
        ctx.exit(3)
    elif isinstance(exc, ExcelParseError):
        ctx.exit(4)
    else:
        ctx.exit(1)


# ---- Helpers --------------------------------------------------------------

def _load_module(excel_path: Path, module_name: str):
    """Load one module from an Excel file. Raises appropriate exceptions."""
    if not excel_path.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_path}")
    modules = parse_workbook(excel_path)
    return get_module(modules, module_name)


# ---- CLI group ------------------------------------------------------------

@click.group()
@click.version_option(package_name="excel2design")
def main() -> None:
    """excel2design — Excel module port tables to box diagrams and Verilog wrapper."""


# ---- parse ----------------------------------------------------------------

@main.command()
@click.argument("excel", type=click.Path(exists=False, path_type=Path))
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def parse(excel: Path, as_json: bool) -> None:
    """Parse an Excel file and list all modules with summary."""
    try:
        if not excel.exists():
            raise FileNotFoundError(f"Excel file not found: {excel}")
        modules = parse_workbook(excel)
    except Exception as e:
        click.echo(_ErrorRenderer.render(e), err=True)
        sys.exit(_exit_code(e))

    if as_json:
        data = {
            "modules": [
                {
                    "name": m.name,
                    "source_sheet": m.source_sheet,
                    "parameter_count": len(m.parameters),
                    "port_count": len(m.ports),
                    "input_count": len(m.inputs()),
                    "output_count": len(m.outputs()),
                    "inout_count": len(m.inouts()),
                }
                for m in modules
            ]
        }
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        for m in modules:
            click.echo(f"Module: {m.name}  (sheet: {m.source_sheet})")
            click.echo(f"  Parameters: {len(m.parameters)}")
            for p in m.parameters:
                click.echo(f"    {p.name} = {p.value}")
            click.echo(f"  Ports:      {len(m.ports)}")
            click.echo(f"    inputs:   {len(m.inputs())}")
            click.echo(f"    outputs:  {len(m.outputs())}")
            click.echo(f"    inouts:   {len(m.inouts())}")


# ---- diagram --------------------------------------------------------------

@main.command()
@click.argument("excel", type=click.Path(exists=False, path_type=Path))
@click.argument("module_name")
@click.option(
    "--format", "fmt",
    type=click.Choice(["html", "svg", "excalidraw", "all"], case_sensitive=False),
    default="all",
    help="Diagram format to generate (default: all)",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=Path("./output"),
    help="Output directory (default: ./output)",
)
def diagram(excel: Path, module_name: str, fmt: str, output: Path) -> None:
    """Generate one or more box diagrams for a module."""
    try:
        m = _load_module(excel, module_name)
    except Exception as e:
        click.echo(_ErrorRenderer.render(e), err=True)
        sys.exit(_exit_code(e))

    output.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    if fmt in ("html", "all"):
        p = output / f"{module_name}.html"
        p.write_text(generate_html(m), encoding="utf-8", newline="\n")
        written.append(str(p))

    if fmt in ("svg", "all"):
        p = output / f"{module_name}.svg"
        p.write_text(generate_svg(m), encoding="utf-8", newline="\n")
        written.append(str(p))

    if fmt in ("excalidraw", "all"):
        p = output / f"{module_name}.excalidraw"
        p.write_text(generate_excalidraw(m), encoding="utf-8", newline="\n")
        written.append(str(p))

    for w in written:
        click.echo(f"Wrote {w}")


# ---- wrapper --------------------------------------------------------------

@main.command()
@click.argument("excel", type=click.Path(exists=False, path_type=Path))
@click.argument("module_name")
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output file path (default: ./<module_name>.v)",
)
def wrapper(excel: Path, module_name: str, output: Path | None) -> None:
    """Generate a Verilog wrapper for a module."""
    try:
        m = _load_module(excel, module_name)
    except Exception as e:
        click.echo(_ErrorRenderer.render(e), err=True)
        sys.exit(_exit_code(e))

    out_path = output or Path(f"./{module_name}.v")
    v = generate_wrapper(m, source_file=excel.name, source_sheet=module_name)
    out_path.write_text(v, encoding="utf-8", newline="\n")
    click.echo(f"Wrote {out_path}")


# ---- all ------------------------------------------------------------------

@main.command()
@click.argument("excel", type=click.Path(exists=False, path_type=Path))
@click.argument("module_name")
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=Path("./output"),
    help="Output directory (default: ./output)",
)
def all_cmd(excel: Path, module_name: str, output: Path) -> None:
    """Generate all 3 diagrams + the Verilog wrapper."""
    ctx = click.get_current_context()
    try:
        m = _load_module(excel, module_name)
    except Exception as e:
        click.echo(_ErrorRenderer.render(e), err=True)
        sys.exit(_exit_code(e))

    output.mkdir(parents=True, exist_ok=True)

    # Diagrams
    for gen, ext in [
        (generate_html, "html"),
        (generate_svg, "svg"),
        (generate_excalidraw, "excalidraw"),
    ]:
        p = output / f"{module_name}.{ext}"
        p.write_text(gen(m), encoding="utf-8", newline="\n")
        click.echo(f"Wrote {p}")

    # Wrapper
    v = generate_wrapper(m, source_file=excel.name, source_sheet=module_name)
    p = output / f"{module_name}.v"
    p.write_text(v, encoding="utf-8", newline="\n")
    click.echo(f"Wrote {p}")


# 'all' is a Python builtin; expose the command as 'all' via alias
all = all_cmd  # type: ignore[assignment]


# ---- Exit code helper -----------------------------------------------------

def _exit_code(exc: BaseException) -> int:
    if isinstance(exc, FileNotFoundError):
        return 2
    if isinstance(exc, ModuleNotFoundError):
        return 3
    if isinstance(exc, ExcelParseError):
        return 4
    return 1


if __name__ == "__main__":
    main()
