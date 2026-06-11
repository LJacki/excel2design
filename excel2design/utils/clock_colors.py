"""Clock-domain color mapping for diagrams.

Bright, saturated palettes: blue series for inputs, green for outputs.
Same clock name → same palette index, but different color per direction.

P0-4 fix: use ``hashlib.md5`` for the palette index (deterministic across
processes), not the built-in ``hash()`` which is randomised by
``PYTHONHASHSEED`` and would break SPEC §5.7 byte-stability.
"""

from __future__ import annotations

import hashlib

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


def _stable_index(clock: str) -> int:
    """Deterministic palette index for a clock name.

    Uses the first 4 hex digits of md5(clock) as an integer in [0, 2**16).
    This is stable across processes (no ``PYTHONHASHSEED`` dependence) and
    gives a uniform distribution across the 8-colour palette.
    """
    digest = hashlib.md5(clock.encode("utf-8")).hexdigest()[:4]
    return int(digest, 16) % len(_BLUE_PALETTE)


def clock_color(clock: str | None, *, is_input: bool = True) -> str:
    if not clock:
        return _NEUTRAL_COLOR
    idx = _stable_index(clock)
    return (_BLUE_PALETTE if is_input else _GREEN_PALETTE)[idx]
