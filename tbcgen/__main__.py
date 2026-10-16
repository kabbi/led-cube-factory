"""CLI: python -m tbcgen <command> [boards...]

  build   generate build/<board>/<board>.kicad_pcb (+ project, pixel map)
  check   run DRC, fail on errors or unconnected items
  render  top/bottom PNG renders and per-layer SVGs
  fab     JLCPCB gerbers (KiKit), BOM and CPL
  panel   panels from panels/*.yaml, boards built first (names given are
          panels, not boards)
  all     build + check + render + fab
  release freeze build/<board> into releases/<board>-<rev>/ (refuses to overwrite)
  model   3D model (GLB) of each built board, for demos and docs
  shapes  polyhedra assembled from built boards, one per shapes/*.yaml
          (names given are shapes, not boards)
  docs    docs/: a page per board and per shape, from build/ (run after
          all, model and shapes)

With no boards given, every boards/*.yaml is processed.
"""
import argparse
import sys
import time

from . import config, outputs


def cmd_build(cfg, out, pcb):
    from .board import build_board
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob(f"{cfg['name']}.kicad_*"):
        f.unlink()
    outputs.write_project(cfg, out)
    pm = build_board(cfg, pcb, log=lambda m: print(m, flush=True))
    outputs.write_pixelmap(pm, out)


def cmd_check(cfg, out, pcb):
    res = outputs.drc(pcb, out)
    ok = res["errors"] == 0 and res["unconnected"] == 0
    print(f"  DRC: {res['errors']} errors, {res['warnings']} warnings, "
          f"{res['unconnected']} unconnected -> {'OK' if ok else 'FAIL'}")
    for k, n in res["by_type"].items():
        print(f"    {n:4d} {k}")
    return ok


def cmd_shapes(a):
    from . import models
    for name in a.boards or config.all_shapes():
        scfg = config.load_shape(name)
        print(f"[{scfg['name']}]", flush=True)
        glb, png = models.build_shape(scfg)
        print(f"  {glb}\n  preview: {png or 'skipped (no Blender)'}")
    return 0


def cmd_panel(a):
    from . import panel
    failed = []
    for name in a.boards or panel.all_panels():
        spec = panel.load_panel(name)
        print(f"[panel {name}]", flush=True)
        t0 = time.time()
        pp, size, ntabs, res = outputs.panel(spec)
        n = sum(len(row) for row in spec["boards"])
        print(f"  {pp}\n  {size[0]:.2f} x {size[1]:.2f} mm, {n} boards, {ntabs} tabs")
        print(f"  DRC: {res['errors']} errors, {res['warnings']} warnings, "
              f"{res['unconnected']} unconnected")
        for k, c in res["by_type"].items():
            print(f"    {c:4d} {k}")
        print(f"  done in {time.time() - t0:.1f}s")
        if res["errors"] or res["unconnected"]:
            failed.append(name)
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tbcgen", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["build", "check", "render", "fab", "panel", "all",
                                        "release", "model", "shapes", "docs"])
    ap.add_argument("boards", nargs="*")
    a = ap.parse_args(argv)

    if a.command == "panel":
        return cmd_panel(a)
    if a.command == "shapes":
        return cmd_shapes(a)
    if a.command == "docs":
        from . import docs
        boards, shapes, skipped = docs.build()
        print(f"  {docs.DOCS}: {len(boards)} boards, {len(shapes)} shapes")
        for s in skipped:
            print(f"  skipped {s} (not built)")
        return 0

    failed = []
    for name in a.boards or config.all_boards():
        cfg = config.load_board(name)
        out = config.BUILD / cfg["name"]
        pcb = out / f"{cfg['name']}.kicad_pcb"
        print(f"[{cfg['name']}]", flush=True)
        t0 = time.time()
        ok = True
        if a.command in ("build", "all"):
            cmd_build(cfg, out, pcb)
        if a.command in ("check", "all"):
            ok = cmd_check(cfg, out, pcb)
        if a.command in ("render", "all"):
            print(f"  renders: {outputs.render(pcb, out)}")
        if a.command in ("fab", "all"):
            print(f"  fab: {outputs.fab(cfg, pcb, out)}")
        if a.command == "model":
            from . import models
            glb = models.export_glb(cfg, pcb, out)
            print(f"  model: {glb}")
            print(f"  preview: {models.render_png(glb) or 'skipped (no Blender)'}")
        if a.command == "release":
            print(f"  release: {outputs.release(cfg, out)}")
        print(f"  done in {time.time() - t0:.1f}s")
        if not ok:
            failed.append(cfg["name"])
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
