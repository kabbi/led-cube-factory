"""A small grid router for regular, sparse boards.

Model: one occupancy grid per routable copper layer. A cell holds the net
code that "owns" it (it lies within clearance + half track width of that
net's copper), 0 if free, -1 if blocked for everyone (edge, or two nets'
keep-outs overlapping). A track of net N may run its centreline through
cells that are 0 or N. Vias are through vias and additionally need room on
every routable layer, plus hole-to-hole spacing (the `novia` mask).

Search is A* over (layer, cell, heading) with 8-way moves, a small penalty per
turn (clean 45-degree routing) and a penalty per via. Results are snapped
polylines that callers turn into KiCad tracks/vias.

It's deliberately simple (no rip-up/reroute): route order is chosen by the
caller, and DRC on the finished board is the source of truth.
"""
import heapq
import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point

DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


class RouteError(RuntimeError):
    pass


class Grid:
    def __init__(self, outline_poly, layers, rules, router):
        self.res = router["grid"]
        self.rules = rules
        # layers: {name: cost multiplier, or None for obstacle-only layers}
        self.layers = list(layers)
        self.routable = [L for L, c in layers.items() if c is not None]
        self.layer_cost = {L: (c or 1.0) for L, c in layers.items()}
        self.hw = rules["track_width"] / 2
        self.via_r = rules["via_diameter"] / 2
        self.infl = rules["clearance"] + self.hw + self.res * 0.75
        x0, y0, x1, y1 = outline_poly.bounds
        self.x0, self.y0 = x0, y0
        self.nx = int(math.ceil((x1 - x0) / self.res)) + 1
        self.ny = int(math.ceil((y1 - y0) / self.res)) + 1
        self.X, self.Y = np.meshgrid(x0 + np.arange(self.nx) * self.res,
                                     y0 + np.arange(self.ny) * self.res)
        self.owner = {L: np.zeros((self.ny, self.nx), np.int32) for L in self.layers}
        self.novia = np.zeros((self.ny, self.nx), bool)
        inside = shapely.contains_xy(
            outline_poly.buffer(-(rules["edge_clearance"] + self.hw)), self.X, self.Y)
        for g in self.owner.values():
            g[~inside] = -1
        self.novia |= ~shapely.contains_xy(
            outline_poly.buffer(-(rules["edge_clearance"] + self.via_r)), self.X, self.Y)
        self.via_cost = router["via_cost"] / self.res
        self.turn_cost = router["turn_cost"] / self.res

    # -- grid <-> mm ---------------------------------------------------------
    def cell(self, x, y):
        return (int(round((y - self.y0) / self.res)), int(round((x - self.x0) / self.res)))

    def xy(self, i, j):
        return (self.x0 + j * self.res, self.y0 + i * self.res)

    def _window(self, geom):
        bx0, by0, bx1, by1 = geom.bounds
        i0 = max(0, int((by0 - self.y0) / self.res) - 1)
        i1 = min(self.ny, int((by1 - self.y0) / self.res) + 2)
        j0 = max(0, int((bx0 - self.x0) / self.res) - 1)
        j1 = min(self.nx, int((bx1 - self.x0) / self.res) + 2)
        sl = (slice(i0, i1), slice(j0, j1))
        return sl, shapely.contains_xy(geom, self.X[sl], self.Y[sl])

    # -- occupancy -------------------------------------------------------------
    def paint(self, layers, geom, net):
        """Register copper `geom` of `net` (net <= 0: belongs to nobody)."""
        sl, m = self._window(geom.buffer(self.infl))
        for L in layers:
            if L not in self.owner:
                continue
            sub = self.owner[L][sl]
            if net <= 0:
                sub[m] = -1
                continue
            clash = m & (sub != 0) & (sub != net)
            sub[m & (sub == 0)] = net
            sub[clash] = -1

    def block_vias(self, geom, extra=0.0):
        sl, m = self._window(geom.buffer(extra))
        self.novia[sl] |= m

    def add_hole(self, x, y, drill):
        r = self.rules
        self.block_vias(Point(x, y), drill / 2 + r["hole_clearance"] + r["via_drill"] / 2)

    def add_track(self, layer, pts, net, hw=None):
        hw = hw or self.hw
        geom = LineString(pts).buffer(hw) if len(pts) > 1 else Point(pts[0]).buffer(hw)
        self.paint([layer], geom, net)

    def add_via(self, x, y, net, r=None, drill=None):
        self.paint(self.layers, Point(x, y).buffer(r or self.via_r), net)
        self.add_hole(x, y, drill or self.rules["via_drill"])

    def via_ok(self, net):
        foreign = np.zeros((self.ny, self.nx), bool)
        for g in self.owner.values():
            foreign |= (g != 0) & (g != net)
        k = int(math.ceil((self.via_r - self.hw) / self.res))
        grown = foreign.copy()
        if k > 0:
            p = np.pad(foreign, k, constant_values=True)
            for di in range(-k, k + 1):
                for dj in range(-k, k + 1):
                    if di * di + dj * dj <= k * k:
                        grown |= p[k + di:k + di + self.ny, k + dj:k + dj + self.nx]
        return ~grown & ~self.novia

    # -- search ----------------------------------------------------------------
    def route(self, net, starts, goal_cells=None, goal_via=False, layers=None,
              max_expand=3_000_000):
        """A* from any of `starts` [(layer, (i, j))] to a goal.

        goal_cells: set of (layer_idx, flat_idx) to reach, or
        goal_via:   stop at the first cell where a through via fits (returns
                    a path ending with a via marker), used for plane escapes.
        Returns a list of (layer_name, i, j) cells, with a layer change
        between consecutive entries meaning a via.
        """
        layers = layers or self.routable
        Ls = [self.layers.index(L) for L in layers]
        nx, ny = self.nx, self.ny
        passable = [((self.owner[L] == 0) | (self.owner[L] == net)).ravel().tobytes()
                    for L in self.layers]
        vok = self.via_ok(net).ravel().tobytes()
        lcost = [self.layer_cost[L] for L in self.layers]

        if goal_cells:
            # octile distance to the (subsampled) goal, as a lookup table
            pts = sorted({f for _, f in goal_cells})
            pts = pts[::max(1, len(pts) // 48)]
            I = np.arange(ny)[:, None]
            J = np.arange(nx)[None, :]
            H = np.full((ny, nx), np.inf)
            for f in pts:
                di, dj = np.abs(I - f // nx), np.abs(J - f % nx)
                H = np.minimum(H, np.maximum(di, dj) + 0.41421356 * np.minimum(di, dj))
            h = H.ravel().tolist().__getitem__
        else:
            h = lambda f: 0.0

        openh, came, gbest = [], {}, {}
        for L, (i, j) in starts:
            li = self.layers.index(L)
            s = (li, i * nx + j, -1)
            gbest[s] = 0.0
            came[s] = None
            heapq.heappush(openh, (h(s[1]), 0.0, s))

        turn = [[self.turn_cost * min((a - b) % 8, (b - a) % 8) ** 2 for b in range(8)]
                for a in range(8)]
        expanded = 0
        while openh:
            f, g, s = heapq.heappop(openh)
            if g > gbest.get(s, 1e18):
                continue
            li, fi, d = s
            if goal_cells and (li, fi) in goal_cells:
                return self._unwind(came, s)
            if goal_via and vok[fi] and came[s] is not None:
                return self._unwind(came, s) + [("VIA",)]
            expanded += 1
            if expanded > max_expand:
                break
            i, j = divmod(fi, nx)
            pas = passable[li]
            for nd, (dj, di) in enumerate(DIRS):
                ii, jj = i + di, j + dj
                if not (0 <= ii < ny and 0 <= jj < nx):
                    continue
                nf = ii * nx + jj
                if not pas[nf]:
                    continue
                if di and dj and not (pas[i * nx + jj] or pas[ii * nx + j]):
                    continue
                step = (1.41421356 if di and dj else 1.0) * lcost[li]
                if d >= 0:
                    step += turn[d][nd]
                ns = (li, nf, nd)
                ng = g + step
                if ng < gbest.get(ns, 1e18):
                    gbest[ns] = ng
                    came[ns] = s
                    heapq.heappush(openh, (ng + h(nf), ng, ns))
            if vok[fi]:
                for lj in Ls:
                    if lj != li and passable[lj][fi]:
                        ns = (lj, fi, -1)
                        ng = g + self.via_cost
                        if ng < gbest.get(ns, 1e18):
                            gbest[ns] = ng
                            came[ns] = s
                            heapq.heappush(openh, (ng + h(fi), ng, ns))
        raise RouteError(f"no route for net {net} (expanded {expanded})")

    def _unwind(self, came, s):
        out = []
        while s is not None:
            li, fi, _ = s
            out.append((self.layers[li], fi // self.nx, fi % self.nx))
            s = came[s]
        return out[::-1]

    def goal_from_cells(self, cells):
        return {(self.layers.index(L), i * self.nx + j) for L, i, j in cells}


def simplify(path):
    """Split a cell path into per-layer polylines (collinear points merged)
    and via positions. Returns (runs, vias): runs = [(layer, [(i, j), ...])]."""
    runs, vias = [], []
    cur_layer, pts = None, []
    for c in path:
        if c[0] == "VIA":
            vias.append(pts[-1])
            continue
        L, i, j = c
        if L != cur_layer:
            if pts and cur_layer is not None:
                runs.append((cur_layer, pts))
                vias.append(pts[-1])
            cur_layer, pts = L, ([pts[-1]] if pts else [])
            if pts and pts[-1] == (i, j):
                continue
        pts.append((i, j))
    if pts:
        runs.append((cur_layer, pts))
    out = []
    for L, ps in runs:
        keep = [ps[0]]
        for a, b in zip(ps[1:], ps[2:]):
            p = keep[-1]
            if (a[0] - p[0]) * (b[1] - a[1]) != (a[1] - p[1]) * (b[0] - a[0]):
                keep.append(a)
        if len(ps) > 1:
            keep.append(ps[-1])
        out.append((L, keep))
    return out, vias
