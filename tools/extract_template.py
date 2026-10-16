"""Extract a hand-drawn "chassis" template from an existing tile board.

A template holds everything that is the same across a family of boards and
is drawn by hand: outline, edge connectors, the back side (caps, jumpers,
labels, B.Cu routing) and the inner-layer hops that routing uses. The
generator copies it unchanged and only adds LEDs + front routing.

    .venv/bin/python tools/extract_template.py SRC.kicad_pcb lib/templates/NAME.kicad_pcb

After extraction, edit the template directly in KiCad. Rules for templates:
  * board centre at (100, 100), connectors J1..Jn clockwise from the top
  * nets: P1..Pn, WS_IN, WS_OUT, PASS, +5V, GND
  * WS_IN / WS_OUT end in a via: the generator routes from there to the
    first / last LED on the front
"""
import sys

import pcbnew

KEEP_FP = ("J", "C", "JP", "kibuzzard")
RENAME = {"Net-(JP10-B)": "PASS"}
RELINK = {"integrated:edge_conn": "tbc:edge_conn",
          "Capacitor_SMD:C_0805_2012Metric": "tbc:C_0805_2012Metric",
          "Jumper:SolderJumper-2_P1.3mm_Open_TrianglePad1.0x1.5mm":
              "tbc:SolderJumper-2_P1.3mm_Open_TrianglePad1.0x1.5mm"}
ENDPOINT_NETS = ("WS_IN", "WS_OUT")   # cut where they leave the back


def same(a, b):
    return abs(a.x - b.x) < 2 and abs(a.y - b.y) < 2


def main(src, dst):
    b = pcbnew.LoadBoard(src)
    bb = b.GetBoardEdgesBoundingBox()
    c = bb.GetCenter()
    offset = pcbnew.VECTOR2I(pcbnew.FromMM(100) - c.x, pcbnew.FromMM(100) - c.y)

    for fp in list(b.GetFootprints()):
        if not fp.GetReference().startswith(KEEP_FP):
            b.Delete(fp)
            continue
        lib = fp.GetFPID().GetUniStringLibId()
        if lib in RELINK:
            fp.SetFPIDAsString(RELINK[lib])

    tracks = list(b.GetTracks())
    back = [t for t in tracks if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == pcbnew.B_Cu]
    for t in tracks:
        net = t.GetNetname()
        is_via = t.Type() == pcbnew.PCB_VIA_T
        if not is_via and t.GetLayer() == pcbnew.B_Cu:
            continue                                   # all back routing is kept
        if net.startswith("P") or net in RENAME:
            continue                                   # port / pass nets: keep hops
        if net in ENDPOINT_NETS and is_via and any(
                bt.GetNetname() == net and (same(bt.GetStart(), t.GetPosition()) or
                                            same(bt.GetEnd(), t.GetPosition())) for bt in back):
            continue                                   # hand-off via
        b.Delete(t)

    for d in list(b.GetDrawings()):
        if d.GetLayer() not in (pcbnew.Edge_Cuts, pcbnew.B_SilkS):
            b.Delete(d)
    for z in list(b.Zones()):
        b.Delete(z)

    for item in list(b.GetFootprints()) + list(b.GetTracks()) + list(b.GetDrawings()):
        item.Move(offset)

    for old, new in RENAME.items():
        n = b.FindNet(old)
        if n:
            n.SetNetname(new)

    pcbnew.SaveBoard(dst, b, True)
    print(f"wrote {dst}: {len(b.GetFootprints())} footprints, {len(b.GetTracks())} tracks/vias")


if __name__ == "__main__":
    main(*sys.argv[1:3])
