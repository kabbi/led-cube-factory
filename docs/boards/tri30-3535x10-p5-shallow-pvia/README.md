# tri30-3535x10-p5-shallow-pvia

Triangle tile, 4+3+2+1 WS2812B-Mini (3535) at 5mm pitch -- same LED and pitch as sq30-3535x16-p5-pvia, same 30mm edge so it mates with the square tiles.

<img src="model.png" width="480" alt="3D render">

## At a glance

| | |
|---|---|
| Shape | triangle, 30 mm edge, 3 ports |
| LEDs | 10 x WS2812B-Mini (4 + 3 + 2 + 1) |
| Footprint | `tbc:LED_WS2812B-Mini_PLCC4_3.5x3.5mm_InnerPads` |
| LCSC | **TODO** |
| Pitch | 5 mm |
| Rotation | one rotation, DOUT to the right |
| Chain | raster |
| Edge connector | `edge_connector_shallow` (`tbc:edge_conn_shallow`) |
| Back side | generated: IN/OUT/PASS jumper hubs with 3 wings each (3.0 mm from the hub centre, hubs on a 5.5 mm circle), 1 cap per edge |
| Power vias | pattern |
| Router | internal |
| Revision | A |

## Name

| | |
|---|---|
| `tri30` | triangle, 30 mm edge |
| `3535x10` | 10 LEDs in the 3535 package |
| `p5` | 5 mm LED pitch |
| `shallow` | shallow edge-connector pads |
| `pvia` | patterned power vias |

## Build

| | |
|---|---|
| DRC | 0 errors, 0 warnings, 0 unconnected |
| Front track | 112 mm |
| Back track | 98 mm |
| In2 hops | 3.7 mm |
| Vias | 28 |

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

<details><summary>10 LEDs, 3 ports</summary>

| LED | x | y |
|---|---|---|
| 1 | 0.00 | -8.66 |
| 2 | -2.50 | -4.33 |
| 3 | 2.50 | -4.33 |
| 4 | -5.00 | 0.00 |
| 5 | 0.00 | 0.00 |
| 6 | 5.00 | 0.00 |
| 7 | -7.50 | 4.33 |
| 8 | -2.50 | 4.33 |
| 9 | 2.50 | 4.33 |
| 10 | 7.50 | 4.33 |

| Port | x | y | facing |
|---|---|---|---|
| P1 | 7.50 | -4.33 | -30 deg |
| P2 | 0.00 | 8.66 | 90 deg |
| P3 | -7.50 | -4.33 | -150 deg |

</details>

## Files

- config: [boards/tri30-3535x10-p5-shallow-pvia.yaml](../../../boards/tri30-3535x10-p5-shallow-pvia.yaml)
- rebuild: `make all model BOARDS=tri30-3535x10-p5-shallow-pvia && make docs`
- KiCad project, gerbers, BOM/CPL: `build/tri30-3535x10-p5-shallow-pvia/` (not committed)
