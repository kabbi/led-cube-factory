"""Panels: built boards, the same or mixed, laid out on one KiKit panel.

panels/<name>.yaml says which boards go where; the KiKit preset it names
(panels/<preset>.json) supplies rails/frame, tooling, fiducials, text and the
mousebite style. Layout and tabs are ours, not KiKit's: its grid wants one
board, and its tabs sit mid-edge, which on these tiles is all connector.

Layouts (all boards are placed by their bounding-box centre):
  grid  rows x cols, boards upright.
  tri   rows of triangles alternating apex up / apex down, slanted edges
        facing at `space`; odd rows mirrored so flat edges face flat edges.

Tabs go only where two edges face each other at `space` (or an edge faces
the rails/frame), one near each end of the edge, inside the copper-free
stretch next to the corner that every tile has (measured per board).
"""
import math

import yaml

from . import config, geometry

PANELS = config.ROOT / "panels"
OUT = config.BUILD / "panels"

VERTEX_MARGIN = 0.35    # mm, nearest mousebite hole centre to a board corner
COPPER_MARGIN = 0.25    # mm, mousebite hole edge to copper near the edge
PROBE_DEPTH = 0.6       # mm, how deep from the edge copper counts as "at the edge"
RAIL_OVERLAP = 0.5      # mm, how far a tab reaches into the rail/frame
TAB_OVERLAP = 0.05      # mm, how far a tab reaches into a board (clean union)
MIN_WEB = 0.25          # mm, least board between two mousebite holes


# -- spec ---------------------------------------------------------------------

def all_panels():
    return sorted(p.stem for p in PANELS.glob("*.yaml"))


def load_panel(name):
    path = PANELS / f"{name}.yaml"
    spec = yaml.safe_load(path.read_text())
    spec["name"] = name
    if "boards" not in spec:
        spec["boards"] = [[spec["board"]] * spec["cols"] for _ in range(spec["rows"])]
    spec.setdefault("layout", "grid")
    spec.setdefault("space", 2.0)
    spec.setdefault("tabs", {})
    spec["tabs"].setdefault("width", 2.0)
    return spec


# -- layout (pure geometry, mm, KiCad orientation: y down) ----------------------

def bbox(pts):
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def tile_outline(cfg, cx=0.0, cy=0.0, angle=0.0):
    """Board outline turned `angle` degrees about its bounding-box centre,
    which then sits at (cx, cy)."""
    pts = geometry.outline(cfg["shape"], cfg["edge"])
    x0, y0, x1, y1 = bbox(pts)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    return [(cx + (x - mx) * c - (y - my) * s, cy + (x - mx) * s + (y - my) * c)
            for x, y in pts]


def placements(spec, cfgs):
    """[(board, cx, cy, angle)] for every slot, bounding-box centres in mm."""
    s = spec["space"]
    rows = spec["boards"]
    out = []
    if spec["layout"] == "grid":
        sizes = [bbox(tile_outline(cfgs[b])) for row in rows for b in row]
        w = max(x1 - x0 for x0, _, x1, _ in sizes)
        h = max(y1 - y0 for _, y0, _, y1 in sizes)
        for r, row in enumerate(rows):
            for c, b in enumerate(row):
                out.append((b, c * (w + s) + w / 2, r * (h + s) + h / 2, 0.0))
    elif spec["layout"] == "tri":
        for b in {b for row in rows for b in row}:
            if cfgs[b]["shape"] != "tri":
                raise ValueError(f"{spec['name']}: layout tri needs triangles, {b} isn't")
        edge = max(cfgs[b]["edge"] for row in rows for b in row)
        h = edge * math.sqrt(3) / 2
        step = edge / 2 + s / math.sin(math.radians(60))   # slanted edges `s` apart
        for r, row in enumerate(rows):
            for k, b in enumerate(row):
                up = (r + k) % 2 == 0           # tiles are apex up as drawn
                out.append((b, edge / 2 + k * step, r * (h + s) + h / 2, 0.0 if up else 180.0))
    else:
        raise ValueError(f"{spec['name']}: unknown layout {spec['layout']!r}")
    return out


# -- tabs -----------------------------------------------------------------------

def _sub(a, b):
    return a[0] - b[0], a[1] - b[1]


def _unit(v):
    n = math.hypot(*v)
    return v[0] / n, v[1] / n


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def _along(p, u, d):
    return p[0] + u[0] * d, p[1] + u[1] * d


