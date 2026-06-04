"""Clock-domain color mapping for diagrams.

Two palettes: vibrant blue series for inputs, vibrant green for outputs.
Same clock name → same palette index, but different color per direction.
Ports without a clock assignment use neutral gray.
"""

from __future__ import annotations

_BLUE_PALETTE = [
    "#2196F3",  # material blue
    "#00BCD4",  # cyan
    "#42A5F5",  # light blue
    "#26C6DA",  # bright cyan
    "#448AFF",  # indigo-blue
    "#40C4FF",  # sky blue
    "#1E88E5",  # medium blue
    "#18FFFF",  # aqua
]

_GREEN_PALETTE = [
    "#4CAF50",  # material green
    "#8BC34A",  # light green
    "#69F0AE",  # mint
    "#00E676",  # bright green
    "#76FF03",  # lime
    "#AEEA00",  # yellow-green
    "#64DD17",  # vivid green
    "#B2FF59",  # pale green
]

_NEUTRAL_COLOR = "#999999"


def clock_color(clock: str | None, *, is_input: bool = True) -> str:
    if not clock:
        return _NEUTRAL_COLOR
    idx = hash(clock) % len(_BLUE_PALETTE)
    return (_BLUE_PALETTE if is_input else _GREEN_PALETTE)[idx]
