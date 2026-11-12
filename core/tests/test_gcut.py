import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gcut import parse, build_subpaths, apply_offset, to_path_data, translate
from gcut.toolpath import SubPath


def test_square_z_controlled():
    gc = """
    G21
    G90
    G0 Z5
    G0 X10 Y10
    G1 Z-1
    G1 X30 Y10
    G1 X30 Y30
    G1 X10 Y30
    G1 X10 Y10
    G0 Z5
    """
    subs = build_subpaths(parse(gc))
    assert len(subs) == 1
    sp = subs[0]
    assert sp.points[0] == (10.0, 10.0)
    assert sp.closed
    # four corners + closing point back to start
    assert sp.points == [(10, 10), (30, 10), (30, 30), (10, 30), (10, 10)]


def test_inch_units_convert_to_mm():
    gc = "G20\nG90\nG0 Z1\nG0 X0 Y0\nG1 Z-1\nG1 X1 Y0\n"
    subs = build_subpaths(parse(gc))
    # 1 inch -> 25.4 mm
    assert math.isclose(subs[0].points[-1][0], 25.4, abs_tol=1e-6)


def test_relative_mode():
    gc = "G21\nG91\nG1 Z-1\nG1 X5 Y0\nG1 X0 Y5\n"
    # G91: moves accumulate. Tool down via Z<=0.
    subs = build_subpaths(parse(gc))
    pts = subs[0].points
    assert pts[-1] == (5.0, 5.0)


def test_m3_m5_tool_control_and_two_subpaths():
    gc = """
    G21
    G90
    M3
    G1 X0 Y0
    G1 X10 Y0
    M5
    G0 X20 Y0
    M3
    G1 X30 Y0
    M5
    """
    subs = build_subpaths(parse(gc))
    assert len(subs) == 2
    assert subs[0].points == [(0, 0), (10, 0)]
    assert subs[1].points[-1] == (30, 0)


def test_arc_tessellation_stays_on_radius():
    gc = "G21\nG90\nM3\nG0 X10 Y20\nM3\nG2 X30 Y20 I10 J0\n"
    # semicircle radius 10 about (20,20)
    subs = build_subpaths(parse(gc), max_segment=0.5)
    for (x, y) in subs[0].points:
        assert math.isclose(math.hypot(x - 20, y - 20), 10.0, abs_tol=0.05)


def test_path_data_format_uses_spaces_and_absolute():
    subs = [SubPath(points=[(0, 0), (10, 0), (10, 10), (0, 0)])]
    (d,) = to_path_data(subs)
    assert "," not in d
    assert d.startswith("M 0 0 L 10 0")
    assert d.endswith("Z")  # closed


def test_knife_offset_inserts_points_at_corner():
    square = SubPath(points=[(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
    out = apply_offset(square, offset=0.5, corner_threshold_deg=20)
    # swivels add points; the shape must have grown.
    assert len(out.points) > len(square.points)
    # endpoints preserved
    assert out.points[0] == (0, 0)
    assert out.points[-1] == (0, 0)


def test_knife_offset_zero_is_noop():
    square = SubPath(points=[(0, 0), (10, 0), (10, 10), (0, 0)])
    assert apply_offset(square, offset=0.0).points == square.points


def test_translate_endtoend():
    gc = "G21\nG90\nG0 Z5\nG0 X0 Y0\nG1 Z-1\nG1 X10 Y0\nG1 X10 Y10\n"
    paths, subs = translate(gc)
    assert len(paths) == 1
    assert paths[0].count("L") == 2


def test_comments_and_blank_lines_ignored():
    gc = "; a comment\n(inline)\n\nG21\nG90\nM3\nG1 X1 Y1 ; trailing\n"
    subs = build_subpaths(parse(gc))
    assert subs[0].points[-1] == (1.0, 1.0)


if __name__ == "__main__":
    import traceback
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