def _edges(poly):
    """(start, end, along-unit, outward normal) per edge."""
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    out = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        u = _unit(_sub(b, a))
        n = (u[1], -u[0])
        if _dot(n, _sub(a, (cx, cy))) < 0:
            n = (-n[0], -n[1])
        out.append((a, b, u, n))
    return out


def _ends(edge):
    """Both ends of an edge as (corner, unit pointing into the edge)."""
    a, b, u, _ = edge
    return [(a, u), (b, (-u[0], -u[1]))]


def _angle(u, v):
    return math.acos(max(-1.0, min(1.0, _dot(_unit(u), _unit(v)))))


def _foot(mill, along, side):
    """How far along the board edge the milling fillet reaches from a tab
    corner: the cutter can't get into the corner between the edge (pointing
    away from the tab) and the tab's side."""
    return mill / math.tan(_angle(along, side) / 2)


def place_tabs(polys, free, space, frame, width, mill, drill):
    """Tabs: [(tab polygon, [board indices it joins])].

    polys: board outlines (mm); free: per board, the copper-free length next
    to every corner; frame: {"top"/"bottom"/"left"/"right": coordinate of the
    rail's/frame's inner edge}, only the sides that have one; mill: the
    cutter radius (inside corners fill in that much).

    The joint is the tab plus the mill fillets either side of it, and the
    mousebites must cover all of it without reaching the first copper. So
    each tab starts VERTEX_MARGIN from its corner and gets the straight width
    that leaves room for the fillet beyond it, up to `width`. (Where corners
    meet, the gaps are narrower than the cutter and the junction stays solid
    anyway; joint_cuts() finds the joints as milled, this only has to leave
    room for them.)
    """
    tabs = []
    lo = VERTEX_MARGIN
    his = [f - drill / 2 - COPPER_MARGIN for f in free]

    # board to board: parallel edges facing each other `space` apart
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            for ea in _edges(polys[i]):
                for eb in _edges(polys[j]):
                    _, _, ua, na = ea
                    if abs(_cross(ua, eb[2])) > 1e-6 or _dot(na, eb[3]) > -0.999:
                        continue
                    if abs(_dot(_sub(eb[0], ea[0]), na) - space) > 1e-3:
                        continue
                    for pa, va in _ends(ea):
                        # the corner of B at this end of A's edge
                        pb, vb = min(_ends(eb), key=lambda e: abs(_dot(_sub(e[0], pa), va)))
                        shift = _dot(_sub(pb, pa), va)
                        if _dot(va, vb) < 0.999 or abs(shift) > 3 * space:
                            continue
                        tab = _bridge(pa, va, his[i], pb, vb, his[j], shift, width, mill, lo)
                        if tab is None:
                            raise ValueError(f"boards {i} and {j}: no tab fits by the corner at "
                                             f"({pa[0]:.1f}, {pa[1]:.1f})")
                        a0, a1, b0, b1 = tab
                        poly = [_along(a0, na, -TAB_OVERLAP), _along(a1, na, -TAB_OVERLAP),
                                _along(b1, na, TAB_OVERLAP), _along(b0, na, TAB_OVERLAP)]
                        tabs.append((poly, [i, j]))

    # board to rail/frame: an axis-aligned edge `space` from the rail
    normals = {"top": (0, -1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)}
    for i, poly in enumerate(polys):
        for e in _edges(poly):
            a, _, _, n = e
            for side, line in frame.items():
                nn = normals[side]
                if _dot(n, nn) < 0.999:
                    continue
                gap = (line - a[1]) * nn[1] if nn[1] else (line - a[0]) * nn[0]
                if abs(gap - space) > 1e-3:
                    continue
                w = min(width, his[i] - mill - lo)
                if w <= 0:
                    raise ValueError(f"board {i}: no tab fits in {free[i]:.2f}mm by its corners")
                for p, v in _ends(e):
                    c0, c1 = _along(p, v, lo), _along(p, v, lo + w)
                    reach = space + RAIL_OVERLAP
                    tabs.append(([_along(c0, n, -TAB_OVERLAP), _along(c1, n, -TAB_OVERLAP),
                                  _along(c1, n, reach), _along(c0, n, reach)], [i]))
    return tabs


