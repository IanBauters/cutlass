"""gcut — turn G-code into Cricut-style cut paths.

Pipeline:  G-code text -> parse() -> build_subpaths() -> [apply_offset] -> emit

The parsing, toolpath and emit stages are machine-independent: they produce the
geometry a cutter needs without touching the Bluetooth link or any encryption.
The separate (not-included) backend is what would hand these paths to the
machine via a driver-reuse approach.
"""

from .parser import parse, Move, Arc, ParseError
from .toolpath import build_subpaths, SubPath
from .knife import apply_offset, apply_offset_all
from .emit import to_path_data, to_svg, bounds

__all__ = [
    "parse", "Move", "Arc", "ParseError",
    "build_subpaths", "SubPath",
    "apply_offset", "apply_offset_all",
    "to_path_data", "to_svg", "bounds",
    "translate",
]

__version__ = "0.1.0"


def translate(text, *, units_z_down=0.0, max_segment=0.25, blade_offset=0.0,
              corner_threshold_deg=20.0):
    """Convenience one-shot: G-code text -> list of SVG-style path strings.

    Returns ``(path_strings, subpaths)`` so callers can also render an SVG.
    """
    moves = parse(text, z_down_threshold=units_z_down)
    subs = build_subpaths(moves, max_segment=max_segment)
    if blade_offset > 0:
        subs = apply_offset_all(subs, blade_offset, corner_threshold_deg)
    return to_path_data(subs), subs
