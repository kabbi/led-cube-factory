import math

import numpy as np
import pytest

from tbcgen import models

FACES = {"tetrahedron": [3] * 4, "cube": [4] * 6, "octahedron": [3] * 8,
         "icosahedron": [3] * 20, "square-pyramid": [3] * 4 + [4],
         "triangular-prism": [3] * 2 + [4] * 3, "cuboctahedron": [3] * 8 + [4] * 6}


@pytest.mark.parametrize("name", models.SHAPES)
def test_polyhedra_have_regular_unit_faces(name):
    v, faces = models.polyhedron(name)
    assert sorted(len(loop) for loop, _ in faces) == FACES[name]
    for loop, n in faces:
        edges = [np.linalg.norm(v[a] - v[b]) for a, b in zip(loop, loop[1:] + loop[:1])]
        assert edges == pytest.approx([1.0] * len(loop))
        assert (v[loop].mean(axis=0)) @ n > 0               # normal points out


@pytest.mark.parametrize("shape,k", [("tri", 3), ("square", 4)])
def test_tile_fits_face_led_side_out(shape, k):
    v, faces = models.polyhedron("square-pyramid")
    loop, n = next(f for f in faces if len(f[0]) == k)
    T = models.fit(models.tile_outline(shape, 1.0), v[loop], n)
    assert np.allclose(T[:3, :3] @ T[:3, :3].T, np.eye(3))  # rigid
    assert T[:3, 1] @ n == pytest.approx(1.0)               # +Y (LEDs) along the normal


@pytest.mark.parametrize("name", __import__("tbcgen.config", fromlist=["x"]).all_shapes())
def test_shape_configs_match_their_solid(name):
    from tbcgen import config
    s = config.load_shape(name)                              # name check happens here
    kinds = {3: "tri", 4: "square"}
    need = {kinds[len(loop)] for loop, _ in models.polyhedron(s["solid"])[1]}
    assert set(s["boards"]) == need, f"{s['solid']} needs boards for {sorted(need)}"
    for kind, board in s["boards"].items():
        cfg = config.load_board(board)
        assert {"tri": "tri", "square": "square"}[kind] == cfg["shape"]
        assert cfg["edge"] == 30.0
