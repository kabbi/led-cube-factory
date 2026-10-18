"""Board config loading: lib/defaults.yaml <- boards/<name>.yaml, plus parts."""
import copy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / "lib"
BOARDS = ROOT / "boards"
SHAPES = ROOT / "shapes"
BUILD = ROOT / "build"


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_parts():
    return yaml.safe_load((LIB / "parts.yaml").read_text())


SHAPE_TAG = {"square": "sq", "tri": "tri", "hex": "hex"}


def board_name(cfg):
    """The name a board config must have: what it is, then how it's built.

        <shape><edge>-<package>x<leds>-p<pitch>[-<variation>...]

    e.g. tri30-3535x10-p6.2-shallow-rot. Variations, in this order:
    tpl (hand-drawn back from a template), shallow / micro
    (shallow or micro edge connector),
    rot / flow / r<deg> (LED rotation other than one-way auto), grp (grouped
    jumpers), nopass (no PASS hub),
    pvia (patterned power vias), fr (Freerouting).
    """
    from . import geometry
    leds = cfg["leds"]
    n = len(geometry.chain(cfg["shape"], leds))
    tags = []
    if cfg.get("template"):
        tags.append("tpl")
    conn_tag = {"edge_connector_shallow": "shallow", "edge_connector_micro": "micro"}
    if cfg["connector"] in conn_tag:
        tags.append(conn_tag[cfg["connector"]])
    rot = leds.get("rotation", "auto")
    if rot != "auto":
        tags.append({"edge": "rot", "flow": "flow"}.get(rot) or f"r{float(rot):g}")
    if cfg["hubs"].get("layout") == "grouped":
        tags.append("grp")
    if "PASS" not in cfg["hubs"].get("roles", ["PASS"]):
        tags.append("nopass")
    if cfg["router"].get("power_vias") == "pattern":
        tags.append("pvia")
    if cfg["router"].get("engine", "internal") == "freerouting":
        tags.append("fr")
    return "-".join([f"{SHAPE_TAG[cfg['shape']]}{cfg['edge']:g}",
                     f"{leds['part'].split('-')[-1]}x{n}", f"p{leds['pitch']:g}"] + tags)


def load_board(path):
    path = Path(path)
    if not path.exists():
        path = BOARDS / f"{path}.yaml"
    defaults = yaml.safe_load((LIB / "defaults.yaml").read_text())
    cfg = _merge(defaults, yaml.safe_load(path.read_text()))
    cfg.setdefault("name", path.stem)
    if cfg["name"] != path.stem:
        raise ValueError(f"{path}: name '{cfg['name']}' must match the file name")
    # the file name spells out the board; anything after "--" is a free note
    want = board_name(cfg)
    if cfg["name"].split("--")[0] != want:
        raise ValueError(f"{path}: config describes '{want}', rename the file to "
                         f"{want}.yaml (or {want}--<note>.yaml)")
    parts = load_parts()
    cfg["_led"] = parts["leds"][cfg["leds"]["part"]]
    cfg["_cap"] = parts["capacitors"][cfg["caps"]["part"]]
    cfg["_jumper"] = parts[cfg["jumper"]]
    cfg["_conn"] = parts[cfg["connector"]]
    return cfg


def all_boards():
    return sorted(p.stem for p in BOARDS.glob("*.yaml"))


def shape_name(cfg):
    """<solid>--<square board>+<tri board>+<hex board> (only the boards the solid uses)."""
    return f"{cfg['solid']}--" + "+".join(cfg["boards"][k] for k in ("square", "tri", "hex")
                                          if k in cfg["boards"])


def load_shape(path):
    """A demo assembly: shapes/<name>.yaml = {solid, boards: {square, tri, hex}}.
    The header comment block is its description."""
    path = Path(path)
    if not path.exists():
        path = SHAPES / f"{path}.yaml"
    text = path.read_text()
    cfg = yaml.safe_load(text)
    cfg["name"] = path.stem
    want = shape_name(cfg)
    if path.stem != want:
        raise ValueError(f"{path}: describes '{want}', rename the file to {want}.yaml")
    cfg["description"] = header_comment(text)
    return cfg


def header_comment(text):
    """The leading '#' comment block of a YAML file, as plain text."""
    lines = []
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        lines.append(line[1:].strip())
    return " ".join(lines).strip()


def all_shapes():
    return sorted(p.stem for p in SHAPES.glob("*.yaml"))