def _bridge(pa, va, hia, pb, vb, hib, shift, width, mill, lo, step=0.02):
    """Widest tab between corner A (pa, edge direction va) and corner B,
    `shift` further along. B's end may slide along its edge relative to A's,
    skewing the tab, up to 60 degrees off square.

    Returns the tab's corners (a0, a1, b0, b1) or None."""
    best = None
    for k in range(-int(3 / step), int(3 / step) + 1):
        d = k * step                            # B's tab start minus A's, along the edge
        ta = max(lo, lo + shift - d)            # each start as close to its corner as allowed
        tb = ta + d - shift
        a0, b0 = _along(pa, va, ta), _along(pb, vb, tb)
        side = _sub(b0, a0)
        skew = abs(math.degrees(_angle(va, side)) - 90)
        if skew > 60:
            continue
        # the fillet past the far side of the tab, on each board
        w = min(width, hia - _foot(mill, va, side) - ta,
                hib - _foot(mill, va, _sub(a0, b0)) - tb)
        if w <= 0:
            continue
        key = (round(w, 3), -skew)
        if best is None or key > best[0]:
            best = (key, ta, tb, w)
    if best is None:
        return None
    _, ta, tb, w = best
    return (_along(pa, va, ta), _along(pa, va, ta + w),
            _along(pb, vb, tb), _along(pb, vb, tb + w))


def check_tabs(polys, tabs):
    """Every tab bridges only the boards it was made for and no two overlap."""
    from shapely.geometry import Polygon
    boards = [Polygon(p) for p in polys]
    shapes = []
    for poly, mine in tabs:
        t = Polygon(poly)
        for k, b in enumerate(boards):
            if k not in mine and t.intersects(b):
                raise ValueError(f"tab at {poly[0]} runs into board {k}")
        for s in shapes:
            if t.intersects(s):
                raise ValueError(f"tabs overlap at {poly[0]}")
        shapes.append(t)


def joint_cuts(polys, substrate, free, drill, probe=0.1, step=0.02):
    """Cut lines for the mousebites, from the panel as milled: every stretch
    of board edge with material just outside it (tab, fillet, a junction the
    cutter can't get into), trimmed to VERTEX_MARGIN from the corners.

    substrate: the milled panel outline, shapely, mm. Raises if a joint runs
    into a board's copper or a board isn't held at all.
    Returns [(board index, (start, end))], the board on the left of each line
    (KiKit offsets mousebites towards the left)."""
    from shapely.geometry import Point
    from shapely.prepared import prep
    sub = prep(substrate)
    cuts = []
    for i, poly in enumerate(polys):
        hi = free[i] - drill / 2 - COPPER_MARGIN
        mine = 0
        for a, b, u, n in _edges(poly):
            length = math.dist(a, b)
            ts = [k * step for k in range(int(length / step) + 1)]
            solid = [sub.contains(Point(_along(_along(a, u, t), n, probe))) for t in ts]
            runs, start = [], None
            for t, s in zip(ts + [None], solid + [False]):
                if s and start is None:
                    start = t
                elif not s and start is not None:
                    runs.append((start, prev))
                    start = None
                prev = t
            for t0, t1 in runs:
                if t1 > hi and t0 < length - hi:
                    raise ValueError(f"board {i}: joint at {t0:.2f}..{t1:.2f}mm along the edge "
                                     f"from ({a[0]:.1f}, {a[1]:.1f}) reaches copper")
                c0, c1 = max(t0, VERTEX_MARGIN), min(t1, length - VERTEX_MARGIN)
                if c1 - c0 < step:
                    continue                    # fillet wrapping the corner
                p, q = _along(a, u, c0), _along(a, u, c1)
                if _cross(_sub(q, p), (-n[0], -n[1])) < 0:
                    p, q = q, p
                cuts.append((i, (p, q)))
                mine += 1
        if mine == 0:
            raise ValueError(f"board {i} isn't held by anything")
    return cuts


def mousebites(seg, drill, spacing, offset):
    """Hole centres along a cut (board on its left): both ends, evenly in
    between, as near `spacing` apart as the length allows but never with
    less than MIN_WEB of board between holes; `offset` towards the board
    (negative: away from it, into the tab)."""
    (x0, y0), (x1, y1) = seg
    length = math.hypot(x1 - x0, y1 - y0)
    u = ((x1 - x0) / length, (y1 - y0) / length) if length else (1.0, 0.0)
    left = (-u[1], u[0])
    if length < drill + MIN_WEB:                    # one hole is all that fits
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2
        return [(mx + left[0] * offset, my + left[1] * offset)]
    n = max(1, round(length / spacing))
    while n > 1 and length / n < drill + MIN_WEB:
        n -= 1
    return [(x0 + (x1 - x0) * k / n + left[0] * offset, y0 + (y1 - y0) * k / n + left[1] * offset)
            for k in range(n + 1)]


