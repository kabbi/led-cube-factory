"""Alternative routing backend: Freerouting via Specctra DSN/SES.

Same contract as the in-house router: everything already on the board
(template copper, footprints) stays fixed, the back is off-limits in
template mode, power pads reach the In1/In2 planes through vias.
"""
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import pcbnew
from shapely.geometry import LineString

# router.freerouting_jar in the board config wins, then $FREEROUTING_JAR
DEFAULT_JAR = os.environ.get(
    "FREEROUTING_JAR", "/Applications/Freerouting.app/Contents/app/freerouting-executable.jar")


def route(builder):
    b, cfg = builder.board, builder.cfg
    rcfg = cfg["router"]
    work = builder.path.parent / "freerouting"
    work.mkdir(exist_ok=True)
    dsn, ses = work / "board.dsn", work / "board.ses"

    # planes are planes; pre-existing copper and all parts are fixed
    for L, role in cfg["stackup"].items():
        if isinstance(role, dict) and "plane" in role:
            b.SetLayerType(b.GetLayerID(L), pcbnew.LT_POWER)
    original = snapshot(b) if builder.template else []
    # Freerouting 2.x won't treat a layer with signal traces as a plane, so the
    # template's inner-layer hops leave the export (restore() puts them back)
    # and become via keep-outs instead
    keepouts = []
    plane_ids = {b.GetLayerID(L) for L, role in cfg["stackup"].items()
                 if isinstance(role, dict) and "plane" in role}
    r = cfg["rules"]
    for t in list(b.GetTracks()):
        if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() in plane_ids:
            line = LineString([(pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y)),
                               (pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))])
            area = line.buffer(pcbnew.ToMM(t.GetWidth()) / 2 + r["clearance"]
                               + r["via_diameter"] / 2, quad_segs=2)
            keepouts.append((str(b.GetLayerName(t.GetLayer())), area))
            b.Delete(t)
    unlock = [fp.GetReference() for fp in b.GetFootprints() if not fp.IsLocked()]
    for item in list(b.GetTracks()) + list(b.GetFootprints()):
        item.SetLocked(True)

    if not pcbnew.ExportSpecctraDSN(b, str(dsn)):
        raise RuntimeError("DSN export failed")
    text = dsn.read_text()
    if builder.template:
        # the back side is hand-drawn: every net may only route on the front
        # (vias still pass through to reach the planes)
        text = text.replace("(circuit\n", "(circuit\n        (use_layer F.Cu)\n")
    if keepouts:
        rules = "".join(
            f"    (via_keepout (polygon {L} 0 "
            + " ".join(f"{x * 1000:.0f} {-y * 1000:.0f}" for x, y in area.exterior.coords)
            + "))\n" for L, area in keepouts)
        text = text.replace("    (boundary", rules + "    (boundary", 1)
    dsn.write_text(text)

    java = shutil.which("java") or "java"
    # Freerouting 2.x: headless batch run, settings as --section.key=value
    cmd = [java, "-Djava.awt.headless=true", "-jar", rcfg.get("freerouting_jar", DEFAULT_JAR),
           "-de", str(dsn), "-do", str(ses)]
    settings = {"gui.enabled": "false",
                "router.autorouter.max_passes": rcfg.get("freerouting_passes", 100),
                # no thinner tracks at pads: 0.2mm is the board minimum
                "router.automatic_neckdown": "false"}
    settings.update(rcfg.get("freerouting_settings", {}))
    cmd += [f"--{k}={v}" for k, v in settings.items()]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=rcfg.get("freerouting_timeout", 1800))
    (work / "freerouting.log").write_text(r.stdout + r.stderr)
    if not ses.exists():
        raise RuntimeError(f"freerouting produced no session (exit {r.returncode}), see {work}/freerouting.log")
    builder.log(f"  freerouting: {time.time() - t0:.1f}s")

    if not pcbnew.ImportSpecctraSES(b, str(ses)):
        raise RuntimeError("SES import failed")
    restore(b, original)
    # the import recreates tracks, so unlock by walking the board again
    for t in b.GetTracks():
        t.SetLocked(False)
    for ref in unlock:
        b.FindFootprintByReference(ref).SetLocked(False)


def snapshot(b):
    """Exact copy of pre-existing copper: (is_via, net, layer, start, end, width, drill)."""
    out = []
    for t in b.GetTracks():
        via = t.Type() == pcbnew.PCB_VIA_T
        # copy coordinates: GetStart() is a reference into the soon-deleted track
        start = pcbnew.VECTOR2I(t.GetStart().x, t.GetStart().y)
        end = pcbnew.VECTOR2I(t.GetEnd().x, t.GetEnd().y)
        out.append((via, str(t.GetNetname()), t.GetLayer(), start, end,
                    t.GetWidth(pcbnew.F_Cu) if via else t.GetWidth(),
                    t.GetDrillValue() if via else 0))
    return out


def restore(b, original, tol=pcbnew.FromMM(0.01)):
    """The SES round trip re-creates fixed copper with ~0.5um rounding and adds
    sub-micron stubs at pads. Drop those copies and stubs, put the originals back."""
    if not original:
        return

    def near(p, q):
        return abs(p.x - q.x) <= tol and abs(p.y - q.y) <= tol

    def on_segment(p, a, b):
        dx, dy = b.x - a.x, b.y - a.y
        L2 = dx * dx + dy * dy
        k = 0 if L2 == 0 else max(0.0, min(1.0, ((p.x - a.x) * dx + (p.y - a.y) * dy) / L2))
        return math.hypot(p.x - (a.x + k * dx), p.y - (a.y + k * dy)) <= tol

    def is_copy(t):
        """Same net and layer, lying on an original (whole, or a split piece)."""
        via = t.Type() == pcbnew.PCB_VIA_T
        for o in original:
            if o[0] != via or o[1] != str(t.GetNetname()):
                continue
            if via and near(t.GetPosition(), o[3]):
                return True
            if not via and o[2] == t.GetLayer() and \
                    on_segment(t.GetStart(), o[3], o[4]) and on_segment(t.GetEnd(), o[3], o[4]):
                return True
        return False

    for t in list(b.GetTracks()):
        stub = t.Type() != pcbnew.PCB_VIA_T and near(t.GetStart(), t.GetEnd())
        if stub or is_copy(t):
            b.Delete(t)
    for via, net, layer, start, end, width, drill in original:
        if via:
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(start)
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetWidth(width)
            v.SetDrill(drill)
            v.SetNet(b.FindNet(net))
            b.Add(v)
        else:
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(start)
            t.SetEnd(end)
            t.SetLayer(layer)
            t.SetWidth(width)
            t.SetNet(b.FindNet(net))
            b.Add(t)
