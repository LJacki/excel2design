"""Golden baseline tests (SPEC §13.6 / Phase 1.5).

Each fixture is parsed and compared byte-for-byte to its expected JSON.
If a fixture legitimately changes, regenerate the baselines with:
    python tools/gen_baseline.py
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from excel2design.core.models import Module
from excel2design.parsers.excel import parse_workbook

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
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


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_golden_baseline(fixture_name: str) -> None:
    xlsx = FIXTURE_DIR / f"{fixture_name}.xlsx"
    expected = EXPECTED_DIR / f"{fixture_name}.json"

    assert xlsx.exists(), f"Missing fixture: {xlsx}"
    assert expected.exists(), f"Missing baseline: {expected}"

    modules = parse_workbook(xlsx)
    assert len(modules) == 1, f"{fixture_name}: expected 1 module, got {len(modules)}"
    actual = module_to_dict(modules[0])
    actual_json = json.dumps(actual, indent=2, ensure_ascii=False, sort_keys=False) + "\n"

    expected_json = expected.read_text(encoding="utf-8")

    if actual_json != expected_json:
        # Write actual to a temp location for debugging
        debug = expected.with_suffix(".actual.json")
        debug.write_text(actual_json, encoding="utf-8")
        pytest.fail(
            f"Baseline mismatch for {fixture_name}.\n"
            f"  actual   written to: {debug}\n"
            f"  expected at:        {expected}\n"
            f"Run: diff {expected} {debug}\n"
            f"Or regenerate with: python tools/gen_baseline.py"
        )


def test_all_fixtures_have_baselines() -> None:
    """Every .xlsx in fixtures/ should have a corresponding .json in expected/."""
    xlsx_files = sorted(p.stem for p in FIXTURE_DIR.glob("*.xlsx"))
    json_files = sorted(p.stem for p in EXPECTED_DIR.glob("*.json"))
    assert xlsx_files == json_files, (
        f"Mismatch between fixtures and baselines.\n"
        f"  xlsx files:  {xlsx_files}\n"
        f"  json files:  {json_files}\n"
        f"Run: python tools/gen_fixtures.py && python tools/gen_baseline.py"
    )
