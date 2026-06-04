"""Clock-domain color mapping for diagrams.

Bright, saturated palettes: blue series for inputs, green for outputs.
Same clock name → same palette index, but different color per direction.
"""

from __future__ import annotations

_BLUE_PALETTE = [
    "#00B0FF",  # bright sky blue
    "#40C4FF",  # light blue
    "#00E5FF",  # cyan
    "#18FFFF",  # aqua
    "#0091EA",  # vivid blue
    "#03A9F4",  # light blue
    "#00BCD4",  # teal-cyan
    "#4FC3F7",  # soft blue
]

_GREEN_PALETTE = [
    "#00E676",  # bright green
    "#76FF03",  # lime
    "#69F0AE",  # mint
    "#B9F6CA",  # pale green
    "#C6FF00",  # yellow-green
    "#64DD17",  # vivid green
    "#AEEA00",  # chartreuse
    "#00C853",  # emerald
]

_NEUTRAL_COLOR = "#999999"


def clock_color(clock: str | None, *, is_input: bool = True) -> str:
    if not clock:
        return _NEUTRAL_COLOR
    idx = hash(clock) % len(_BLUE_PALETTE)
    return (_BLUE_PALETTE if is_input else _GREEN_PALETTE)[idx]
