"""Clock-domain color mapping for diagrams.

Each unique clock name gets a deterministic color from a fixed palette.
Ports without a clock assignment use a neutral gray.
"""

from __future__ import annotations

_CLOCK_PALETTE = [
    "#2E86C1",  # blue
    "#E74C3C",  # red
    "#27AE60",  # green
    "#8E44AD",  # purple
    "#F39C12",  # orange
    "#1ABC9C",  # teal
    "#D35400",  # dark orange
    "#2980B9",  # dark blue
]

_NEUTRAL_COLOR = "#888888"  # gray — ports without a clock


def clock_color(clock: str | None) -> str:
    """Return a deterministic color for a clock name.

    Same clock name always returns the same color across runs.
    None / empty → neutral gray.
    """
    if not clock:
        return _NEUTRAL_COLOR
    return _CLOCK_PALETTE[hash(clock) % len(_CLOCK_PALETTE)]
