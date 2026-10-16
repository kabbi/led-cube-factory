"""Checks on generated boards in build/ (run `make build` first)."""
import json

import pytest

from tbcgen.config import BUILD, LIB, all_boards, load_board

pcbnew = pytest.importorskip("pcbnew")
BUILT = [b for b in all_boards() if (BUILD / b / f"{b}.kicad_pcb").exists()]


def load(name):
    return pcbnew.LoadBoard(str(BUILD / name / f"{name}.kicad_pcb"))


def mm(p):
    return (round(pcbnew.ToMM(p.x), 4), round(pcbnew.ToMM(p.y), 4))


def back_art(board):
    tracks = {(str(t.GetNetname()), board.GetLayerName(t.GetLayer()), mm(t.GetStart()), mm(t.GetEnd()))
              for t in board.GetTracks()
              if t.Type() != pcbnew.PCB_VIA_T and t.GetLayer() == pcbnew.B_Cu}
    fps = {fp.GetReference(): (mm(fp.GetPosition()), fp.GetOrientationDegrees(), fp.GetLayer())
           for fp in board.GetFootprints() if not fp.GetReference().startswith("D")}
    return tracks, fps


@pytest.mark.parametrize("name", BUILT)
def test_drc_clean(name):
    d = json.loads((BUILD / name / "drc.json").read_text())
    errors = [v for v in d["violations"] if v["severity"] == "error"]
    assert not errors and not d["unconnected_items"]


@pytest.mark.parametrize("name", BUILT)
def test_template_back_untouched(name):
    cfg = load_board(name)
    if not cfg.get("template"):
        pytest.skip("generated back side")
    tpl = pcbnew.LoadBoard(str(LIB / "templates" / f"{cfg['template']}.kicad_pcb"))
    assert back_art(load(name)) == back_art(tpl)


@pytest.mark.parametrize("name", BUILT)
def test_leds_chained_with_catalog_pinout(name):
    cfg = load_board(name)
    pins = cfg["_led"]["pins"]
    b = load(name)
    leds = sorted((fp for fp in b.GetFootprints() if fp.GetReference().startswith("D")),
                  key=lambda fp: int(fp.GetReference()[1:]))
    net = lambda fp, role: str(next(p for p in fp.Pads() if p.GetNumber() == pins[role]).GetNetname())
    assert net(leds[0], "DIN") == "WS_IN" and net(leds[-1], "DOUT") == "WS_OUT"
    for a, c in zip(leds, leds[1:]):
        assert net(a, "DOUT") == net(c, "DIN")
    for fp in leds:
        assert net(fp, "VDD") == "+5V" and net(fp, "GND") == "GND"
    rot = cfg["leds"].get("rotation", "auto")
    if rot == "edge":
        # one base rotation; outer LEDs turned from it in 15 deg steps, at most 45
        turns = [(fp.GetOrientationDegrees() - leds[0].GetOrientationDegrees()) for fp in leds]
        base = leds[0].GetOrientationDegrees() + max(set(turns), key=turns.count)
        for fp in leds:
            t = (fp.GetOrientationDegrees() - base + 180) % 360 - 180
            assert abs(t) <= 45 and t % 15 == 0, f"{fp.GetReference()} turned {t}"
    elif rot != "flow":
        assert len({fp.GetOrientationDegrees() for fp in leds}) == 1, "LEDs must share one rotation"


@pytest.mark.parametrize("name", BUILT)
def test_pixelmap(name):
    pm = json.loads((BUILD / name / "pixelmap.json").read_text())
    assert [L["index"] for L in pm["leds"]] == list(range(1, len(pm["leds"]) + 1))
