"""Turn a flat list of :class:`~gcut.parser.Move` into subpaths.

A *subpath* is a run of points the blade travels with the tool down, i.e. one
continuous cut. Every tool-up travel ends the current subpath; the next cut
starts a new one. Arcs are tessellated here into short straight segments so the
rest of the pipeline only deals with polylines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math

from .parser import Move


@dataclass
class SubPath:
    points: list[tuple[float, float]] = field(default_factory=list)

    @property
    def closed(self) -> bool:
        if len(self.points) < 3:
            return False
        ax, ay = self.points[0]
        bx, by = self.points[-1]
        return math.hypot(ax - bx, ay - by) < 1e-6


def _tessellate_arc(
    start: tuple[float, float],
    end: tuple[float, float],
    cx: float,
    cy: float,
    clockwise: bool,
    max_segment: float,
) -> list[tuple[float, float]]:
    """Return intermediate+end points approximating an arc (start excluded)."""

    sx, sy = start
    ex, ey = end
    r = math.hypot(sx - cx, sy - cy)
    if r < 1e-9:
        return [end]

    a0 = math.atan2(sy - cy, sx - cx)
    a1 = math.atan2(ey - cy, ex - cx)
    sweep = a1 - a0
    if clockwise:
        while sweep >= 0:
            sweep -= 2 * math.pi
    else:
        while sweep <= 0:
            sweep += 2 * math.pi

    arc_len = abs(sweep) * r
    steps = max(1, int(math.ceil(arc_len / max_segment)))
    pts: list[tuple[float, float]] = []
    for k in range(1, steps + 1):
        a = a0 + sweep * (k / steps)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    pts[-1] = end  # land exactly on the commanded endpoint
    return pts


def build_subpaths(moves: list[Move], max_segment: float = 0.25) -> list[SubPath]:
    """Group moves into cut subpaths, tessellating arcs to ``max_segment`` mm."""

    subpaths: list[SubPath] = []
    current: SubPath | None = None
    pos = (0.0, 0.0)

    def add(pt: tuple[float, float]) -> None:
        # Drop zero-length segments (e.g. a plunge G1 Z-1 at the same X/Y, or
        # repeated coordinates) so they don't become duplicate points.
        if current.points and math.hypot(pt[0] - current.points[-1][0],
                                         pt[1] - current.points[-1][1]) < 1e-9:
            return
        current.points.append(pt)

    for mv in moves:
        if mv.kind == "travel":
            if current is not None and len(current.points) >= 2:
                subpaths.append(current)
            current = None
            pos = (mv.x, mv.y)
            continue

        # cut
        if current is None:
            current = SubPath(points=[pos])

        if mv.arc is not None:
            pts = _tessellate_arc(
                pos, (mv.x, mv.y), mv.arc.cx, mv.arc.cy, mv.arc.clockwise, max_segment
            )
            for p in pts:
                add(p)
        else:
            add((mv.x, mv.y))
        pos = (mv.x, mv.y)

    if current is not None and len(current.points) >= 2:
        subpaths.append(current)

    return subpaths
