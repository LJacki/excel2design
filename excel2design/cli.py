"""excel2design CLI — entry point per SPEC §6.

Usage:
    excel2design parse <excel> [--json]
    excel2design diagram <excel> <module> [--format {html,svg,excalidraw,all}] [--output <dir>]
    excel2design wrapper <excel> <module> [--output <file>]
    excel2design all <excel> <module> [--output <dir>]
    excel2design project <excel> -o <dir>     # v0.5: multi-file project

Exit codes (per SPEC §6):
    0 — success
    2 — Excel file not found
    3 — module/sheet not found
    4 — parsing error (incl. BadZipFile / InvalidFileException — P1-4 fix)
"""

from __future__ import annotations

import json
import sys
from functools import wraps
from pathlib import Path

import click

from excel2design.core.exceptions import ExcelParseError, ModuleNotFoundError as _ModuleNotFoundError
from excel2design.parsers.excel import get_module, parse_workbook
from excel2design.parsers.hierarchy import parse_project
from excel2design.generators.diagram_excalidraw import generate_excalidraw
from excel2design.generators.diagram_html import generate_html
from excel2design.generators.diagram_svg import generate_svg
from excel2design.generators.project_output import generate_all as generate_project_output
from excel2design.generators.verilog import generate_wrapper


# ---- Error handling (P0-1 fix: shared decorator, not 6× duplicated try/except) --


def _is_bad_zip_or_invalid_file(exc: BaseException) -> bool:
    """Detect openpyxl's BadZipFile / InvalidFileException without importing them
    (so we don't crash if openpyxl is missing for some reason)."""
    name = type(exc).__name__
    module = type(exc).__module__
    return (
        name in ("BadZipFile", "InvalidFileException")
        or module.endswith("zipfile")
    )


def _exit_code(exc: BaseException) -> int:
    # Custom module-not-found from the parser (must come before the built-in
    # ModuleNotFoundError check, since the custom one doesn't subclass it).
    if isinstance(exc, _ModuleNotFoundError):
        return 3
    if isinstance(exc, FileNotFoundError):
        return 2
    # Built-in ModuleNotFoundError — click 9.x maps it to exit 3, so we
    # preserve that for any code that happens to raise the stdlib one.
    if isinstance(exc, ModuleNotFoundError):
        return 3
    if isinstance(exc, ExcelParseError):
        return 4
    if _is_bad_zip_or_invalid_file(exc):
        return 4
    return 1


def _render_error(exc: BaseException) -> str:
    """Format an exception for the click error stream."""
    if isinstance(exc, ExcelParseError):
        return str(exc)  # already carries suggestion + location
    return f"{type(exc).__name__}: {exc}"


def catch_errors(func):
    """Decorator: catch any exception, render via _render_error, exit with the
    right code per SPEC §6. Replaces the 6× duplicated try/except blocks that
    used to live inside every subcommand (P0-1 fix).
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except click.exceptions.Exit:
            # click's own sys.exit() — let it propagate (carries the right code)
            raise
        except click.UsageError:
            raise  # let click handle usage errors with its own formatting
        except Exception as e:
            click.echo(_render_error(e), err=True)
            sys.exit(_exit_code(e))
    return wrapper


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
@catch_errors
def parse(excel: Path, as_json: bool) -> None:
    """Parse an Excel file and list all modules with summary."""
    if not excel.exists():
        raise FileNotFoundError(f"Excel file not found: {excel}")
    modules = parse_workbook(excel)

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
@click.argument("module_name", required=False, default=None)
@click.option(
    "--format", "fmt",
    type=click.Choice(["html", "svg", "excalidraw", "all"], case_sensitive=False),
    default="all",
    help="Diagram format to generate (default: all)",
)
@click.option(
    "--all", "all_modules", is_flag=True, default=False,
    help="Generate diagrams for all modules",
)
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=Path("./output"),
    help="Output directory (default: ./output)",
)
@catch_errors
def diagram(excel: Path, module_name: str | None, fmt: str, all_modules: bool, output: Path) -> None:
    """Generate box diagrams for one or all modules."""
    if all_modules:
        modules = parse_workbook(excel)
    elif module_name is None:
        raise click.UsageError("Missing argument MODULE_NAME or use --all for all modules.")
    else:
        modules = [_load_module(excel, module_name)]

    output.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for m in modules:
        if fmt in ("html", "all"):
            p = output / f"{m.name}.html"
            p.write_text(generate_html(m), encoding="utf-8", newline="\n")
            written.append(str(p))

        if fmt in ("svg", "all"):
            p = output / f"{m.name}.svg"
            p.write_text(generate_svg(m), encoding="utf-8", newline="\n")
            written.append(str(p))

        if fmt in ("excalidraw", "all"):
            p = output / f"{m.name}.excalidraw"
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
@catch_errors
def wrapper(excel: Path, module_name: str, output: Path | None) -> None:
    """Generate a Verilog wrapper for a module."""
    m = _load_module(excel, module_name)

    out_path = output or Path(f"./{module_name}.v")
    # P1-5 fix: ensure parent dir exists, so single-file output works
    # even when --output points to a not-yet-created directory.
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
@catch_errors
def all_cmd(excel: Path, module_name: str, output: Path) -> None:
    """Generate all 3 diagrams + the Verilog wrapper."""
    m = _load_module(excel, module_name)

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


# ---- project (v0.5) -------------------------------------------------------


@main.command()
@click.argument("excel", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(file_okay=False, path_type=Path),
              default=Path("output"), help="Output root directory")
@catch_errors
def project(excel: Path, output: Path) -> None:
    """Generate complete project from multi-sheet Excel.

    Creates define/, filelist/, rtl/, doc/ under output/<top_module>/.
    """
    proj = parse_project(excel)

    generated = generate_project_output(proj, output)
    for f in generated:
        click.echo(f"  {f}")
    click.echo(f"\nGenerated {len(generated)} files in {output}/")


if __name__ == "__main__":
    main()
