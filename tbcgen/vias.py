"""Planned LED power vias: one pad-relative spot, repeated on every LED.

All LEDs share a rotation, so a via offset that works for one LED usually
works for all of them. Placing vias as a regular pattern (instead of
"nearest free spot", which depends on routing order) keeps the front tidy
and leaves the corridors the data chain needs:

  1. reserve corridors for the data chain: straight in-row links, and for
     each row change a band in the row gap for the return trace
  2. score candidate stubs (straight / 45 degree rays from each power pad)
     by how many LEDs they fit, against everything already on the board --
     template back copper, pads, edge, holes -- and the corridors
  3. pick the best compatible VDD/GND offset pair (and band position),
     then commit LED by LED, re-checking each; misfits take the next-best
     offset, and the router's nearest-via search as a last resort
"""
import math

import numpy as np
import pcbnew
import shapely
from shapely.geometry import LineString, Point

RAYS = [(math.cos(math.radians(a)), math.sin(math.radians(a))) for a in range(0, 360, 45)]


def _mask(g, geom):
    m = np.zeros((g.ny, g.nx), bool)
    if not geom.is_empty:
        sl, w = g._window(geom)
        m[sl] = w
    return m


def plan(b):
    """b: BoardBuilder with grid initialised. Returns number of vias placed by pattern."""
    g, cfg = b.grid, b.cfg
    pins = cfg["_led"]["pins"]
    leds, n = b.leds, len(b.leds)
    hw, vr, clr = g.hw, g.via_r, b.rules["clearance"]
    hole = b.rules["via_drill"] + b.rules["hole_clearance"]
    D = lambda k, role: b.pad(b.fps[f"D{k}"], pins[role])
    xy = lambda pad: (pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y))
    rots = {b.fps[f"D{k}"].GetOrientationDegrees() for k in range(1, n + 1)}
    if len(rots) != 1:
        return 0                                # pattern needs one LED rotation

    # 1. data-chain corridors, one variant per return-band position
    links, returns = [], []
    for k in range(1, n):
        a, c = xy(D(k, "DOUT")), xy(D(k + 1, "DIN"))
        same_row = abs(leds[k - 1].y - leds[k].y) < 1e-6
        (links if same_row else returns).append((a, c, leds[k - 1].y, leds[k].y))
    row_pitch = min((r[3] - r[2] for r in returns), default=0)

    def corridors(frac):
        lines = [LineString([a, c]) for a, c, _, _ in links]
        for a, c, y0, y1 in returns:
            yb = b.cy + y0 + frac * (y1 - y0)
            lines.append(LineString([a, (a[0], yb), (c[0], yb), c]))
        geom = shapely.union_all(lines)
        return (_mask(g, geom.buffer(vr + clr + hw + g.res)),      # no via here
                _mask(g, geom.buffer(2 * hw + clr + g.res)))       # no stub here

    # candidate offsets: rays from the pad centre
    step = 2 * g.res
    dists = [float(d) for d in np.arange(vr + clr, 2.2, step)]
    cands = [(round(dx * d, 4), round(dy * d, 4)) for dx, dy in RAYS for d in dists]

    nets = {role: D(1, role).GetNetCode() for role in ("VDD", "GND")}

    def fits(role, k, off, vok, res_via, res_stub, own):
        px, py = xy(D(k, role))
        vx, vy = px + off[0], py + off[1]
        i, j = g.cell(vx, vy)
        if not (0 <= i < g.ny and 0 <= j < g.nx) or not vok[i, j] or res_via[i, j]:
            return False
        steps = max(2, int(math.hypot(*off) / (g.res / 2)))
        for s in range(steps + 1):
            ci, cj = g.cell(px + off[0] * s / steps, py + off[1] * s / steps)
            o = own[ci, cj]
            if (o != 0 and o != nets[role]) or res_stub[ci, cj]:
                return False
        return True

    def neighbour_vectors():
        vs = set()
        for L1 in leds:
            for L2 in leds:
                d = math.hypot(L2.x - L1.x, L2.y - L1.y)
                if 0 < d < 1.6 * cfg["leds"]["pitch"]:
                    vs.add((round(L2.x - L1.x, 4), round(L2.y - L1.y, 4)))
        return vs | {(0.0, 0.0)}

    pad_off = {role: (xy(D(1, role))[0] - (b.cx + leds[0].x), xy(D(1, role))[1] - (b.cy + leds[0].y))
               for role in nets}
    nbrs = neighbour_vectors()
    min_gap = max(2 * vr + clr, hole)

    def compatible(ov, og):
        # VDD via of one LED vs GND via of the same / a neighbouring LED
        ax, ay = pad_off["VDD"][0] + ov[0], pad_off["VDD"][1] + ov[1]
        bx, by = pad_off["GND"][0] + og[0], pad_off["GND"][1] + og[1]
        return all(math.hypot(bx + tx - ax, by + ty - ay) >= min_gap for tx, ty in nbrs)

    # 2. score every (band, offset) on the board as it is now
    vok0 = {role: g.via_ok(net) for role, net in nets.items()}
    own = g.owner["F.Cu"]
    best = None
    fracs = [0.5] if not returns else [0.25, 0.4, 0.5, 0.6, 0.75]
    for frac in fracs:
        res_via, res_stub = corridors(frac)
        fit = {role: {} for role in nets}
        for role in nets:
            for off in cands:
                ks = frozenset(k for k in range(1, n + 1)
                               if fits(role, k, off, vok0[role], res_via, res_stub, own))
                if ks:
                    fit[role][off] = ks
        top = {role: sorted(fit[role], key=lambda o: (-len(fit[role][o]), math.hypot(*o)))[:40]
               for role in nets}
        for ov in top["VDD"]:
            for og in top["GND"]:
                if not compatible(ov, og):
                    continue
                score = (len(fit["VDD"][ov] & fit["GND"][og]), -(math.hypot(*ov) + math.hypot(*og)))
                if best is None or score > best[0]:
                    best = (score, frac, ov, og, fit)
    if best is None:
        return 0
    (count, _), frac, ov, og, fit = best
    b.log(f"  power-via pattern: VDD {ov}, GND {og}, return band at {frac:.2f} of the row gap; "
          f"fits {count}/{n} LEDs as is")

    # 3. commit, re-checking against what's been placed so far
    res_via, res_stub = corridors(frac)
    pattern = {"VDD": ov, "GND": og}
    placed = 0
    misfits = []
    for k in range(1, n + 1):
        for role, net in nets.items():
            vok = g.via_ok(net)
            order = [pattern[role]] + sorted(fit[role], key=lambda o: (
                math.hypot(o[0] - pattern[role][0], o[1] - pattern[role][1]), -len(fit[role][o])))
            off = next((o for o in order
                        if fits(role, k, o, vok, res_via, res_stub, g.owner["F.Cu"])), None)
            pad = D(k, role)
            if off is None:
                misfits.append((pad, f"D{k}.{role}"))
                continue
            px, py = xy(pad)
            _stub_and_via(b, pad, (px, py), (px + off[0], py + off[1]))
            placed += 1
    # misfits: nearest free spot, still keeping out of the data corridors
    for pad, label in misfits:
        _escape_outside(b, pad, label, res_via, res_stub)
    b.log(f"  power vias: {placed} by pattern, {len(misfits)} by nearest search")
    return placed


