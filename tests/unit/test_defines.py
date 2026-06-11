"""P1-1 unit tests for generators/defines.py (v0.5 .vh / .f generators)."""

from __future__ import annotations

from excel2design.core.models import Define
from excel2design.generators.defines import generate_f, generate_vh


def test_generate_vh_empty_returns_empty_string():
    assert generate_vh([], "top") == ""


def test_generate_vh_single_define_no_value():
    """A `define without a value must still emit the macro name."""
    defines = [Define(name="FIFO_READY", value="")]
    out = generate_vh(defines, "top")
    assert "`define FIFO_READY" in out
    # No value portion when the value is empty.
    assert "`define FIFO_READY " not in out


def test_generate_vh_aligned_columns():
    """All `define lines must align the name column for readability."""
    defines = [
        Define(name="A", value="1"),
        Define(name="LONG_NAME", value="32"),
    ]
    out = generate_vh(defines, "top")
    # Find the `define lines and check they're all the same prefix length.
    lines = [ln for ln in out.splitlines() if ln.startswith("`define ")]
    assert len(lines) == 2
    # Both should have the same padding after the name (aligned).
    a_pos = lines[0].index("A")
    b_pos = lines[1].index("LONG_NAME")
    # The value column starts at the same position (one space after the longest name).
    a_val = lines[0][a_pos + len("A"):].strip()
    b_val = lines[1][b_pos + len("LONG_NAME"):].strip()
    assert a_val == "1"
    assert b_val == "32"


def test_generate_vh_header_includes_module_name():
    out = generate_vh([Define(name="X", value="1")], "my_module")
    assert "my_module.vh" in out
    assert "v0.5" in out  # version marker


def test_generate_f_empty_returns_empty_string():
    assert generate_f([], "top") == ""


def test_generate_f_one_module_per_line():
    out = generate_f(["top", "u_ctrl"], "my_project")
    lines = out.splitlines()
    rtl_lines = [ln for ln in lines if ln.startswith("rtl/")]
    assert rtl_lines == ["rtl/top.v", "rtl/u_ctrl.v"]


def test_generate_f_strips_hierarchy_prefix():
    """A sheet named 'top.u_ctrl' should appear as 'u_ctrl.v' in the filelist."""
    out = generate_f(["top", "top.u_ctrl", "top.u_ctrl.u_fifo"], "top")
    rtl_lines = [ln for ln in out.splitlines() if ln.startswith("rtl/")]
    assert rtl_lines == ["rtl/top.v", "rtl/u_ctrl.v", "rtl/u_fifo.v"]


def test_generate_f_header_includes_project_name():
    out = generate_f(["a"], "my_project")
    assert "my_project.f" in out
