"""Pure geometry: outlines, ports, LED grids, chain order, hub layout.

No KiCad imports here, so this is unit-testable with any Python. All
coordinates are mm relative to the board centre, KiCad orientation (y down).
Angles are degrees measured with atan2(dy, dx), i.e. clockwise on screen.
"""
import math
from dataclasses import dataclass

SIDES = {"tri": 3, "square": 4, "hex": 6}
# First-vertex angle so that rows of LEDs run parallel to a flat edge.
START = {"tri": -90.0, "square": -135.0, "hex": 0.0}


@dataclass
class Port:
    index: int          # 1-based, clockwise starting from the top
    x: float            # edge midpoint
    y: float
    angle: float        # outward normal


@dataclass
class Led:
    index: int          # 1-based position in the data chain
    x: float
    y: float
    flow: int           # +1: data flows left-to-right in this row, -1: right-to-left


def outline(shape, edge):
    n = SIDES[shape]
    r = edge / (2 * math.sin(math.pi / n))
    a0 = START[shape]
    return [(r * math.cos(math.radians(a0 + 360 * i / n)),
             r * math.sin(math.radians(a0 + 360 * i / n))) for i in range(n)]


def inradius(shape, edge):
    return edge / (2 * math.tan(math.pi / SIDES[shape]))


def ports(shape, edge):
    vs = outline(shape, edge)
    out = []
    for i, (a, b) in enumerate(zip(vs, vs[1:] + vs[:1])):
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        out.append((mx, my, math.degrees(math.atan2(my, mx))))
    # P1 is the edge facing up (or the first one clockwise from up)
    out.sort(key=lambda p: (p[2] + 90 + 1e-6) % 360)
    return [Port(i + 1, x, y, a) for i, (x, y, a) in enumerate(out)]


def led_rows(shape, leds):
    """Rows of LED centres (top to bottom, each left to right)."""
    p = leds["pitch"]
    if shape == "square":
        cols, rows = leds["cols"], leds["rows"]
        py = leds.get("pitch_y", p)
        return [[((c - (cols - 1) / 2) * p, (r - (rows - 1) / 2) * py)
                 for c in range(cols)] for r in range(rows)]
    dy = p * math.sqrt(3) / 2
    if shape == "hex":
        n = leds["rings"]
        return [[((c - (2 * n - 2 - abs(r)) / 2) * p, r * dy)
                 for c in range(2 * n - 1 - abs(r))] for r in range(-(n - 1), n)]
    if shape == "tri":
        n = leds["rows"]
        rows = [[((c - r / 2) * p, r * dy) for c in range(r + 1)] for r in range(n)]
        cy = sum(y for row in rows for _, y in row) / sum(len(r) for r in rows)
        return [[(x, y - cy) for x, y in row] for row in rows]
    raise ValueError(f"unknown shape {shape}")


def chain(shape, leds):
    order = []
    for i, row in enumerate(led_rows(shape, leds)):
        flow = 1
        if leds.get("chain", "serpentine") == "serpentine" and i % 2:
            row, flow = row[::-1], -1
        order += [(x, y, flow) for x, y in row]
    return [Led(i + 1, x, y, f) for i, (x, y, f) in enumerate(order)]


def hub_centres(cfg):
    hubs = cfg["hubs"]
    auto = {"PASS": -90.0, "IN": 30.0, "OUT": 150.0}
    turn = hubs.get("angle", 0.0)           # rotate the auto layout (clockwise)
    out = {}
    for role, a in auto.items():
        a += turn
        at = (hubs.get(role) or {}).get("at")
        if at is None:
            r = hubs["radius"]
            at = (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
        out[role] = tuple(at)
    return out


def jumper_positions(hub, port_list, radius):
    """One jumper per port around a hub centre, pointing at that port."""
    hx, hy = hub
    return [(p, hx + radius * math.cos(math.radians(p.angle)),
             hy + radius * math.sin(math.radians(p.angle))) for p in port_list]


def cap_positions(port, along, inset):
    a = math.radians(port.angle)
    nx, ny = math.cos(a), math.sin(a)          # outward normal
    tx, ty = -ny, nx                            # along the edge
    return [(port.x - nx * inset + tx * d, port.y - ny * inset + ty * d)
            for d in along]


def edge_rotations(shape, edge, points, body, margin, step=15.0):
    """Per-LED body rotation (degrees, -45..45, same angle convention as
    above) that keeps a square `body` furthest from the outline edges.

    A rotated square reaches h * (|cos| + |sin|) of the angle between its
    axes and an edge normal towards that edge, so turning an edge LED flat to
    its edge (or splitting the difference in a corner) wins back clearance.
    LEDs with at least `margin` of clearance unrotated stay at 0.
    """
    h = body / 2
    normals = [(p.angle, inradius(shape, edge)) for p in ports(shape, edge)]

    def clearance(x, y, rot):
        out = math.inf
        for a, r in normals:
            ar = math.radians(a)
            d = r - (x * math.cos(ar) + y * math.sin(ar))
            t = math.radians(a - rot)
            out = min(out, d - h * (abs(math.cos(t)) + abs(math.sin(t))))
        return out

    candidates = sorted((k * step for k in range(-int(45 // step), int(45 // step) + 1)),
                        key=abs)                    # ties go to the smallest turn
    rots = []
    for x, y in points:
        if clearance(x, y, 0.0) >= margin:
            rots.append(0.0)
            continue
        rots.append(max(candidates, key=lambda r: round(clearance(x, y, r), 6)))
    return rots
