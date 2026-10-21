# LED rotation on triangles

2026-10-16. Result: `rotation: edge`, `tri30-3535x10-p6.2-shallow-rot` and its
pitch twin `sq30-3535x16-p6.2-pvia`.

**Question.** Does rotating footprints raise the usable pitch on the 30 mm
3535 triangle ([5 mm without](2026-10-16-triangle-3535.md))?

On a triangle the LED bodies, not the pads, set the pitch: turned all the
same way, a 3535's corner sticks out towards the slanted edges.

Largest pitch keeping every body >= 0.3 mm from the shallow connector pads:

| LED rotation | max pitch |
|---|---|
| one angle for all LEDs (0-75 deg tried) | 5.72-5.78 mm: turning all of them doesn't help |
| each outer LED turned to its own edge | **6.24 mm** |

With one shared angle, the LEDs near the top corner hit the slanted edges
first. Turning each edge LED to face its edge raises the worst gap (at
5.8 mm) from 0.30 to 0.85 mm.

`rotation: edge` turns each outer LED in 15 deg steps flat to its edge
(needs the body size, `body:` in `lib/parts.yaml`): slanted-edge LEDs 30 deg,
bottom corners 15 deg (splitting the difference), top LED a 45 deg diamond;
inner LEDs stay put. Built at 6.2 mm: 0.40 mm body to pads at the corners,
0.60 mm on the flat ones, 1.43 mm between bodies.

Costs:

- Mixed rotations (JLC places any angle; check the assembly preview). The
  one-rotation test allows 15 deg steps of at most 45 deg from a base.
- Patterned power vias need one rotation, so this board uses `nearest`.
- Less regular data chain.

The square needs neither rotation nor the shallow connector at 6.2 mm:
2.57 mm body to pads, 2.71 mm between bodies.
