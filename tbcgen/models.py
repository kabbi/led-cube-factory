"""3D models for demos and docs: per-board GLB (kicad-cli) and polyhedra
assembled from those tiles (trimesh).

    python -m tbcgen model [boards...]       build/<board>/3d/<board>.glb (+ .png)
    python -m tbcgen shapes [shapes...]      build/shapes/<shape>.glb (+ .png)
                                             from shapes/<shape>.yaml

PNG previews are rendered with Blender when it's installed
(tools/render_glb.py); without it you get the GLBs only.

GLB frame as KiCad exports it with the board centre as origin: metres,
Y up (LED side), X = KiCad x, Z = KiCad y. Tiles are placed with their board
bottom on the polyhedron face, LEDs out, so neighbours meet along their
inner edges like on a real build.
"""
import itertools
import math
import shutil
from pathlib import Path

import numpy as np

from . import geometry as geo
from .config import BUILD, ROOT
from .outputs import KICAD_CLI, run

PHI = (1 + 5 ** 0.5) / 2


def export_glb(cfg, pcb, out):
    d = out / "3d"
    d.mkdir(exist_ok=True)
    glb = d / f"{cfg['name']}.glb"
    run([KICAD_CLI, "pcb", "export", "glb", "--force", "--subst-models",
         "--user-origin", "100x100mm",                     # board centre (templates too)
         "--include-tracks", "--include-pads", "--include-silkscreen",
         "--include-soldermask", "-o", glb, pcb])
    return glb


def render_png(glb, size=1200):
    """PNG preview next to the GLB, rendered by Blender (headless, Cycles CPU).
    Returns the path, or None when Blender isn't installed."""
    app = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    blender = shutil.which("blender") or (app if app.exists() else None)
    if not blender:
        return None
    png = glb.with_suffix(".png")
    run([blender, "-b", "--factory-startup", "-P", ROOT / "tools" / "render_glb.py",
         "--", glb, png, size])
    return png


# -- polyhedra (unit edge) -------------------------------------------------------

def _perms(v, even=False):
    """All sign combinations of all (cyclic if even) coordinate permutations."""
    orders = [(0, 1, 2), (1, 2, 0), (2, 0, 1)] if even else itertools.permutations(range(3))
    out = set()
    for o in orders:
        for s in itertools.product((1, -1), repeat=3):
            out.add(tuple(round(s[i] * v[o[i]], 9) for i in range(3)))
    return list(out)


def _prism(n):
    r = 1 / (2 * math.sin(math.pi / n))
    return [(r * math.cos(2 * math.pi * k / n), y, r * math.sin(2 * math.pi * k / n))
            for k in range(n) for y in (-0.5, 0.5)]


SHAPES = {
    "tetrahedron": [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)],
    "cube": _perms((1, 1, 1)),
    "octahedron": _perms((1, 0, 0)),
    "icosahedron": _perms((0, 1, PHI), even=True),
    "square-pyramid": [(1, 0, 1), (1, 0, -1), (-1, 0, 1), (-1, 0, -1), (0, 2 ** 0.5, 0)],
    "triangular-prism": _prism(3),
    "cuboctahedron": _perms((1, 1, 0)),
    "hexagonal-prism": _prism(6),
    "truncated-tetrahedron": [v for v in _perms((3, 1, 1)) if v[0] * v[1] * v[2] > 0],
    "truncated-octahedron": _perms((0, 1, 2)),
}
KINDS = {3: "tri", 4: "square", 6: "hex"}       # face size -> board shape


def polyhedron(name):
    """(vertices scaled to unit edge, faces as vertex-index loops, outward normals)."""
    v = np.array(SHAPES[name], float)
    d = [np.linalg.norm(a - b) for a, b in itertools.combinations(v, 2)]
    v /= min(x for x in d if x > 1e-9)
    v -= v.mean(axis=0)
    faces, seen = [], set()
    for i, j, k in itertools.combinations(range(len(v)), 3):
        n = np.cross(v[j] - v[i], v[k] - v[i])
        if np.linalg.norm(n) < 1e-9:
            continue
        n /= np.linalg.norm(n)
        side = (v - v[i]) @ n
        if side.max() > 1e-6:
            n, side = -n, -side
        if side.max() > 1e-6:
            continue                                   # not a supporting plane
        on = tuple(sorted(np.flatnonzero(abs(side) < 1e-6)))
        if on in seen:
            continue
        seen.add(on)
        c = v[list(on)].mean(axis=0)
        u = v[on[0]] - c
        u /= np.linalg.norm(u)
        w = np.cross(n, u)
        loop = sorted(on, key=lambda m: math.atan2((v[m] - c) @ w, (v[m] - c) @ u))
        faces.append((loop, n))
    return v, faces