# -- KiCad side -------------------------------------------------------------------

def edge_free(cfg, pcb):
    """Shortest copper-free run from any corner along its edges: pads and
    tracks on every copper layer within PROBE_DEPTH of the edge. (The planes
    keep the board's edge clearance everywhere, so they don't count.)"""
    import pcbnew
    from shapely.geometry import LineString, Point, Polygon
    from shapely.ops import unary_union
    board = pcbnew.LoadBoard(str(pcb))
    bb = board.GetBoardEdgesBoundingBox()
    poly = tile_outline(cfg, bb.GetCenter().x / 1e6, bb.GetCenter().y / 1e6)
    copper = []
    for layer in board.GetEnabledLayers().CuStack():
        for item in [*board.GetPads(), *board.GetTracks()]:
            if not item.IsOnLayer(layer):
                continue
            ps = pcbnew.SHAPE_POLY_SET()
            item.TransformShapeToPolygon(ps, layer, 0, 5000, pcbnew.ERROR_OUTSIDE)
            for k in range(ps.OutlineCount()):
                o = ps.Outline(k)
                copper.append(Polygon([(o.CPoint(m).x / 1e6, o.CPoint(m).y / 1e6)
                                       for m in range(o.PointCount())]))
    copper = unary_union(copper)
    free = math.inf
    for a, b in zip(poly, poly[1:] + poly[:1]):
        e = LineString([a, b])
        hit = copper.intersection(e.buffer(PROBE_DEPTH, cap_style=2))
        if hit.is_empty:
            continue
        ts = [e.project(Point(p)) for g in getattr(hit, "geoms", [hit])
              for p in g.exterior.coords]
        free = min(free, min(ts), e.length - max(ts))
    return free


def finest_rules(pcbs):
    """The board whose design rules are all at or below every other board's.

    KiKit takes the panel's rules from one board; with that one, panel DRC
    holds every board to limits it was built within. (Each board has passed
    its own DRC already; on the panel DRC is for the tabs and holes.)"""
    import json

    def limits(pcb):
        pro = json.loads(pcb.with_suffix(".kicad_pro").read_text())
        rules = pro["board"]["design_settings"]["rules"]
        nc = pro["net_settings"]["classes"][0]
        keys = ["min_clearance", "min_track_width", "min_via_diameter",
                "min_through_hole_diameter", "min_hole_to_hole", "min_hole_clearance",
                "min_copper_edge_clearance", "min_via_annular_width"]
        return [rules[k] for k in keys] + [nc["clearance"], nc["track_width"]]

    have = {b: limits(p) for b, p in pcbs.items()}
    for b, mine in sorted(have.items()):
        if all(m <= o for other in have.values() for m, o in zip(mine, other)):
            return b
    raise RuntimeError(f"no board's rules are the finest on every count: {sorted(have)}; "
                       "panel these separately")


