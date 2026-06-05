"""Hierarchy parser for multi-sheet Excel projects (v0.5, SPEC §15).

Sheet naming convention: dots separate hierarchy levels.
  top_module            → top-level wrapper
  top_module.u_sub_a    → submodule instance "u_sub_a"
  top_module.u_sub_a.u_fifo → nested submodule
"""

from __future__ import annotations

from pathlib import Path

from excel2design.core.exceptions import (
    EmptyHierarchyError,
    OrphanChildError,
    RecursiveHierarchyError,
)
from excel2design.core.models import Module, Project
from excel2design.parsers.excel import parse_workbook, parse_defines


def parse_project(xlsx_path: Path | str) -> Project:
    """Parse a multi-sheet Excel into a Project with hierarchy tree.

    Steps:
      1. Parse all module sheets via parse_workbook()
      2. Parse @defines sheet via parse_defines()
      3. Build hierarchy tree from dotted sheet names
      4. Validate (orphan detection, cycle detection)
    """
    modules_list = parse_workbook(xlsx_path)
    defines = parse_defines(xlsx_path)

    # Build module dict keyed by sheet name
    # Module.name is the sheet name; for submodule sheets it's the full
    # dotted name (e.g. "sram_wrapper.u_ctrl").
    modules: dict[str, Module] = {}
    for m in modules_list:
        modules[m.source_sheet or m.name] = m

    # Build hierarchy: parent_sheet -> [child_sheet_names]
    hierarchy: dict[str, list[str]] = {}
    all_sheets = list(modules.keys())

    # First pass: identify all parent-child relationships
    for sheet in all_sheets:
        if "." not in sheet:
            continue  # top-level, no parent
        # parent is everything before the last dot
        parent = sheet.rsplit(".", 1)[0]
        hierarchy.setdefault(parent, []).append(sheet)

    # Validate: orphan children
    for parent in hierarchy:
        if parent not in modules:
            # Find which sheets reference this missing parent
            orphans = hierarchy[parent]
            raise OrphanChildError(orphans[0], parent)

    # Validate: recursive hierarchy (detect by checking for cycles)
    _check_no_cycles(all_sheets, hierarchy)

    # Validate: at least one top-level module
    top_modules = [s for s in all_sheets if "." not in s]
    if not top_modules:
        raise EmptyHierarchyError()

    return Project(
        modules=modules,
        hierarchy=hierarchy,
        defines=defines,
    )


def _check_no_cycles(sheets: list[str], hierarchy: dict[str, list[str]]) -> None:
    """Detect circular references in the hierarchy tree (DFS)."""
    visited: set[str] = set()
    path: list[str] = []

    def dfs(sheet: str) -> None:
        if sheet in path:
            cycle_start = path.index(sheet)
            cycle = path[cycle_start:] + [sheet]
            raise RecursiveHierarchyError(sheet, cycle)
        if sheet in visited:
            return
        visited.add(sheet)
        path.append(sheet)
        for child in hierarchy.get(sheet, []):
            dfs(child)
        path.pop()

    for sheet in sheets:
        if sheet not in visited:
            dfs(sheet)
