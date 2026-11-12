"""Drag-knife (tangential blade) corner compensation.

A drag knife's cutting tip sits a small distance *behind* the spindle axis —
the "blade offset", typically 0.25–1.0 mm. On a straight line this doesn't
matter: the tip simply trails the carriage. At a corner, though, the blade is
still pointing along the *old* direction, so a sharp turn gets rounded or torn
unless the blade is swivelled into the new direction first.

The standard fix is a *swivel* (a.k.a. overcut): at each corner sharper than a
threshold, drive the carriage a little past the vertex along the incoming
direction and sweep a small arc of radius = offset, so the trailing tip rotates
to face the outgoing direction before the next segment starts.

This is the well-known pragmatic algorithm used by hobby cutter drivers. It is
an approximation — the exact tip path depends on blade geometry and material —
so treat the numbers as a starting point to refine against real cuts. Offset
compensation is applied only to closed/again-cut shapes where it matters; it is
fully optional (``offset = 0`` disables it).
"""

from __future__ import annotations

import math

from .toolpath import SubPath


def _unit(dx: float, dy: float) -> tuple[float, float]:
    d = math.hypot(dx, dy)
    if d < 1e-12:
        return (0.0, 0.0)
    return (dx / d, dy / d)


def _angle_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Signed turn angle from direction a to direction b, in radians (-pi..pi)."""
    dot = max(-1.0, min(1.0, a[0] * b[0] + a[1] * b[1]))
    ang = math.acos(dot)
    cross = a[0] * b[1] - a[1] * b[0]
    return ang if cross >= 0 else -ang


def apply_offset(
    sub: SubPath,
    offset: float,
    corner_threshold_deg: float = 20.0,
    swivel_steps: int = 4,
) -> SubPath:
    """Return a new SubPath with swivel loops inserted at sharp corners.

    ``offset``                blade offset in mm (0 disables, returns input)
    ``corner_threshold_deg``  only corners sharper than this get a swivel
    ``swivel_steps``          line segments used to approximate each swivel arc
    """

    if offset <= 0 or len(sub.points) < 3:
        return sub

    pts = sub.points
    thresh = math.radians(corner_threshold_deg)
    out: list[tuple[float, float]] = [pts[0]]

    n = len(pts)
    for i in range(1, n - 1):
        px, py = pts[i - 1]
        cx, cy = pts[i]
        nx, ny = pts[i + 1]

        din = _unit(cx - px, cy - py)
        dout = _unit(nx - cx, ny - cy)
        if din == (0.0, 0.0) or dout == (0.0, 0.0):
            out.append((cx, cy))
            continue

        turn = _angle_between(din, dout)
        if abs(turn) < thresh:
            out.append((cx, cy))
            continue

        # Overshoot the vertex along the incoming direction by `offset`, then
        # sweep the tip from the incoming heading to the outgoing heading.
        lead = (cx + din[0] * offset, cy + din[1] * offset)
        out.append(lead)

        base_ang = math.atan2(din[1], din[0])
        for s in range(1, swivel_steps + 1):
            a = base_ang + turn * (s / swivel_steps)
            out.append((cx + math.cos(a) * offset, cy + math.sin(a) * offset))
        # Rejoin the real corner so the outgoing segment starts clean.
        out.append((cx, cy))

    out.append(pts[-1])
    return SubPath(points=out)


def apply_offset_all(
    subpaths: list[SubPath],
    offset: float,
    corner_threshold_deg: float = 20.0,
) -> list[SubPath]:
    return [apply_offset(s, offset, corner_threshold_deg) for s in subpaths]