def _stub_and_via(b, pad, a, v):
    g = b.grid
    net = pad.GetNet()
    t = pcbnew.PCB_TRACK(b.board)
    t.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
    t.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(v[0]), pcbnew.FromMM(v[1])))
    t.SetWidth(pcbnew.FromMM(b.rules["track_width"]))
    t.SetLayer(pcbnew.F_Cu)
    t.SetNet(net)
    b.board.Add(t)
    g.add_track("F.Cu", [a, v], pad.GetNetCode())
    via = pcbnew.PCB_VIA(b.board)
    via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(v[0]), pcbnew.FromMM(v[1])))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetWidth(pcbnew.FromMM(b.rules["via_diameter"]))
    via.SetDrill(pcbnew.FromMM(b.rules["via_drill"]))
    via.SetNet(net)
    b.board.Add(via)
    g.add_via(v[0], v[1], pad.GetNetCode())


def _escape_outside(b, pad, label, res_via, res_stub):
    """Nearest-via escape with the corridors temporarily blocked; if that
    finds nothing, a plain one."""
    from .router import RouteError
    g = b.grid
    novia, front = g.novia.copy(), g.owner["F.Cu"].copy()
    g.novia |= res_via
    g.owner["F.Cu"][res_stub & (front == 0)] = -1
    before = {t.m_Uuid.AsString() for t in b.board.GetTracks()}
    try:
        b.escape_to_plane(pad, label)
    except RouteError:
        g.novia, g.owner["F.Cu"] = novia, front
        b.escape_to_plane(pad, label)
        return
    # undo the temporary blocking, keep (re-register) the new copper
    g.novia, g.owner["F.Cu"] = novia, front
    for t in b.board.GetTracks():
        if t.m_Uuid.AsString() in before:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            g.add_via(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y), t.GetNetCode())
        else:
            g.add_track("F.Cu", [(pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)),
                                 (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))], t.GetNetCode())
