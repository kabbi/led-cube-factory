import math

import pytest

from tbcgen import geometry as geo


@pytest.mark.parametrize("shape,n", [("tri", 3), ("square", 4), ("hex", 6)])
def test_ports_on_edge_midpoints_clockwise_from_top(shape, n):
    ports = geo.ports(shape, 30)
    assert [p.index for p in ports] == list(range(1, n + 1))
    r = geo.inradius(shape, 30)
    for p in ports:
        assert math.hypot(p.x, p.y) == pytest.approx(r)
    assert ports[0].y < 0                       # P1 faces up
    angles = [(p.angle + 90 + 1e-6) % 360 for p in ports]
    assert angles == sorted(angles)             # clockwise on screen


def test_square_matches_led_board_v5():
    vs = geo.outline("square", 30)
    assert sorted({round(abs(c), 6) for v in vs for c in v}) == [15.0]
    ports = geo.ports("square", 30)
    assert [(round(p.x, 6), round(p.y, 6)) for p in ports] == [(0, -15), (15, 0), (0, 15), (-15, 0)]


@pytest.mark.parametrize("shape,leds,count", [
    ("square", {"cols": 4, "rows": 4, "pitch": 7.112}, 16),
    ("square", {"cols": 8, "rows": 8, "pitch": 3.4}, 64),
    ("hex", {"rings": 3, "pitch": 4}, 19),
    ("tri", {"rows": 5, "pitch": 4}, 15),
])
def test_led_grid_counts_and_centred(shape, leds, count):
    chain = geo.chain(shape, leds)
    assert len(chain) == count
    assert sum(L.x for L in chain) / count == pytest.approx(0, abs=1e-9)
    assert sum(L.y for L in chain) / count == pytest.approx(0, abs=1e-9)


def test_raster_vs_serpentine():
    leds = {"cols": 3, "rows": 2, "pitch": 1}
    raster = geo.chain("square", dict(leds, chain="raster"))
    snake = geo.chain("square", dict(leds, chain="serpentine"))
    assert [L.x for L in raster] == [-1, 0, 1, -1, 0, 1]
    assert [L.x for L in snake] == [-1, 0, 1, 1, 0, -1]
    assert {L.flow for L in raster} == {1}


def test_edge_rotations_turn_outer_leds_towards_their_edges():
    rows = geo.led_rows("tri", {"rows": 4, "pitch": 6.2})
    rots = geo.edge_rotations("tri", 30, [p for r in rows for p in r], 3.5, 3.1)
    # apex as a diamond, slanted edges flat, bottom corners split, inside unturned
    assert [abs(r) for r in rots] == [45, 30, 30, 30, 0, 30, 15, 0, 0, 15]
    assert rots[1] == -rots[2] and rots[6] == -rots[9]      # mirror-symmetric
    assert geo.edge_rotations("square", 30, [(0, 0)], 3.5, 3.1) == [0.0]
