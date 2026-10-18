"""Markdown docs from what's in build/: a page per board and per shape.

    docs/README.md                       index with thumbnails
    docs/boards/<board>/README.md        config, name, results, renders, pixel map
    docs/shapes/<shape>/README.md        render, solid, boards used

Images are copied next to each page (layer SVGs get a background and a pixel
size so they read on GitHub in light and dark mode), so docs/ stands alone.
Regenerate after `make all model shapes`; pages are overwritten.
"""
import json
import re
import shutil
import subprocess

from . import config, geometry
from .config import BUILD, ROOT

DOCS = ROOT / "docs"
SHAPE_WORD = {"square": "square", "tri": "triangle", "hex": "hexagon"}
TAG_TEXT = {
    "tpl": "hand-drawn back side from a template",
    "shallow": "shallow edge-connector pads",
    "micro": "micro edge connector (small tiles)",
    "rot": "outer LEDs turned to clear the edge",
    "flow": "LEDs flipped per row to follow the chain",
    "grp": "jumpers grouped by port",
    "nopass": "no PASS hub",
    "pvia": "patterned power vias",
    "fr": "routed with Freerouting",
}
LAYERS = [("front", "Front: F.Cu, silkscreen"), ("back", "Back, seen from below: B.Cu, silkscreen"),
          ("in1", "In1: GND plane"), ("in2", "In2: +5V plane (and a few hops)")]


# -- helpers ---------------------------------------------------------------------

def _png(src, dst, width=None):
    """Copy a PNG, shrunk to `width` px with sips when available."""
    if width and shutil.which("sips"):
        subprocess.run(["sips", "--resampleWidth", str(width), str(src), "--out", str(dst)],
                       capture_output=True, check=True)
    else:
        shutil.copyfile(src, dst)


def _svg(src, dst, px=480, bg="#001023"):
    """Layer SVG with KiCad's dark background and a pixel size."""
    s = src.read_text()
    m = re.search(r'viewBox="([\d.\- ]+)"', s)
    x, y, w, h = m.group(1).split()
    s = re.sub(r'width="[\d.]+mm" height="[\d.]+mm"',
               f'width="{px}" height="{round(px * float(h) / float(w))}"', s, count=1)
    s = re.sub(r"(<svg[^>]*>)", rf'\1\n<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{bg}"/>',
               s, count=1)
    dst.write_text(s)


def _table(rows):
    return "\n".join(["| | |", "|---|---|"] + [f"| {k} | {v} |" for k, v in rows])


def _mm(v):
    return f"{v:g} mm"


def name_parts(name):
    """Readable breakdown of a board name."""
    base, _, note = name.partition("--")
    shape_edge, pkg_count, pitch, *tags = base.split("-")
    shape = re.match(r"[a-z]+", shape_edge).group()
    out = [(f"`{shape_edge}`", f"{SHAPE_WORD.get({'sq': 'square'}.get(shape, shape), shape)}, "
                               f"{shape_edge[len(shape):]} mm edge"),
           (f"`{pkg_count}`", "{} LEDs in the {} package".format(*reversed(pkg_count.split("x")))),
           (f"`{pitch}`", f"{pitch[1:]} mm LED pitch")]
    for t in tags:
        out.append((f"`{t}`", TAG_TEXT.get(t, f"rotated {t[1:]} deg" if t.startswith("r") else t)))
    if note:
        out.append((f"`--{note}`", "note"))
    return out


def board_stats(pcb):
    import pcbnew
    b = pcbnew.LoadBoard(str(pcb))
    length, vias = {}, 0
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            vias += 1
        else:
            L = b.GetLayerName(t.GetLayer())
            length[L] = length.get(L, 0) + pcbnew.ToMM(t.GetLength())
    return {"length": length, "vias": vias}


def shapes_using():
    out = {}
    for s in config.all_shapes():
        for board in config.load_shape(s)["boards"].values():
            out.setdefault(board, []).append(s)
    return out


# -- pages -----------------------------------------------------------------------