# -- placement -------------------------------------------------------------------

def tile_outline(shape, edge_m):
    """Tile outline in the GLB frame (y = 0 is the board bottom)."""
    return np.array([(x, 0.0, y) for x, y in geo.outline(shape, edge_m)])


def fit(local, world, normal):
    """Rigid transform taking the tile outline onto a face, LED side (+Y) out."""
    best = None
    n = len(local)
    for loop in (list(world), list(world)[::-1]):
        for s in range(n):
            W = np.array(loop[s:] + loop[:s])
            pc, wc = local.mean(axis=0), W.mean(axis=0)
            U, _, Vt = np.linalg.svd((local - pc).T @ (W - wc))
            D = np.diag([1, 1, np.sign(np.linalg.det(Vt.T @ U.T))])
            R = Vt.T @ D @ U.T
            if R[:, 1] @ normal < 0.5:
                continue
            err = np.abs((local - pc) @ R.T + wc - W).max()
            if best is None or err < best[0]:
                best = (err, R, wc - R @ pc)
    err, R, t = best
    if err > 1e-6:
        raise ValueError(f"tile doesn't fit the face ({err * 1e3:.3f} mm off)")
    T = np.eye(4)
    T[:3, :3], T[:3, 3] = R, t
    return T


def tile_parts(glb):
    """A board GLB flattened to one mesh per material (instanced on every face)."""
    import trimesh
    scene = trimesh.load(glb, force="scene")
    groups = {}
    for node in scene.graph.nodes_geometry:
        T, g = scene.graph[node]
        m = scene.geometry[g]
        mat = getattr(m.visual, "material", None)
        key = getattr(mat, "name", None) or g
        groups.setdefault(key, (mat, []))[1].append(m.copy().apply_transform(T))
    parts = {}
    for key, (mat, meshes) in groups.items():
        merged = trimesh.util.concatenate([trimesh.Trimesh(m.vertices, m.faces, process=False)
                                           for m in meshes])
        if mat is not None:
            merged.visual = trimesh.visual.TextureVisuals(material=mat)
        parts[key] = merged
    return parts


def assemble(name, tiles):
    """tiles: {"tri" | "square" | "hex": (cfg, glb)}. Returns a trimesh Scene."""
    import trimesh
    v, faces = polyhedron(name)
    need = {len(loop) for loop, _ in faces}
    for k in need:
        if KINDS[k] not in tiles:
            raise ValueError(f"{name} needs a {KINDS[k]} board")
    edge = {k: tiles[k][0]["edge"] / 1000 for k in tiles}
    if len({edge[KINDS[k]] for k in need}) > 1:
        raise ValueError(f"{name}: its boards have different edge lengths")
    scale = edge[KINDS[next(iter(need))]]
    scene = trimesh.Scene()
    parts = {k: tile_parts(tiles[k][1]) for k in {KINDS[n] for n in need}}
    for f, (loop, normal) in enumerate(faces):
        kind = KINDS[len(loop)]
        T = fit(tile_outline(kind, scale), v[loop] * scale, normal)
        for key, mesh in parts[kind].items():
            geom = f"{kind}_{key}"
            if geom not in scene.geometry:
                scene.add_geometry(mesh, geom_name=geom, node_name=f"face{f}_{key}", transform=T)
            else:
                scene.graph.update(frame_to=f"face{f}_{key}", frame_from=scene.graph.base_frame,
                                   matrix=T, geometry=geom)
    return scene


def board_glb(name):
    """GLB of a built board (exported on first use)."""
    from . import config
    cfg = config.load_board(name)
    out = BUILD / cfg["name"]
    glb = out / "3d" / f"{cfg['name']}.glb"
    if not glb.exists():
        pcb = out / f"{cfg['name']}.kicad_pcb"
        if not pcb.exists():
            raise FileNotFoundError(f"{cfg['name']} isn't built: make build BOARDS={cfg['name']}")
        export_glb(cfg, pcb, out)
    return cfg, glb


def build_shape(scfg):
    """shapes/<name>.yaml -> build/shapes/<name>.glb (+ .png). Returns (glb, png)."""
    out = BUILD / "shapes"
    out.mkdir(parents=True, exist_ok=True)
    tiles = {kind: board_glb(name) for kind, name in scfg["boards"].items()}
    glb = out / f"{scfg['name']}.glb"
    assemble(scfg["solid"], tiles).export(glb)
    return glb, render_png(glb)
