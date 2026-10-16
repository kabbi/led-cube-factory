"""Project scaffolding and everything downstream of the .kicad_pcb:
DRC, renders, JLCPCB fab files (KiKit + kicad-cli), panels, pixel map."""
import collections
import csv
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .config import LIB, ROOT

KICAD_CLI = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KIKIT = str(Path(sys.executable).with_name("kikit"))


def run(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"{' '.join(map(str, cmd))}\n{r.stdout}\n{r.stderr}")
    return r


# -- project files ------------------------------------------------------------

def write_project(cfg, out):
    """.kicad_pro (design rules), .kicad_dru (custom rules), fp-lib-table."""
    r, name = cfg["rules"], cfg["name"]
    nc = {"name": "Default", "clearance": r["clearance"], "track_width": r["track_width"],
          "via_diameter": r["via_diameter"], "via_drill": r["via_drill"],
          "microvia_diameter": 0.3, "microvia_drill": 0.1,
          "diff_pair_gap": 0.25, "diff_pair_width": 0.2, "diff_pair_via_gap": 0.25,
          "bus_width": 12, "wire_width": 6, "line_style": 0, "priority": 2147483647,
          "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}
    pro = {
        "meta": {"filename": f"{name}.kicad_pro", "version": 3},
        "board": {"design_settings": {
            "rules": {
                "min_clearance": r["clearance"],
                "min_track_width": r["track_width"],
                "min_via_diameter": r["via_diameter"],
                "min_through_hole_diameter": r["via_drill"],
                "min_hole_to_hole": r["hole_clearance"],
                "min_copper_edge_clearance": r["pad_edge_clearance"],
                "min_via_annular_width": 0.1,
                "min_hole_clearance": r["hole_copper_clearance"],
                "min_text_height": 0.8,
                "min_text_thickness": 0.08,
            },
            "rule_severities": {
                # silk clipped by pads/vias is cosmetic on these tiles
                "silk_over_copper": "ignore", "silk_overlap": "ignore",
                "silk_edge_clearance": "ignore",
                "lib_footprint_mismatch": "ignore", "lib_footprint_issues": "ignore",
            },
            "track_widths": [0.0, r["track_width"]],
            "via_dimensions": [{"diameter": 0.0, "drill": 0.0},
                               {"diameter": r["via_diameter"], "drill": r["via_drill"]}],
        }},
        "net_settings": {"classes": [nc], "meta": {"version": 4}},
        "text_variables": {"BOARD": name, "REV": cfg["rev"]},
    }
    (out / f"{name}.kicad_pro").write_text(json.dumps(pro, indent=2))
    ec = r["edge_clearance"]
    (out / f"{name}.kicad_dru").write_text(
        (LIB / "tbc.kicad_dru").read_text().replace("${EDGE_CLEARANCE}", f"{ec}mm"))
    rel = os.path.relpath(LIB / "tbc.pretty", out)
    (out / "fp-lib-table").write_text(
        f'(fp_lib_table\n  (version 7)\n  (lib (name "tbc")(type "KiCad")'
        f'(uri "${{KIPRJMOD}}/{rel}")(options "")(descr "the-better-cube shared library"))\n)\n')


# -- checks -------------------------------------------------------------------

def drc(pcb, out):
    report = out / "drc.json"
    run([KICAD_CLI, "pcb", "drc", "--format", "json", "--severity-all",
         "--refill-zones", "-o", report, pcb])
    d = json.loads(report.read_text())
    sev = collections.Counter()
    kinds = collections.Counter()
    for v in d.get("violations", []):
        sev[v["severity"]] += 1
        kinds[(v["severity"], v["type"])] += 1
    unconnected = len(d.get("unconnected_items", []))
    return {"errors": sev["error"], "warnings": sev["warning"], "unconnected": unconnected,
            "by_type": {f"{s}:{t}": n for (s, t), n in sorted(kinds.items())}}


def render(pcb, out):
    rd = out / "renders"
    rd.mkdir(exist_ok=True)
    for side in ("top", "bottom"):
        run([KICAD_CLI, "pcb", "render", "--side", side, "-w", "1200", "-h", "1200",
             "--quality", "basic", "-o", rd / f"{side}.png", pcb])
    for name, layers in {"front": "F.Cu,F.SilkS,Edge.Cuts", "back": "B.Cu,B.SilkS,Edge.Cuts",
                         "in2": "In2.Cu,Edge.Cuts", "in1": "In1.Cu,Edge.Cuts"}.items():
        mirror = ["--mirror"] if name == "back" else []     # as seen from below
        run([KICAD_CLI, "pcb", "export", "svg", "--layers", layers, "--mode-single", *mirror,
             "--fit-page-to-board", "--exclude-drawing-sheet", "-o", rd / f"{name}.svg", pcb])
    return rd


# -- fabrication ----------------------------------------------------------------

def fab(cfg, pcb, out):
    """Gerbers via KiKit; BOM/CPL from kicad-cli positions + LCSC fields."""
    import pcbnew  # noqa: imported late so non-KiCad commands still work
    fd = out / "fab"
    if fd.exists():
        shutil.rmtree(fd)
    fd.mkdir()
    run([KIKIT, "fab", "jlcpcb", "--no-drc", "--no-assembly", "--autoname", pcb, fd])

    board = pcbnew.LoadBoard(str(pcb))
    parts = {}
    for fp in board.GetFootprints():
        if fp.IsExcludedFromBOM():
            continue
        lcsc = fp.GetFieldText("LCSC") if fp.HasField("LCSC") else ""
        parts[fp.GetReference()] = (fp.GetValue(), fp.GetFPID().GetLibItemName().wx_str(), lcsc)

    groups = collections.defaultdict(list)
    for ref, key in parts.items():
        groups[key].append(ref)
    nat = lambda r: (r.rstrip("0123456789"), int(r[len(r.rstrip("0123456789")):] or 0))
    with open(fd / f"{cfg['name']}-bom.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC", "Quantity"])
        for (val, fpn, lcsc), refs in sorted(groups.items()):
            w.writerow([val, ",".join(sorted(refs, key=nat)), fpn, lcsc, len(refs)])

    pos = fd / "pos.csv"
    run([KICAD_CLI, "pcb", "export", "pos", "--format", "csv", "--units", "mm",
         "--side", "both", "--exclude-dnp", "-o", pos, pcb])
    rot_fix = {p["value"]: p.get("jlc_rotation", 0) for p in [cfg["_led"], cfg["_cap"]]}
    cx, cy = 100.0, 100.0
    with open(pos) as f, open(fd / f"{cfg['name']}-cpl.csv", "w", newline="") as g:
        w = csv.writer(g)
        w.writerow(["Designator", "Val", "Package", "Mid X", "Mid Y", "Rotation", "Layer"])
        for row in csv.DictReader(f):
            if row["Ref"] not in parts:
                continue
            rot = (float(row["Rot"]) + rot_fix.get(row["Val"], 0)) % 360
            # kicad-cli pos is already y-up; re-centre on the board middle
            w.writerow([row["Ref"], row["Val"], row["Package"],
                        f"{float(row['PosX']) - cx:.4f}", f"{float(row['PosY']) + cy:.4f}",
                        f"{rot:.1f}", row["Side"]])
    pos.unlink()
    return fd


