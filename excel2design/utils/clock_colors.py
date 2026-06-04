"""Clock-domain color mapping for diagrams.

Two palettes: blue series for inputs, green series for outputs.
Same clock name → same palette index, but different color per direction.
Ports without a clock assignment use neutral gray.
"""

from __future__ import annotations

_BLUE_PALETTE = [
    "#2E86C1",  # blue
    "#1A5276",  # dark blue
    "#2980B9",  # medium blue
    "#2471A3",  # steel blue
    "#5DADE2",  # light blue
    "#85C1E9",  # sky blue
    "#3498DB",  # bright blue
    "#1F618D",  # navy
]

_GREEN_PALETTE = [
    "#27AE60",  # green
    "#1E8449",  # dark green
    "#229954",  # forest green
    "#2ECC71",  # emerald
    "#58D68D",  # light green
    "#82E0AA",  # mint
    "#28B463",  # medium green
    "#196F3D",  # deep green
]

_NEUTRAL_COLOR = "#888888"  # gray — ports without a clock


def clock_color(clock: str | None, *, is_input: bool = True) -> str:
    """Return a deterministic color for a clock name × direction.

    Same clock name × same direction always returns the same color.
    None / empty → neutral gray.
    """
    if not clock:
        return _NEUTRAL_COLOR
    idx = hash(clock) % len(_BLUE_PALETTE)
    return (_BLUE_PALETTE if is_input else _GREEN_PALETTE)[idx]