def board_page(name, used_in):
    cfg = config.load_board(name)
    src = BUILD / name
    pcb = src / f"{name}.kicad_pcb"
    if not pcb.exists():
        return None
    d = DOCS / "boards" / name
    d.mkdir(parents=True, exist_ok=True)
    led, leds = cfg["_led"], cfg["leds"]
    n = len(geometry.chain(cfg["shape"], leds))
    drc = json.loads((src / "drc.json").read_text()) if (src / "drc.json").exists() else None
    stats = board_stats(pcb)

    images = {}
    for f, w in (("top.png", 480), ("bottom.png", 480)):
        if (src / "renders" / f).exists():
            _png(src / "renders" / f, d / f, w)
            images[f] = True
    for f, _ in LAYERS:
        if (src / "renders" / f"{f}.svg").exists():
            _svg(src / "renders" / f"{f}.svg", d / f"{f}.svg")
            images[f] = True
    if (src / "3d" / f"{name}.png").exists():
        _png(src / "3d" / f"{name}.png", d / "model.png", 640)
        images["model"] = True
    if (src / "pixelmap.json").exists():
        shutil.copyfile(src / "pixelmap.json", d / "pixelmap.json")

    layout = {"square": f"{leds.get('cols')} x {leds.get('rows')}",
              "tri": " + ".join(str(k) for k in range(leds.get("rows", 0), 0, -1)),
              "hex": f"{leds.get('rings')} rings"}[cfg["shape"]]
    rot = leds.get("rotation", "auto")
    ncaps = len(cfg["caps"]["along"])
    caps = "1 cap" if ncaps == 1 else f"{ncaps} caps"
    caps += (" on " + ", ".join(f"P{k}" for k in cfg["caps"]["ports"]) if "ports" in cfg["caps"]
             else " per edge")
    if not ncaps or cfg["caps"].get("ports") == []:
        caps = "no caps"
    hubs = cfg["hubs"]
    roles = "/".join(hubs.get("roles", ["IN", "OUT", "PASS"]))
    if cfg.get("template"):
        back = f"hand-drawn template `{cfg['template']}`"
    elif hubs.get("layout") == "grouped":
        back = (f"generated: {roles} jumpers grouped by port ({hubs['spacing']} mm apart, "
                f"{hubs['inset']} mm in from the edge), hubs routed as rings, {caps}")
    else:
        back = ("generated: {} jumper hubs with {} wings each ({} mm from the hub centre, hubs on a "
                "{} mm circle), {}".format(roles, len(geometry.ports(cfg["shape"], cfg["edge"])),
                                           hubs["jumper_radius"], hubs["radius"], caps))
    rows = [
        ("Shape", f"{SHAPE_WORD[cfg['shape']]}, {_mm(cfg['edge'])} edge, "
                  f"{len(geometry.ports(cfg['shape'], cfg['edge']))} ports"),
        ("LEDs", f"{n} x {led['value']} ({layout})"),
        ("Footprint", f"`tbc:{led['footprint']}`"),
        ("LCSC", led.get("lcsc") or "**TODO**"),
        ("Pitch", _mm(leds["pitch"])),
        ("Rotation", {"auto": "one rotation, DOUT to the right",
                      "edge": "outer LEDs turned (15 deg steps) to clear the edge",
                      "flow": "flipped per row"}.get(rot, f"{rot} deg")),
        ("Chain", leds.get("chain", "raster")),
        ("Edge connector", "from the template" if cfg.get("template") else
                           f"`{cfg['connector']}` (`tbc:{cfg['_conn']['footprint']}`)"),
        ("Back side", back),
        ("Power vias", cfg["router"].get("power_vias", "nearest")),
        ("Router", cfg["router"].get("engine", "internal")),
        ("Revision", cfg["rev"]),
    ]
    L = stats["length"]
    results = [
        ("DRC", "not run" if drc is None else "{} errors, {} warnings, {} unconnected".format(
            sum(v["severity"] == "error" for v in drc["violations"]),
            sum(v["severity"] == "warning" for v in drc["violations"]),
            len(drc["unconnected_items"]))),
        ("Front track", _mm(round(L.get("F.Cu", 0)))),
        ("Back track", _mm(round(L.get("B.Cu", 0)))),
        ("In2 hops", _mm(round(L.get("In2.Cu", 0), 1))),
        ("Vias", stats["vias"]),
    ]

    md = [f"# {name}", ""]
    desc = config.header_comment((config.BOARDS / f"{name}.yaml").read_text())
    if desc:
        md += [desc, ""]
    if "model" in images:
        md += ['<img src="model.png" width="480" alt="3D render">', ""]
    md += ["## At a glance", "", _table(rows), "", "## Name", "", _table(name_parts(name)), "",
           "## Build", "", _table(results), "",
           "## Renders", "", "| Top | Bottom |", "|---|---|",
           "| {} | {} |".format(*(f'<img src="{f}" width="320">' if f in images else "-"
                                  for f in ("top.png", "bottom.png"))), "",
           "### Layers", ""]
    for pair in (LAYERS[:2], LAYERS[2:]):
        md += ["| " + " | ".join(t for _, t in pair) + " |", "|---|---|",
               "| " + " | ".join(f'<img src="{f}.svg" width="320">' if f in images else "-"
                                 for f, _ in pair) + " |", ""]
    md += [""]
    if (d / "pixelmap.json").exists():
        pm = json.loads((d / "pixelmap.json").read_text())
        md += ["## Pixel map", "",
               "LED index in the data chain -> position, mm from the board centre "
               "(y down, top view). Also in [pixelmap.json](pixelmap.json).", "",
               "<details><summary>{} LEDs, {} ports</summary>".format(len(pm["leds"]), len(pm["ports"])),
               "", "| LED | x | y |", "|---|---|---|"]
        md += [f"| {L['index']} | {L['x']:.2f} | {L['y']:.2f} |" for L in pm["leds"]]
        md += ["", "| Port | x | y | facing |", "|---|---|---|---|"]
        md += [f"| P{p['index']} | {p['x']:.2f} | {p['y']:.2f} | {p['angle']:.0f} deg |"
               for p in pm["ports"]]
        md += ["", "</details>", ""]
    if used_in:
        md += ["## Used in", ""] + [f"- [{s}](../../shapes/{s}/README.md)" for s in used_in] + [""]
    md += ["## Files", "",
           f"- config: [boards/{name}.yaml](../../../boards/{name}.yaml)",
           f"- rebuild: `make all model BOARDS={name} && make docs`",
           f"- KiCad project, gerbers, BOM/CPL: `build/{name}/` (not committed)", ""]
    (d / "README.md").write_text("\n".join(md))
    return {"name": name, "cfg": cfg, "n": n, "drc": results[0][1], "model": "model" in images}


