"""Core data models per SPEC §3.

Three dataclasses plus a few enums. The Module is the top-level entity returned
by the Excel parser; generators consume a Module to emit HTML/SVG/Excalidraw/
Verilog artifacts.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from excel2design.parsers.width import PortWidth


class Direction(Enum):
    INPUT = "input"
    OUTPUT = "output"
    INOUT = "inout"

    @classmethod
    def parse(cls, s: str) -> "Direction":
        v = (s or "").strip().lower()
        for d in cls:
            if d.value == v:
                return d
        from excel2design.core.exceptions import PortValidationError
        raise PortValidationError(
            f"非法 direction: '{s}'",
            suggestion="direction 必须是 input / output / inout",
        )


class SignalType(Enum):
    WIRE = "wire"
    REG = "reg"
    LOGIC = "logic"

    @classmethod
    def parse(cls, s: str, direction: "Direction") -> "SignalType":
        v = (s or "").strip().lower()
        if not v:
            # Default per SPEC: output→reg, input→wire, inout→wire
            if direction == Direction.OUTPUT:
                return SignalType.REG
            return SignalType.WIRE
        for t in cls:
            if t.value == v:
                return t
        from excel2design.core.exceptions import PortValidationError
        raise PortValidationError(
            f"非法 type: '{s}'",
            suggestion="type 必须是 wire / reg / logic",
        )


class ResetType(Enum):
    SYNC = "sync"
    ASYNC = "async"
    NONE = "none"

    @classmethod
    def parse(cls, s: str) -> "ResetType":
        v = (s or "").strip().lower()
        if not v:
            return cls.SYNC  # default
        for r in cls:
            if r.value == v:
                return r
        from excel2design.core.exceptions import PortValidationError
        raise PortValidationError(
            f"非法 reset_type: '{s}'",
            suggestion="reset_type 必须是 sync / async / none",
        )


class ParamType(Enum):
    PARAMETER = "parameter"
    LOCALPARAM = "localparam"

    @classmethod
    def parse(cls, s: str) -> "ParamType":
        v = (s or "").strip().lower()
        if not v:
            return cls.PARAMETER  # default
        for p in cls:
            if p.value == v:
                return p
        from excel2design.core.exceptions import PortValidationError
        raise PortValidationError(
            f"非法 param_type: '{s}'",
            suggestion="param_type 必须是 parameter / localparam",
        )


@dataclass
class Port:
    name: str
    direction: Direction
    width: PortWidth
    type: SignalType
    default: Optional[str] = None
    clock: Optional[str] = None
    reset_type: ResetType = ResetType.SYNC
    signed: bool = False
    is_interface: bool = False
    comment: Optional[str] = None


@dataclass
class Parameter:
    name: str
    value: str
    width: Optional[str] = None
    param_type: ParamType = ParamType.PARAMETER
    comment: Optional[str] = None


@dataclass
class Module:
    name: str
    ports: list[Port] = field(default_factory=list)
    parameters: list[Parameter] = field(default_factory=list)
    source_file: Optional[Path] = None
    source_sheet: str = ""

    # ---- Lookup helpers ------------------------------------------------

    def inputs(self) -> list[Port]:
        return [p for p in self.ports if p.direction == Direction.INPUT]

    def outputs(self) -> list[Port]:
        return [p for p in self.ports if p.direction == Direction.OUTPUT]

    def inouts(self) -> list[Port]:
        return [p for p in self.ports if p.direction == Direction.INOUT]

    def regs(self) -> list[Port]:
        return [p for p in self.ports if p.type in (SignalType.REG, SignalType.LOGIC)]

    def wires(self) -> list[Port]:
        return [p for p in self.ports if p.type == SignalType.WIRE]

    def async_regs(self) -> list[Port]:
        return [p for p in self.regs() if p.reset_type == ResetType.ASYNC]

    def sync_regs(self) -> list[Port]:
        return [p for p in self.regs() if p.reset_type == ResetType.SYNC]

    def no_reset_regs(self) -> list[Port]:
        return [p for p in self.regs() if p.reset_type == ResetType.NONE]

    def primary_clock(self) -> Optional[str]:
        """Return the most common clock name among ports that declare a clock.

        Ties → first occurrence in Excel order. Returns None if no port has a clock.
        """
        clocks = [p.clock for p in self.ports if p.clock]
        if not clocks:
            return None
        # Counter.most_common returns descending frequency; on tie, insertion order.
        return Counter(clocks).most_common(1)[0][0]

    def parameter_names(self) -> set[str]:
        return {p.name for p in self.parameters}


# ---- v0.5: Define / Project / SubmoduleInstance ---------------------------


@dataclass
class Define:
    """A `define macro from the @defines sheet (SPEC §16)."""
    name: str
    value: str        # "" = define without value
    comment: Optional[str] = None


@dataclass
class SubmoduleInstance:
    """A sub-module instantiated within a parent module (SPEC §15.2)."""
    instance_name: str            # "u_ctrl"
    module: Module                # sub-module definition
    depth: int                    # 1 = direct child of wrapper
    parent_sheet: str             # parent's sheet name


@dataclass
class Project:
    """Top-level project container parsed from a multi-sheet Excel (SPEC §15.2).

    modules:   {sheet_name: Module} for all module sheets
    hierarchy: {parent_sheet: [child_sheet_names]} tree
    defines:   parsed @defines sheet entries
    """

    modules: dict[str, Module] = field(default_factory=dict)
    hierarchy: dict[str, list[str]] = field(default_factory=dict)
    defines: list[Define] = field(default_factory=list)

    @property
    def top_modules(self) -> list[str]:
        """Return sheet names of top-level modules (no '.' in name)."""
        return sorted([n for n in self.modules if "." not in n])

    def get_submodules(self, parent_sheet: str, depth_offset: int = 0,
                        recursive: bool = True) -> list[SubmoduleInstance]:
        """Return submodule instances for a parent. recursive=True includes all descendants."""
        children: list[SubmoduleInstance] = []
        for child_sheet in self.hierarchy.get(parent_sheet, []):
            child_mod = self.modules.get(child_sheet)
            if child_mod is None:
                continue
            instance_name = child_sheet.rsplit(".", 1)[-1]
            children.append(SubmoduleInstance(
                instance_name=instance_name,
                module=child_mod,
                depth=depth_offset + 1,
                parent_sheet=parent_sheet,
            ))
            if recursive:
                children.extend(self.get_submodules(child_sheet, depth_offset + 1, recursive=True))
        return children

    def walk_bfs(self) -> list[str]:
        """BFS traversal: top modules first, then children, etc. (SPEC §8.4)."""
        result: list[str] = []
        queue = list(self.top_modules)
        while queue:
            sheet = queue.pop(0)
            if sheet not in result:
                result.append(sheet)
            for child in sorted(self.hierarchy.get(sheet, [])):
                if child not in result:
                    queue.append(child)
        return result
