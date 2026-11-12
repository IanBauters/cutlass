"""Parse a practical subset of G-code into a flat list of motion events.

Supported words
---------------
  G0 / G00   rapid move      (treated as travel / tool-up unless Z/M says otherwise)
  G1 / G01   linear move     (cut / draw when the tool is down)
  G2 / G3    arc move        clockwise / counter-clockwise, I/J centre offsets
  G20 / G21  units           inches / millimetres
  G90 / G91  distance mode   absolute / relative
  M3 / M4    tool down       (pen down / blade engaged)
  M5         tool up
  Z          tool axis       height; <= z_down_threshold means "down"
  F          feed rate       carried through as the segment speed

Anything else (comments in ; or ( ), unknown words) is ignored rather than
rejected, so real-world files from Inkscape, LightBurn, etc. still load.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import re

MM_PER_INCH = 25.4

_WORD = re.compile(r"([A-Za-z])\s*([-+]?[0-9]*\.?[0-9]+)")


def _strip_comments(line: str) -> str:
    # ';' to end of line, and anything inside parentheses
    line = re.sub(r"\(.*?\)", " ", line)
    semi = line.find(";")
    if semi != -1:
        line = line[:semi]
    return line


@dataclass
class Move:
    """One resolved motion in millimetres, absolute coordinates."""

    kind: str                       # 'travel' or 'cut'
    x: float
    y: float
    # For arcs the parser has already resolved these; the toolpath layer
    # tessellates them. 'arc' is None for straight moves.
    arc: Optional["Arc"] = None
    feed: Optional[float] = None


@dataclass
class Arc:
    cx: float          # centre, absolute mm
    cy: float
    clockwise: bool


@dataclass
class ParseError(Exception):
    line_no: int
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"line {self.line_no}: {self.message}"


@dataclass
class ParserState:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    absolute: bool = True
    units_to_mm: float = 1.0        # 1.0 if already mm (G21), 25.4 if inches
    tool_down: bool = False
    feed: Optional[float] = None
    moves: list = field(default_factory=list)


def parse(text: str, z_down_threshold: float = 0.0) -> list[Move]:
    """Parse G-code text into a list of :class:`Move` in absolute millimetres.

    ``z_down_threshold``: a Z height at or below this counts as tool-down.
    Files that drive the tool with M3/M5 instead of Z work too.
    """

    st = ParserState()

    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = _strip_comments(raw).strip()
        if not line:
            continue

        words = _WORD.findall(line)
        if not words:
            continue

        # Collect axis words and the active G/M codes on this line.
        axis: dict[str, float] = {}
        gcodes: list[int] = []
        for letter, num in words:
            L = letter.upper()
            val = float(num)
            if L == "G":
                gcodes.append(int(round(val)))
            elif L == "M":
                m = int(round(val))
                if m in (3, 4):
                    st.tool_down = True
                elif m == 5:
                    st.tool_down = False
            elif L == "F":
                st.feed = val * st.units_to_mm
            elif L in ("X", "Y", "Z", "I", "J"):
                axis[L] = val

        # Modal settings first.
        for g in gcodes:
            if g == 20:
                st.units_to_mm = MM_PER_INCH
            elif g == 21:
                st.units_to_mm = 1.0
            elif g == 90:
                st.absolute = True
            elif g == 91:
                st.absolute = False

        motion = next((g for g in gcodes if g in (0, 1, 2, 3)), None)
        if motion is None and not axis:
            continue
        # A bare "X.. Y.." line repeats the previous motion mode; default G1
        # only makes sense once a motion has been seen, so treat bare coordinate
        # lines as the last motion. We keep it simple: no motion word + axis =>
        # same as previous motion mode, defaulting to G1.
        if motion is None:
            motion = getattr(st, "_last_motion", 1)
        st._last_motion = motion  # type: ignore[attr-defined]

        prev_x, prev_y = st.x, st.y

        def resolve(letter: str, base: float) -> float:
            if letter not in axis:
                return base
            v = axis[letter] * st.units_to_mm
            return v if st.absolute else base + v

        nx = resolve("X", st.x)
        ny = resolve("Y", st.y)
        if "Z" in axis:
            zv = axis["Z"] * st.units_to_mm
            st.z = zv if st.absolute else st.z + zv

        # Decide tool state. Z overrides when present on this file at all.
        down = st.tool_down or (st.z <= z_down_threshold * st.units_to_mm)
        # Rapids are travel by convention even if the tool is nominally down.
        if motion == 0:
            kind = "travel"
        else:
            kind = "cut" if down else "travel"

        if motion in (2, 3):
            if "I" not in axis and "J" not in axis:
                raise ParseError(line_no, "arc (G2/G3) needs I and/or J centre offset")
            i = axis.get("I", 0.0) * st.units_to_mm
            j = axis.get("J", 0.0) * st.units_to_mm
            arc = Arc(cx=prev_x + i, cy=prev_y + j, clockwise=(motion == 2))
            st.moves.append(Move(kind, nx, ny, arc=arc, feed=st.feed))
        else:
            st.moves.append(Move(kind, nx, ny, feed=st.feed))

        st.x, st.y = nx, ny

    return st.moves