def shape_page(name):
    from . import models
    scfg = config.load_shape(name)
    glb = BUILD / "shapes" / f"{name}.glb"
    if not glb.exists():
        return None
    d = DOCS / "shapes" / name
    d.mkdir(parents=True, exist_ok=True)
    png = glb.with_suffix(".png")
    if png.exists():
        _png(png, d / "render.png", 640)

    _, faces = models.polyhedron(scfg["solid"])
    kinds = models.KINDS
    count = {}
    for loop, _ in faces:
        count[kinds[len(loop)]] = count.get(kinds[len(loop)], 0) + 1
    boards = {k: config.load_board(b) for k, b in scfg["boards"].items()}
    leds = {k: len(geometry.chain(c["shape"], c["leds"])) for k, c in boards.items()}
    total = sum(count[k] * leds[k] for k in count)
    import trimesh
    size = trimesh.load(glb, force="scene").extents * 1000

    rows = [("Solid", f"{scfg['solid']}, {len(faces)} faces"),
            ("Tiles", ", ".join(f"{count[k]} x {SHAPE_WORD[boards[k]['shape']]}" for k in count)),
            ("LEDs", f"{total} (" + " + ".join(f"{count[k]} x {leds[k]}" for k in count) + ")"),
            ("Size", " x ".join(f"{v:.0f}" for v in size) + " mm (with LEDs)")]
    md = [f"# {name}", ""]
    if scfg["description"]:
        md += [scfg["description"], ""]
    if (d / "render.png").exists():
        md += ['<img src="render.png" width="480" alt="render">', ""]
    md += [_table(rows), "", "## Boards", ""]
    for k, c in boards.items():
        b = c["name"]
        md.append(f"- **{count.get(k, 0)} x [{b}](../../boards/{b}/README.md)**: "
                  f"{leds[k]} x {c['_led']['value']} at {c['leds']['pitch']:g} mm")
    md += ["", "## Files", "",
           f"- config: [shapes/{name}.yaml](../../../shapes/{name}.yaml)",
           f"- rebuild: `make shapes SHAPES={name} && make docs`",
           f"- 3D model: `build/shapes/{name}.glb` (not committed; opens in Blender or any "
           "glTF viewer)", ""]
    (d / "README.md").write_text("\n".join(md))
    return {"name": name, "cfg": scfg, "total": total, "render": (d / "render.png").exists()}


def index(boards, shapes):
    md = ["# the-better-cube docs", "",
          "Generated by `make docs` from `build/` (run `make all model shapes` first); "
          "don't edit by hand.", "", "## Boards", "", "| | Board | LEDs | Pitch | DRC |",
          "|---|---|---|---|---|"]
    for b in boards:
        img = f'<img src="boards/{b["name"]}/model.png" width="120">' if b["model"] else ""
        md.append(f"| {img} | [{b['name']}](boards/{b['name']}/README.md) | {b['n']} | "
                  f"{b['cfg']['leds']['pitch']:g} mm | {b['drc']} |")
    md += ["", "## Shapes", "", "| | Shape | LEDs |", "|---|---|---|"]
    for s in shapes:
        img = f'<img src="shapes/{s["name"]}/render.png" width="120">' if s["render"] else ""
        md.append(f"| {img} | [{s['name']}](shapes/{s['name']}/README.md) | {s['total']} |")
    (DOCS / "README.md").write_text("\n".join(md) + "\n")


def build():
    DOCS.mkdir(exist_ok=True)
    used = shapes_using()
    boards, shapes, skipped = [], [], []
    for b in config.all_boards():
        page = board_page(b, used.get(b, []))
        (boards if page else skipped).append(page or b)
    for s in config.all_shapes():
        page = shape_page(s)
        (shapes if page else skipped).append(page or s)
    index(boards, shapes)
    return boards, shapes, skipped
