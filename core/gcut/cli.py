"""Command-line entry point.

    python -m gcut INPUT.gcode [--svg OUT.svg] [--json OUT.json]
                   [--blade-offset MM] [--max-segment MM] [--z-down MM]

Prints one path string per cut subpath to stdout. With --svg, also writes a
preview you can open in a browser to check the translation without a machine.
"""

from __future__ import annotations

import argparse
import json
import sys

from . import parse, build_subpaths, apply_offset_all, to_path_data, to_svg, bounds


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gcut", description="G-code to Cricut-style cut paths")
    ap.add_argument("input", help="G-code file (use - for stdin)")
    ap.add_argument("--svg", help="write an SVG preview here")
    ap.add_argument("--json", help="write subpaths as JSON here")
    ap.add_argument("--blade-offset", type=float, default=0.0,
                    help="drag-knife offset in mm (0 = off)")
    ap.add_argument("--corner-threshold", type=float, default=20.0,
                    help="corner angle (deg) above which to swivel")
    ap.add_argument("--max-segment", type=float, default=0.25,
                    help="arc tessellation step in mm")
    ap.add_argument("--z-down", type=float, default=0.0,
                    help="Z at or below this means tool-down")
    args = ap.parse_args(argv)

    text = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()

    moves = parse(text, z_down_threshold=args.z_down)
    subs = build_subpaths(moves, max_segment=args.max_segment)
    if args.blade_offset > 0:
        subs = apply_offset_all(subs, args.blade_offset, args.corner_threshold)

    paths = to_path_data(subs)
    for p in paths:
        print(p)

    minx, miny, maxx, maxy = bounds(subs)
    sys.stderr.write(
        f"[gcut] {len(subs)} subpath(s), {sum(len(s.points) for s in subs)} points, "
        f"extent {maxx - minx:.1f} x {maxy - miny:.1f} mm\n"
    )

    if args.svg:
        with open(args.svg, "w", encoding="utf-8") as fh:
            fh.write(to_svg(subs))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump([s.points for s in subs], fh, indent=2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