def panel(cfg, pcb, out, preset):
    pd = out / "panel"
    pd.mkdir(exist_ok=True)
    pp = pd / f"{cfg['name']}-panel.kicad_pcb"
    run([KIKIT, "panelize", "-p", preset, pcb, pp])
    run([KICAD_CLI, "pcb", "render", "--side", "top", "-w", "1600", "-h", "1200",
         "--quality", "basic", "-o", pd / "panel.png", pp])
    run([KIKIT, "fab", "jlcpcb", "--no-drc", "--no-assembly", "--autoname", pp, pd / "fab"])
    return pp


def write_pixelmap(pixelmap, out):
    (out / "pixelmap.json").write_text(json.dumps(pixelmap, indent=1))


def release(cfg, out):
    """Copy a checked build into releases/ -- the frozen record of what was ordered."""
    drc_report = out / "drc.json"
    if not drc_report.exists():
        raise RuntimeError("run `check` (or `all`) before releasing")
    d = json.loads(drc_report.read_text())
    if any(v["severity"] == "error" for v in d["violations"]) or d["unconnected_items"]:
        raise RuntimeError("DRC is not clean, refusing to release")
    dst = ROOT / "releases" / f"{cfg['name']}-{cfg['rev']}"
    if dst.exists():
        raise RuntimeError(f"{dst} exists -- bump `rev` in boards/{cfg['name']}.yaml")
    dst.mkdir(parents=True)
    name = cfg["name"]
    for f in [f"{name}.kicad_pcb", f"{name}.kicad_pro", f"{name}.kicad_dru",
              "fp-lib-table", "pixelmap.json", "drc.json"]:
        shutil.copy2(out / f, dst / f)
    shutil.copytree(out / "fab", dst / "fab")
    shutil.copytree(out / "renders", dst / "renders", ignore=shutil.ignore_patterns("*.svg"))
    shutil.copy2(ROOT / "boards" / f"{name}.yaml", dst / "board.yaml")
    return dst
