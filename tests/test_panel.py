import math

import pytest

from tbcgen import config
from tbcgen import panel as pnl

FREE = 3.73     # copper-free run next to every corner, as measured on the tiles


def layout(name):
    spec = pnl.load_panel(name)
    cfgs = {b: config.load_board(b) for row in spec["boards"] for b in row}
    slots = pnl.placements(spec, cfgs)
    polys = [pnl.tile_outline(cfgs[b], x, y, a) for b, x, y, a in slots]
    return spec, polys


def frame_of(polys, space):
    _, y0, _, y1 = pnl.bbox([p for poly in polys for p in poly])
    return {"top": y0 - space, "bottom": y1 + space}


@pytest.mark.parametrize("name", pnl.all_panels())
def test_panel_specs_name_real_boards(name):
    spec = pnl.load_panel(name)
    for row in spec["boards"]:
        for b in row:
            assert (config.BOARDS / f"{b}.yaml").exists(), b


@pytest.mark.parametrize("name", pnl.all_panels())
def test_boards_keep_their_distance(name):
    from shapely.geometry import Polygon
    spec, polys = layout(name)
    shapes = [Polygon(p) for p in polys]
    for i, a in enumerate(shapes):
        for b in shapes[i + 1:]:
            assert a.distance(b) == pytest.approx(spec["space"], abs=1e-6) or \
                a.distance(b) > spec["space"]


@pytest.mark.parametrize("name", pnl.all_panels())
def test_panel_fits_max_size(name):
    spec, polys = layout(name)
    x0, y0, x1, y1 = pnl.bbox([p for poly in polys for p in poly])
    # 5mm rails top and bottom, `space` from the boards
    w, h = x1 - x0, y1 - y0 + 2 * (5 + spec["space"])
    if "max_size" in spec:
        assert w <= spec["max_size"][0] and h <= spec["max_size"][1]


def test_triangles_nest_edge_to_edge():
    spec, polys = layout("tri30-3535x10-p6.2-shallow-rot-2x5")
    x0, _, x1, _ = pnl.bbox([p for poly in polys for p in poly])
    # five 30mm triangles in a row, slanted edges 2mm apart
    assert x1 - x0 == pytest.approx(30 + 4 * (15 + 2 / math.sin(math.radians(60))))


@pytest.mark.parametrize("name,count", [
    ("sq30-3535x16-p6.2-pvia-3x2", 2 * 4 + 2 * 3 + 2 * 6),       # sides, rows, rails
    ("tri30-3535x10-p6.2-shallow-rot-2x5", 2 * 8 + 2 * 3 + 2 * 4),
    ("tri30-mix-4", 2 * 3 + 2 * 4),
])
def test_tabs_at_both_ends_of_every_facing_edge(name, count):
    spec, polys = layout(name)
    tabs = pnl.place_tabs(polys, [FREE] * len(polys), spec["space"],
                          frame_of(polys, spec["space"]), 2.0, 1.0, 0.5)
    pnl.check_tabs(polys, tabs)
    assert len(tabs) == count


@pytest.mark.parametrize("name", pnl.all_panels())
def test_tabs_stay_off_the_connector(name):
    """Where a tab meets a board, it's within the copper-free run by a
    corner, short of the first copper by a hole radius and margin plus the
    least mill fillet (joint_cuts() checks the fillets as milled)."""
    from shapely.geometry import Point, Polygon
    spec, polys = layout(name)
    tabs = pnl.place_tabs(polys, [FREE] * len(polys), spec["space"],
                          frame_of(polys, spec["space"]), 2.0, 1.0, 0.5)
    hi = FREE - 0.25 - pnl.COPPER_MARGIN
    for poly, boards in tabs:
        for i in boards:
            edge = Polygon(polys[i]).exterior
            on = [v for v in poly if edge.distance(Point(v)) < 2 * pnl.TAB_OVERLAP]
            assert len(on) == 2
            for v in on:
                d = min(math.dist(v, c) for c in polys[i])
                assert pnl.VERTEX_MARGIN - 0.01 <= d <= hi - 0.5


def test_mousebites_cover_the_cut_without_crowding():
    seg = ((0.0, 0.0), (2.9, 0.0))
    holes = pnl.mousebites(seg, 0.5, 0.85, -0.25)
    xs = [x for x, _ in holes]
    assert xs[0] == pytest.approx(0) and xs[-1] == pytest.approx(2.9)
    gaps = [b - a for a, b in zip(xs, xs[1:])]
    assert max(gaps) <= 0.85 * 1.25 and min(gaps) >= 0.5 + pnl.MIN_WEB - 1e-9
    # board on the left of the cut (y up in shapely terms): holes go right
    assert all(y == pytest.approx(0.25) for _, y in holes) or \
        all(y == pytest.approx(-0.25) for _, y in holes)
    short = pnl.mousebites(((0.0, 0.0), (0.6, 0.0)), 0.5, 0.85, -0.25)
    assert len(short) == 1


def test_joint_cuts_follow_the_material():
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    tri = pnl.tile_outline({"shape": "tri", "edge": 30.0}, 0, 0, 0)
    a, b = tri[1], tri[2]       # the bottom edge, y = +13
    y = a[1]
    # board + a 1.5mm wide tab 1mm from the left corner, reaching 2mm down
    tab = box(min(a[0], b[0]) + 1.0, y - 0.01, min(a[0], b[0]) + 2.5, y + 2)
    sub = unary_union([Polygon(tri), tab, box(-20, y + 2, 20, y + 7)])
    cuts = pnl.joint_cuts([tri], sub, [FREE], 0.5)
    assert len(cuts) == 1
    (p, q) = cuts[0][1]
    xs = sorted([p[0], q[0]])
    assert xs[0] == pytest.approx(min(a[0], b[0]) + 1.0, abs=0.05)
    assert xs[1] == pytest.approx(min(a[0], b[0]) + 2.5, abs=0.05)


def test_joint_into_copper_is_refused():
    from shapely.geometry import Polygon, box
    from shapely.ops import unary_union
    tri = pnl.tile_outline({"shape": "tri", "edge": 30.0}, 0, 0, 0)
    y = tri[1][1]
    sub = unary_union([Polygon(tri), box(-3, y - 0.01, 3, y + 2)])    # mid-edge tab
    with pytest.raises(ValueError, match="reaches copper"):
        pnl.joint_cuts([tri], sub, [FREE], 0.5)
