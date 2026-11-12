"""Emit the toolpath in two forms.

* ``to_path_data`` — a restricted SVG path string using only ``M``/``L``/``Z``,
  absolute coordinates, space-separated (never commas). This matches the path
  dialect that the slicebug driver accepts, so the output can be fed straight
  into a driver-reuse backend. Curves are already tessellated to line segments
  upstream, so only M/L/Z are produced.

* ``to_svg`` — a standalone SVG for eyeballing the result in a browser. This is
  purely for verification; it is not sent to any machine.

Coordinates are millimetres. SVG's y-axis points down; cutters and G-code use
y-up, so ``to_svg`` flips y for display only. ``to_path_data`` leaves
coordinates in machine space.
"""

from __future__ import annotations

from .toolpath import SubPath


def _fmt(v: float, places: int = 4) -> str:
    s = f"{v:.{places}f}".rstrip("0").rstrip(".")
    return s if s not in ("", "-0") else "0"


def to_path_data(subpaths: list[SubPath], places: int = 4) -> list[str]:
    """One path string per subpath, M/L[...]/Z, absolute, space-separated."""

    out: list[str] = []
    for sub in subpaths:
        if len(sub.points) < 2:
            continue
        toks: list[str] = []
        first = True
        for (x, y) in sub.points:
            cmd = "M" if first else "L"
            toks.append(f"{cmd} {_fmt(x, places)} {_fmt(y, places)}")
            first = False
        if sub.closed:
            toks.append("Z")
        out.append(" ".join(toks))
    return out


def bounds(subpaths: list[SubPath]) -> tuple[float, float, float, float]:
    xs = [p[0] for s in subpaths for p in s.points]
    ys = [p[1] for s in subpaths for p in s.points]
    if not xs:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


def to_svg(subpaths: list[SubPath], margin: float = 5.0, stroke: float = 0.3) -> str:
    minx, miny, maxx, maxy = bounds(subpaths)
    w = (maxx - minx) + 2 * margin
    h = (maxy - miny) + 2 * margin
    if w <= 0 or h <= 0:
        w = h = 2 * margin

    def tx(x: float) -> float:
        return x - minx + margin

    def ty(y: float) -> float:
        # flip y for display (y-up -> y-down)
        return (maxy - y) + margin

    paths: list[str] = []
    for sub in subpaths:
        if len(sub.points) < 2:
            continue
        d = []
        for i, (x, y) in enumerate(sub.points):
            d.append(("M" if i == 0 else "L") + f" {tx(x):.3f} {ty(y):.3f}")
        if sub.closed:
            d.append("Z")
        paths.append(f'  <path d="{" ".join(d)}" fill="none" '
                     f'stroke="#c0392b" stroke-width="{stroke}"/>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{w:.2f}mm" height="{h:.2f}mm" '
        f'viewBox="0 0 {w:.3f} {h:.3f}">\n'
        f'  <rect width="{w:.3f}" height="{h:.3f}" fill="#fafafa"/>\n'
        + "\n".join(paths)
        + "\n</svg>\n"
    )
