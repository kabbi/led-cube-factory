# sq30-3535x16-p5-pvia

4x4 WS2812B-Mini (3535) tile at 5mm pitch -- same LED and pitch as the triangle tri30-3535x10-p5-shallow-pvia.

<img src="model.png" width="480" alt="3D render">

## At a glance

| | |
|---|---|
| Shape | square, 30 mm edge, 4 ports |
| LEDs | 16 x WS2812B-Mini (4 x 4) |
| Footprint | `tbc:LED_WS2812B-Mini_PLCC4_3.5x3.5mm_InnerPads` |
| LCSC | **TODO** |
| Pitch | 5 mm |
| Rotation | one rotation, DOUT to the right |
| Chain | raster |
| Edge connector | `edge_connector` (`tbc:edge_conn`) |
| Back side | generated: IN/OUT/PASS jumper hubs with 4 wings each (3.225 mm from the hub centre, hubs on a 7.0 mm circle), 2 caps per edge |
| Power vias | pattern |
| Router | internal |
| Revision | A |

## Name

| | |
|---|---|
| `sq30` | square, 30 mm edge |
| `3535x16` | 16 LEDs in the 3535 package |
| `p5` | 5 mm LED pitch |
| `pvia` | patterned power vias |

## Build

| | |
|---|---|
| DRC | 0 errors, 0 warnings, 0 unconnected |
| Front track | 176 mm |
| Back track | 196 mm |
| In2 hops | 0 mm |
| Vias | 46 |

## Renders

| Top | Bottom |
|---|---|
| <img src="top.png" width="320"> | <img src="bottom.png" width="320"> |

### Layers

| Front: F.Cu, silkscreen | Back, seen from below: B.Cu, silkscreen |
|---|---|
| <img src="front.svg" width="320"> | <img src="back.svg" width="320"> |

| In1: GND plane | In2: +5V plane (and a few hops) |
|---|---|
| <img src="in1.svg" width="320"> | <img src="in2.svg" width="320"> |


## Pixel map

LED index in the data chain -> position, mm from the board centre (y down, top view). Also in [pixelmap.json](pixelmap.json).

<details><summary>16 LEDs, 4 ports</summary>

| LED | x | y |
|---|---|---|
| 1 | -7.50 | -7.50 |
| 2 | -2.50 | -7.50 |
| 3 | 2.50 | -7.50 |
| 4 | 7.50 | -7.50 |
| 5 | -7.50 | -2.50 |
| 6 | -2.50 | -2.50 |
| 7 | 2.50 | -2.50 |
| 8 | 7.50 | -2.50 |
| 9 | -7.50 | 2.50 |
| 10 | -2.50 | 2.50 |
| 11 | 2.50 | 2.50 |
| 12 | 7.50 | 2.50 |
| 13 | -7.50 | 7.50 |
| 14 | -2.50 | 7.50 |
| 15 | 2.50 | 7.50 |
| 16 | 7.50 | 7.50 |

| Port | x | y | facing |
|---|---|---|---|
| P1 | 0.00 | -15.00 | -90 deg |
| P2 | 15.00 | 0.00 | 0 deg |
| P3 | 0.00 | 15.00 | 90 deg |
| P4 | -15.00 | 0.00 | 180 deg |

</details>

## Files

- config: [boards/sq30-3535x16-p5-pvia.yaml](../../../boards/sq30-3535x16-p5-pvia.yaml)
- rebuild: `make all model BOARDS=sq30-3535x16-p5-pvia && make docs`
- KiCad project, gerbers, BOM/CPL: `build/sq30-3535x16-p5-pvia/` (not committed)
