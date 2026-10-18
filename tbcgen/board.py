"""Build a .kicad_pcb from a board config using KiCad's pcbnew Python API.

Two modes:
  * template (cfg["template"] set): start from a hand-drawn chassis in
    lib/templates/ -- outline, edge connectors, back side, its routing --
    and only add LEDs, front routing and power planes. The back is never
    touched (vias still pass through it, avoiding its copper).
  * generated: build the chassis too (connectors, caps, jumper hubs) and
    auto-route the back. Used for shapes that have no template yet.
"""
import math
import shutil
import time

import pcbnew
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from . import geometry as geo
from .config import LIB
from .router import Grid, RouteError, simplify

CENTRE = (100.0, 100.0)        # board centre in KiCad page coordinates, mm
LAYER_IDS = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu,
             "In2.Cu": pcbnew.In2_Cu, "B.Cu": pcbnew.B_Cu}


def mm(v):
    return pcbnew.FromMM(v)


def vec(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def to_mm(p):
    return (pcbnew.ToMM(p.x), pcbnew.ToMM(p.y))


def pad_poly(pad, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    pad.TransformShapeToPolygon(ps, layer, 0, mm(0.005), pcbnew.ERROR_INSIDE)
    polys = []
    for k in range(ps.OutlineCount()):
        o = ps.Outline(k)
        polys.append(Polygon([to_mm(o.CPoint(n)) for n in range(o.PointCount())]))
    return unary_union(polys)


class BoardBuilder:
    def __init__(self, cfg, pcb_path, log=print):
        self.cfg, self.path, self.log = cfg, pcb_path, log
        self.rules = cfg["rules"]
        self.template = cfg.get("template")
        if self.template:
            shutil.copyfile(LIB / "templates" / f"{self.template}.kicad_pcb", pcb_path)
            self.board = pcbnew.LoadBoard(str(pcb_path))
        else:
            self.board = pcbnew.NewBoard(str(pcb_path))
        self.board.SetCopperLayerCount(4)
        tb = self.board.GetTitleBlock()
        tb.SetTitle(cfg["name"])
        tb.SetRevision(str(cfg["rev"]))
        self.nets = {str(k): v for k, v in self.board.GetNetsByName().items() if str(k)}
        self.fps = {fp.GetReference(): fp for fp in self.board.GetFootprints()}
        self.pixelmap = {"name": cfg["name"], "rev": cfg["rev"], "leds": [], "ports": []}
        self.cx, self.cy = CENTRE
        self.ports = geo.ports(cfg["shape"], cfg["edge"])

    # -- primitives --------------------------------------------------------
    def net(self, name):
        if name not in self.nets:
            n = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(n)
            self.nets[name] = n
        return self.nets[name]

    def footprint(self, name, ref, value, x, y, back=False, lcsc=None):
        fp = pcbnew.FootprintLoad(str(LIB / "tbc.pretty"), name)
        if fp is None:
            raise FileNotFoundError(f"footprint tbc:{name}")
        fp.SetFPIDAsString(f"tbc:{name}")
        fp.SetReference(ref)
        fp.SetValue(value)
        fp.Reference().SetVisible(False)
        self.set_lcsc(fp, lcsc)
        self.board.Add(fp)
        fp.SetPosition(vec(self.cx + x, self.cy + y))
        if back:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        self.fps[ref] = fp
        return fp

    @staticmethod
    def set_lcsc(fp, lcsc):
        if lcsc:
            fp.SetField("LCSC", lcsc)
            fp.GetField("LCSC").SetVisible(False)

    def pad(self, fp, number):
        for p in fp.Pads():
            if p.GetNumber() == number:
                return p
        raise KeyError(f"{fp.GetReference()} has no pad {number}")

    def orient(self, fp, a_num, b_num, angle, candidates=None):
        """Rotate fp so the vector pad b -> pad a points along `angle`."""
        want = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
        best = None
        for o in candidates or [k * 15.0 for k in range(24)]:
            fp.SetOrientationDegrees(o)
            ax, ay = to_mm(self.pad(fp, a_num).GetPosition())
            bx, by = to_mm(self.pad(fp, b_num).GetPosition())
            d = math.hypot(ax - bx, ay - by) or 1
            score = ((ax - bx) * want[0] + (ay - by) * want[1]) / d
            if best is None or score > best[0] + 1e-9:
                best = (score, o)
        fp.SetOrientationDegrees(best[1])

    def text(self, s, x, y, layer=pcbnew.B_SilkS, size=1.0, angle=0):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(s)
        t.SetPosition(vec(self.cx + x, self.cy + y))
        t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(size * 0.15))
        t.SetTextAngleDegrees(angle)
        if layer in (pcbnew.B_SilkS, pcbnew.B_Fab):
            t.SetMirrored(True)
        self.board.Add(t)

    # -- chassis -----------------------------------------------------------
    def outline(self):
        cfg = self.cfg
        vs = [(self.cx + x, self.cy + y) for x, y in geo.outline(cfg["shape"], cfg["edge"])]
        if not self.template:
            for a, b in zip(vs, vs[1:] + vs[:1]):
                s = pcbnew.PCB_SHAPE(self.board)
                s.SetShape(pcbnew.SHAPE_T_SEGMENT)
                s.SetStart(vec(*a))
                s.SetEnd(vec(*b))
                s.SetLayer(pcbnew.Edge_Cuts)
                s.SetWidth(mm(0.05))
                self.board.Add(s)
        self.outline_pts = vs
        self.outline_poly = Polygon(vs)

    def check_template(self):
        """The template must match the config's shape: same connectors."""
        bb = self.board.GetBoardEdgesBoundingBox()
        ox, oy = to_mm(bb.GetCenter())
        if math.dist((ox, oy), CENTRE) > 0.05:
            raise ValueError(f"template {self.template}: board centre {ox, oy} != {CENTRE}")
        for p in self.ports:
            fp = self.fps.get(f"J{p.index}")
            if fp is None:
                raise ValueError(f"template {self.template}: missing J{p.index}")
            d = math.dist(to_mm(fp.GetPosition()), (self.cx + p.x, self.cy + p.y))
            if d > 0.05:
                raise ValueError(f"template {self.template}: J{p.index} is {d:.3f}mm off "
                                 f"the {self.cfg['shape']} {self.cfg['edge']}mm port position")
        for n in ["WS_IN", "WS_OUT", "PASS"] + [f"P{p.index}" for p in self.ports]:
            if n not in self.nets:
                raise ValueError(f"template {self.template}: no net {n}")
        # template parts (caps included) keep their value and BOM flags as drawn
        for ref, fp in self.fps.items():
            if ref.startswith(("JP", "kibuzzard")):
                fp.SetExcludedFromBOM(True)
                fp.SetExcludedFromPosFiles(True)

    def place_chassis(self):
        cfg, n = self.cfg, self.cfg["nets"]
        role_net = {"VDD": self.net(n["VDD"]), "GND": self.net(n["GND"])}

        conn = cfg["_conn"]
        for p in self.ports:
            fp = self.footprint(conn["footprint"], f"J{p.index}", conn["value"], p.x, p.y)
            fp.SetOrientationDegrees(-(p.angle + 90))
            for pad in fp.Pads():           # a pad may be split (edge_conn_shallow)
                role = conn["pins"][pad.GetNumber()]
                pad.SetNet(role_net.get(role) or self.net(f"P{p.index}"))
            # port number beside the port pad, clear of the hub jumper facing it
            nx, ny = math.cos(math.radians(p.angle)), math.sin(math.radians(p.angle))
            self.text(str(p.index), p.x - nx * 2.6 - ny * 2.5, p.y - ny * 2.6 + nx * 2.5,
                      size=1.0)

        # Decoupling caps: VDD pad towards the connector centre
        cap, k = cfg["_cap"], 1
        for p in self.ports:
            if p.index not in cfg["caps"].get("ports", [p.index]):
                continue
            for (x, y), d in zip(geo.cap_positions(p, cfg["caps"]["along"], cfg["caps"]["inset"]),
                                 cfg["caps"]["along"]):
                fp = self.footprint(cap["footprint"], f"C{k}", cap["value"], x, y,
                                    back=True, lcsc=cap.get("lcsc"))
                self.orient(fp, cap["pins"]["VDD"], cap["pins"]["GND"],
                            p.angle + (90 if d < 0 else -90))
                for role, num in cap["pins"].items():
                    self.pad(fp, num).SetNet(role_net[role])
                k += 1

        # Jumper hubs on the back: one jumper per port, pointing at it
        jp, k = cfg["_jumper"], 1
        hubs = geo.hub_centres(cfg)
        hub_net = {"IN": "WS_IN", "OUT": "WS_OUT", "PASS": "PASS"}
        self.hub_pads = {r: [] for r in hub_net}
        self.port_pads = {p.index: [] for p in self.ports}
        for role in ("IN", "OUT", "PASS"):
            for p, x, y in geo.jumper_positions(hubs[role], self.ports,
                                                cfg["hubs"]["jumper_radius"]):
                fp = self.footprint(jp["footprint"], f"JP{k}", f"{role}{p.index}", x, y, back=True)
                fp.SetExcludedFromBOM(True)
                fp.SetExcludedFromPosFiles(True)
                self.orient(fp, jp["pins"]["PORT"], jp["pins"]["HUB"], p.angle)
                pp, hp = self.pad(fp, jp["pins"]["PORT"]), self.pad(fp, jp["pins"]["HUB"])
                pp.SetNet(self.net(f"P{p.index}"))
                hp.SetNet(self.net(hub_net[role]))
                self.port_pads[p.index].append(pp)
                self.hub_pads[role].append(hp)
                k += 1
            lx, ly = cfg["hubs"].get("label_offset", (0, 0))
            fp = self.footprint(jp["labels"][role], f"kibuzzard-{role}", role,
                                hubs[role][0] + lx, hubs[role][1] + ly, back=True)
            fp.Value().SetVisible(False)
            fp.SetExcludedFromBOM(True)
            fp.SetExcludedFromPosFiles(True)

    def place_leds(self):
        cfg, n = self.cfg, self.cfg["nets"]
        led, pins = cfg["_led"], cfg["_led"]["pins"]
        rot = cfg["leds"].get("rotation", "auto")
        self.leds = geo.chain(cfg["shape"], cfg["leds"])
        turn = [0.0] * len(self.leds)
        if rot == "edge":
            # outer-ring LEDs turned (15 deg steps) to keep their body off the edge
            turn = geo.edge_rotations(cfg["shape"], cfg["edge"], [(L.x, L.y) for L in self.leds],
                                      led["body"], cfg["leds"]["pitch"] / 2)
        for L, t in zip(self.leds, turn):
            ref = f"D{L.index}"
            fp = self.footprint(led["footprint"], ref, led["value"], L.x, L.y, lcsc=led.get("lcsc"))
            if rot == "flow":
                # rotate per row so DOUT faces downstream (shortest links)
                self.orient(fp, pins["DOUT"], pins["DIN"], 0 if L.flow > 0 else 180,
                            candidates=[0, 90, 180, 270])
            elif rot in ("auto", "edge"):
                # one orientation for every LED (simpler assembly): DOUT to the right
                self.orient(fp, pins["DOUT"], pins["DIN"], 0, candidates=[0, 90, 180, 270])
                # geometry angles are clockwise on screen, KiCad's counter-clockwise
                fp.SetOrientationDegrees(fp.GetOrientationDegrees() - t)
            else:
                fp.SetOrientationDegrees(float(rot))
            self.pad(fp, pins["VDD"]).SetNet(self.net(n["VDD"]))
            self.pad(fp, pins["GND"]).SetNet(self.net(n["GND"]))
            din = "WS_IN" if L.index == 1 else f"D{L.index - 1}_OUT"
            dout = "WS_OUT" if L.index == len(self.leds) else f"D{L.index}_OUT"
            self.pad(fp, pins["DIN"]).SetNet(self.net(din))
            self.pad(fp, pins["DOUT"]).SetNet(self.net(dout))
            self.pixelmap["leds"].append({"index": L.index, "ref": ref,
                                          "x": round(L.x, 4), "y": round(L.y, 4)})
        for p in self.ports:
            self.pixelmap["ports"].append({"index": p.index, "ref": f"J{p.index}",
                                           "x": round(p.x, 4), "y": round(p.y, 4),
                                           "angle": round(p.angle, 3)})

    # -- routing -----------------------------------------------------------
    def init_grid(self):
        costs = {}
        for L, role in self.cfg["stackup"].items():
            if role == "signal":
                costs[L] = 1.0
            elif isinstance(role, dict) and role.get("signal_cost"):
                costs[L] = float(role["signal_cost"])
            else:
                costs[L] = None                 # obstacle-only (plane layer)
        if self.template:
            costs["B.Cu"] = None                # the back is hand-drawn art
        self.grid = g = Grid(self.outline_poly, costs, self.rules, self.cfg["router"])
        for fp in self.board.GetFootprints():
            for pad in fp.Pads():
                net = pad.GetNetCode()
                for L in g.layers:
                    if pad.IsOnLayer(LAYER_IDS[L]):
                        poly = pad_poly(pad, LAYER_IDS[L])
                        g.paint([L], poly, net)
                        g.block_vias(poly, g.via_r + g.via_clr)
                if pad.HasHole():
                    x, y = to_mm(pad.GetPosition())
                    g.add_hole(x, y, pcbnew.ToMM(pad.GetDrillSize().x))
            if not self.template and fp.GetReference().startswith("kibuzzard"):
                # keep vias from punching through the hub labels
                bb = fp.GetBoundingBox(False)
                g.block_vias(box(*to_mm(bb.GetOrigin()), *to_mm(bb.GetEnd())), g.via_r)
        for t in self.board.GetTracks():          # pre-existing (template) copper
            if t.Type() == pcbnew.PCB_VIA_T:
                g.add_via(*to_mm(t.GetPosition()), t.GetNetCode(),
                          r=pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2,
                          drill=pcbnew.ToMM(t.GetDrillValue()))
            else:
                L = self.board.GetLayerName(t.GetLayer())
                g.add_track(L, [to_mm(t.GetStart()), to_mm(t.GetEnd())], t.GetNetCode(),
                            hw=pcbnew.ToMM(t.GetWidth()) / 2)

    def routable(self, *prefer):
        rest = [L for L in self.grid.routable if L not in prefer]
        return [L for L in prefer if L in self.grid.routable] + rest

    def pad_cells(self, pad, shrink=None):
        """Grid cells inside a pad (any copper layer it is on)."""
        g = self.grid
        shrink = g.hw if shrink is None else shrink
        out = set()
        for L in g.layers:
            if not pad.IsOnLayer(LAYER_IDS[L]):
                continue
            poly = pad_poly(pad, LAYER_IDS[L]).buffer(-shrink)
            if not poly.is_empty:
                sl, m = g._window(poly)
                ii, jj = m.nonzero()
                out |= {(L, i + sl[0].start, j + sl[1].start) for i, j in zip(ii, jj)}
            out.add((L, *g.cell(*to_mm(pad.GetPosition()))))
        return out

    def net_cells(self, code):
        """Grid cells on the centreline of a net's existing tracks and vias."""
        return self.cells_of([t for t in self.board.GetTracks() if t.GetNetCode() == code])

    def cells_of(self, tracks):
        g = self.grid
        out = set()
        for t in tracks:
            if t.Type() == pcbnew.PCB_VIA_T:
                c = g.cell(*to_mm(t.GetPosition()))
                out |= {(L, *c) for L in g.layers}
                continue
            line = LineString([to_mm(t.GetStart()), to_mm(t.GetEnd())])
            L = self.board.GetLayerName(t.GetLayer())
            steps = max(1, int(line.length / (g.res / 2)))
            for k in range(steps + 1):
                p = line.interpolate(k / steps, normalized=True)
                i, j = g.cell(p.x, p.y)
                if math.dist(g.xy(i, j), (p.x, p.y)) < g.res * 0.3:
                    out.add((L, i, j))
        return out

    def commit(self, path, net_code, start_xy=None):
        """Turn a router path into tracks and vias; returns its cells."""
        g = self.grid
        runs, vias = simplify(path)
        net = self.board.FindNet(net_code)
        w = mm(self.rules["track_width"])
        for n, (L, cells) in enumerate(runs):
            pts = [g.xy(i, j) for i, j in cells]
            if n == 0 and start_xy and math.dist(start_xy, pts[0]) > 1e-6:
                pts.insert(0, start_xy)
            for a, b in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(self.board)
                t.SetStart(vec(*a))
                t.SetEnd(vec(*b))
                t.SetWidth(w)
                t.SetLayer(LAYER_IDS[L])
                t.SetNet(net)
                self.board.Add(t)
            if len(pts) > 1:
                g.add_track(L, pts, net_code)
        for i, j in vias:
            x, y = g.xy(i, j)
            v = pcbnew.PCB_VIA(self.board)
            v.SetPosition(vec(x, y))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetWidth(mm(self.rules["via_diameter"]))
            v.SetDrill(mm(self.rules["via_drill"]))
            v.SetNet(net)
            self.board.Add(v)
            g.add_via(x, y, net_code)
        cells = {c for c in path if c[0] != "VIA"}
        for i, j in vias:
            cells |= {(L, i, j) for L in g.layers}
        return cells

    def _route(self, net, starts, goal, layers, label, goal_via=False):
        try:
            return self.grid.route(net, starts, goal_cells=goal, goal_via=goal_via, layers=layers)
        except RouteError as e:
            raise RouteError(f"{label}: {e}") from None

    def connect_pad(self, pad, tree, layers, label):
        g = self.grid
        x, y = to_mm(pad.GetPosition())
        c = g.cell(x, y)
        starts = [(L, c) for L in layers if pad.IsOnLayer(LAYER_IDS[L])]
        if not starts:
            raise RouteError(f"{label}: pad not on any of {layers}")
        path = self._route(pad.GetNetCode(), starts, g.goal_from_cells(tree), layers, label)
        return self.commit(path, pad.GetNetCode(), start_xy=(x, y)) | self.pad_cells(pad)

    def connect(self, pads, layers, label):
        """Route a tree joining all `pads` (first pad is the root)."""
        g = self.grid
        tree = self.pad_cells(pads[0])
        todo = list(pads[1:])
        while todo:
            sample = list(tree)[::7] or list(tree)
            todo.sort(key=lambda p: min(math.dist(to_mm(p.GetPosition()), g.xy(i, j))
                                        for _, i, j in sample))
            pad = todo.pop(0)
            tree |= self.connect_pad(pad, tree, layers, label)

    def escape_to_plane(self, pad, label):
        """Short stub from an SMD pad to a through via (into the planes)."""
        L = "F.Cu" if pad.IsOnLayer(pcbnew.F_Cu) else "B.Cu"
        x, y = to_mm(pad.GetPosition())
        path = self._route(pad.GetNetCode(), [(L, self.grid.cell(x, y))], None, [L],
                           label, goal_via=True)
        self.commit(path, pad.GetNetCode(), start_xy=(x, y))

    def route(self):
        t0 = time.time()
        self.init_grid()
        pins = self.cfg["_led"]["pins"]
        n = len(self.leds)
        D = lambda k, role: self.pad(self.fps[f"D{k}"], pins[role])

        if not self.template:
            # caps -> nearest same-net connector pin, on the back
            for ref, fp in self.fps.items():
                if not ref.startswith("C"):
                    continue
                for pad in fp.Pads():
                    p = min(self.ports, key=lambda p: math.dist(
                        to_mm(pad.GetPosition()), (self.cx + p.x, self.cy + p.y)))
                    tgt = min((cp for cp in self.fps[f"J{p.index}"].Pads()
                               if cp.GetNetCode() == pad.GetNetCode()),
                              key=lambda cp: math.dist(to_mm(cp.GetPosition()),
                                                       to_mm(pad.GetPosition())))
                    self.connect([tgt, pad], ["B.Cu"], f"{ref}.{pad.GetNumber()}")

        # LED power first: every pad gets its via while there is still room
        from . import vias
        if not (self.cfg["router"].get("power_vias") == "pattern" and vias.plan(self)):
            for k in range(1, n + 1):
                for role in ("VDD", "GND"):
                    self.escape_to_plane(D(k, role), f"D{k}.{role}")

        # data chain, shortest links first (row returns go around them):
        # front only if possible, then any routable layer
        links = sorted(range(1, n), key=lambda k: math.dist(
            to_mm(D(k, "DOUT").GetPosition()), to_mm(D(k + 1, "DIN").GetPosition())))
        for k in links:
            try:
                self.connect([D(k + 1, "DIN"), D(k, "DOUT")], ["F.Cu"], f"D{k}->D{k + 1}")
            except RouteError:
                self.connect([D(k + 1, "DIN"), D(k, "DOUT")], self.routable("F.Cu"),
                             f"D{k}->D{k + 1}")

        if self.template:
            # chain ends -> the template's hand-off vias
            for pad, label in ((D(1, "DIN"), "WS_IN"), (D(n, "DOUT"), "WS_OUT")):
                self.connect_pad(pad, self.net_cells(pad.GetNetCode()),
                                 self.routable("F.Cu"), label)
        else:
            back = self.routable("B.Cu")
            for role, extra in (("IN", D(1, "DIN")), ("OUT", D(n, "DOUT")), ("PASS", None)):
                self.connect(self.hub_pads[role] + ([extra] if extra else []), back, f"hub {role}")
            for p in self.ports:
                conn = self.pad(self.fps[f"J{p.index}"], "3")
                self.connect([conn] + self.port_pads[p.index], back, f"P{p.index}")
        self.log(f"  routed in {time.time() - t0:.1f}s")

    def finish(self):
        """After an external router: complete whatever it left open on the
        data chain (links and chain ends) with the in-house router, which
        may hop on In2."""
        self.board.BuildConnectivity()
        conn = self.board.GetConnectivity()
        pins, n = self.cfg["_led"]["pins"], len(self.leds)
        D = lambda k, role: self.pad(self.fps[f"D{k}"], pins[role])
        uuid = lambda i: i.m_Uuid.AsString()
        todo = []
        # (pad, copper to reach): ends -> template copper, links -> upstream pad's cluster
        for pad, label in ((D(1, "DIN"), "WS_IN"), (D(n, "DOUT"), "WS_OUT")):
            reached = {uuid(i) for i in conn.GetConnectedItems(pad)}
            rest = [t for t in self.board.GetTracks()
                    if t.GetNetCode() == pad.GetNetCode() and uuid(t) not in reached]
            if rest:
                todo.append((pad, rest, [], label))
        for k in range(1, n):
            a, b = D(k, "DOUT"), D(k + 1, "DIN")
            cluster = list(conn.GetConnectedItems(a))
            if uuid(b) not in {uuid(i) for i in cluster}:
                tracks = [i for i in cluster if i.GetClass() in ("PCB_TRACK", "PCB_VIA")]
                todo.append((b, tracks, [a], f"D{k}->D{k + 1}"))
        if not todo:
            return
        self.init_grid()
        for pad, tracks, pads, label in todo:
            goal = self.cells_of(tracks)
            for p in pads:
                goal |= self.pad_cells(p)
            self.connect_pad(pad, goal, self.routable("F.Cu"), f"finish {label}")
        self.log(f"  finished {len(todo)} connection(s) with the in-house router: "
                 + ", ".join(t[3] for t in todo))

    # -- zones & save ----------------------------------------------------------
    def zones(self):
        self.add_zones()
        pcbnew.ZONE_FILLER(self.board).Fill(self.board.Zones())

    def add_zones(self):
        if list(self.board.Zones()):
            return
        for L, role in self.cfg["stackup"].items():
            if not isinstance(role, dict) or "plane" not in role:
                continue
            netname = self.cfg["nets"][role["plane"]]
            z = pcbnew.ZONE(self.board)
            z.SetLayer(LAYER_IDS[L])
            z.SetNet(self.net(netname))
            z.SetZoneName(f"{netname}_{L}")
            o = z.Outline()
            o.NewOutline()
            for x, y in self.outline_pts:
                o.Append(mm(x), mm(y))
            z.SetMinThickness(mm(0.2))
            z.SetLocalClearance(mm(self.rules["zone_clearance"]))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
            z.SetThermalReliefGap(mm(0.3))
            z.SetThermalReliefSpokeWidth(mm(0.4))
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
            self.board.Add(z)

    def build(self):
        self.outline()
        if self.template:
            self.check_template()
        else:
            self.place_chassis()
        self.place_leds()
        try:
            if self.cfg["router"].get("engine", "internal") == "freerouting":
                from . import freerouting
                self.add_zones()            # exported as planes
                t0 = time.time()
                freerouting.route(self)
                self.finish()
                self.log(f"  routed in {time.time() - t0:.1f}s")
            else:
                self.route()
        except RouteError:
            # keep what got routed so the failure can be inspected in KiCad
            failed = self.path.with_name(self.path.stem + "-failed.kicad_pcb")
            pcbnew.SaveBoard(str(failed), self.board, True)
            self.log(f"  partial board saved to {failed}")
            raise
        self.zones()
        pcbnew.SaveBoard(str(self.path), self.board)
        return self.pixelmap


def build_board(cfg, pcb_path, log=print):
    return BoardBuilder(cfg, pcb_path, log).build()