def build(spec):
    """build/panels/<name>/<name>.kicad_pcb from already built boards."""
    import pcbnew
    from kikit import panelize_ui_impl as ki
    from kikit.panelize import Origin, Panel
    from shapely.affinity import scale
    from shapely.geometry import Polygon

    name = spec["name"]
    out = OUT / name
    out.mkdir(parents=True, exist_ok=True)
    pp = out / f"{name}.kicad_pcb"

    cfgs, pcbs = {}, {}
    for b in {b for row in spec["boards"] for b in row}:
        cfgs[b] = config.load_board(b)
        pcbs[b] = config.BUILD / b / f"{b}.kicad_pcb"
        if not pcbs[b].exists():
            raise RuntimeError(f"{b} isn't built yet: make all BOARDS={b}")
    free = {b: edge_free(cfgs[b], pcbs[b]) for b in cfgs}

    preset = ki.obtainPreset([str(PANELS / f"{spec['preset']}.json")])
    mm = pcbnew.FromMM
    space = spec["space"]
    framing = preset["framing"]
    framing["hspace"] = framing["vspace"] = mm(space)
    preset["text"]["text"] = preset["text"]["text"].replace("{panel}", name)
    cuts_p = preset["cuts"]
    if cuts_p["prolong"]:
        raise RuntimeError(f"{spec['preset']}: set cuts.prolong to 0, the cut lines "
                           "already cover the mill fillets")
    mill = preset["post"]["millradius"] / 1e6

    slots = placements(spec, cfgs)
    polys = [tile_outline(cfgs[b], x, y, a) for b, x, y, a in slots]
    x0, y0, x1, y1 = bbox([p for poly in polys for p in poly])
    ftype = framing["type"]
    frame = {}
    if ftype in ("railstb", "frame"):
        frame.update(top=y0 - space, bottom=y1 + space)
    if ftype in ("railslr", "frame"):
        frame.update(left=x0 - space, right=x1 + space)
    tabs = place_tabs(polys, [free[b] for b, *_ in slots], space, frame,
                      spec["tabs"]["width"], mill, cuts_p["drill"] / 1e6)
    check_tabs(polys, tabs)

    rules_from = finest_rules(pcbs)
    first = pcbnew.LoadBoard(str(pcbs[slots[0][0]]))
    panel = Panel(str(pp))
    panel.inheritDesignSettings(first)
    panel.inheritProperties(first)
    panel.inheritTitleBlock(first)
    panel.inheritLayerNames(first)
    for b, x, y, a in slots:
        panel.appendBoard(str(pcbs[b]), pcbnew.VECTOR2I(mm(x), mm(y)), origin=Origin.Center,
                          rotationAngle=pcbnew.EDA_ANGLE(a, pcbnew.DEGREES_T),
                          tolerance=mm(1), refRenamer=lambda n, ref: f"{ref}_{n + 1}",
                          inheritDrc=b == rules_from)
    # our outlines must be where KiKit put the boards, or the tabs miss
    for (b, *_), poly, s in zip(slots, polys, panel.substrates):
        mine = Polygon([(mm(x), mm(y)) for x, y in poly])
        if mine.hausdorff_distance(s.exterior()) > mm(0.02):
            raise RuntimeError(f"{b}: outline isn't the {cfgs[b]['shape']} the config describes")

    for poly, _ in tabs:
        panel.appendSubstrate(Polygon([(mm(x), mm(y)) for x, y in poly]))

    frame_cuts = ki.buildFraming(preset, panel)
    ki.buildTooling(preset, panel)
    ki.buildFiducials(preset, panel)
    for section in ["text", "text2", "text3", "text4"]:
        ki.buildText(preset[section], panel)
    ki.buildPostprocessing(preset["post"], panel)
    milled = scale(panel.boardSubstrate.substrates, 1e-6, 1e-6, origin=(0, 0))
    if cuts_p["type"] != "mousebites":
        raise RuntimeError(f"{spec['preset']}: cuts must be mousebites")
    drill, spacing, offset = (cuts_p[k] / 1e6 for k in ("drill", "spacing", "offset"))
    cuts = joint_cuts(polys, milled, [free[b] for b, *_ in slots], drill)
    for k, (_, seg) in enumerate(cuts):
        # not panel.makeMouseBites: it drops holes whose centre misses
        # material, i.e. the end ones on thin fillets -- exactly where a
        # joint still needs perforating
        for m, (x, y) in enumerate(mousebites(seg, drill, spacing, offset)):
            panel.addNPTHole(pcbnew.VECTOR2I(mm(x), mm(y)), mm(drill),
                             ref=f"MB_{k + 1}_{m + 1}", excludedFromPos=True)
    ki.makeOtherCuts(preset, panel, frame_cuts)
    ki.setStackup(preset["source"], panel)
    ki.setPageSize(preset["page"], panel, first)
    ki.positionPanel(preset["page"], panel)
    panel.save(reconstructArcs=preset["post"]["reconstructarcs"],
               refillAllZones=preset["post"]["refillzones"],
               edgeWidth=preset["post"]["edgewidth"])
    if panel.hasErrors():
        raise RuntimeError("\n".join(msg for _, msg in panel.errors))

    px0, py0, px1, py1 = panel.panelBBox()
    size = ((px1 - px0) / 1e6, (py1 - py0) / 1e6)
    limit = spec.get("max_size")
    if limit and (size[0] > limit[0] + 1e-6 or size[1] > limit[1] + 1e-6):
        raise RuntimeError(f"{name}: panel is {size[0]:.2f} x {size[1]:.2f} mm, "
                           f"over max_size {limit[0]} x {limit[1]}")
    return pp, cfgs, size, len(tabs)
