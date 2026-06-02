#!/usr/bin/env python3
"""Generate JSON golden baselines for all fixtures under tests/fixtures/.

Run from repo root (after fixtures are present):
    python tools/gen_baseline.py

Outputs:
    tests/fixtures/expected/uart_rx.json
    tests/fixtures/expected/axi_crossbar.json
    tests/fixtures/expected/multi_clock.json
    tests/fixtures/expected/empty_ports.json

Each JSON is a byte-stable representation of the parsed Module tree. The
test_golden.py test compares these byte-for-byte against the current parse
output, ensuring parser behaviour doesn't drift.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

# Allow running as a script without installing
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from excel2design.core.models import Module
from excel2design.parsers.excel import parse_workbook

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures"
EXPECTED_DIR = FIXTURE_DIR / "expected"

FIXTURES = ["uart_rx", "axi_crossbar", "multi_clock", "empty_ports"]


def module_to_dict(m: Module) -> dict[str, Any]:
    """Convert a Module tree to a JSON-serializable dict (deterministic)."""
    return {
        "name": m.name,
        "source_sheet": m.source_sheet,
        "parameters": [
            {
                "name": p.name,
                "value": p.value,
                "width": p.width,
                "param_type": p.param_type.value,
                "comment": p.comment,
            }
            for p in m.parameters
        ],
        "ports": [
            {
                "name": p.name,
                "direction": p.direction.value,
                "width": {
                    "raw": p.width.raw,
                    "msb": p.width.msb,
                    "is_parameter": p.width.is_parameter,
                },
                "type": p.type.value,
                "default": p.default,
                "clock": p.clock,
                "reset_type": p.reset_type.value,
                "signed": p.signed,
                "is_interface": p.is_interface,
                "comment": p.comment,
            }
            for p in m.ports
        ],
    }


def main() -> int:
    EXPECTED_DIR.mkdir(parents=True, exist_ok=True)

    for name in FIXTURES:
        path = FIXTURE_DIR / f"{name}.xlsx"
        if not path.exists():
            print(f"SKIP: {path} not found (run tools/gen_fixtures.py first)")
            continue
        modules = parse_workbook(path)
        assert len(modules) == 1, f"{name}: expected 1 module, got {len(modules)}"
        data = module_to_dict(modules[0])
        out = EXPECTED_DIR / f"{name}.json"
        with out.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=False)
            f.write("\n")  # trailing newline for byte-stability
        print(f"Wrote {out} ({len(data['ports'])} ports)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
