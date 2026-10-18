# sq15-2020x16-p2.85-micro-pvia

4x4 WS2812B-2020 at 2.85mm pitch (courtyards just clear) on a 15mm square, with the micro edge connector like the other small tiles. Fits 13.5mm (the LED pads 0.25mm from the connector pads); 15mm to match the 2x2 5050.

<img src="model.png" width="480" alt="3D render">

## At a glance

| | |
|---|---|
| Shape | square, 15 mm edge, 4 ports |
| LEDs | 16 x WS2812B-2020 (4 x 4) |
| Footprint | `tbc:LED_WS2812B-2020_PLCC4_2.0x2.0mm` |
| LCSC | C52917434 |
| Pitch | 2.85 mm |
| Rotation | one rotation, DOUT to the right |
| Chain | raster |
| Edge connector | `edge_connector_micro` (`tbc:edge_conn_micro`) |
| Back side | generated: IN/OUT/PASS jumper hubs with 4 wings each (1.7 mm from the hub centre, hubs on a 4.2 mm circle), 1 cap on P2 |
| Power vias | pattern |
| Router | internal |
| Revision | A |

## Name

| | |
|---|---|
| `sq15` | square, 15 mm edge |
| `2020x16` | 16 LEDs in the 2020 package |
| `p2.85` | 2.85 mm LED pitch |
| `micro` | micro edge connector (small tiles) |
| `pvia` | patterned power vias |

## Build

| | |
|---|---|
| DRC | 0 errors, 0 warnings, 0 unconnected |
| Front track | 118 mm |
| Back track | 70 mm |
| In2 hops | 5.5 mm |
| Vias | 40 |

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
| 1 | -4.28 | -4.28 |
| 2 | -1.43 | -4.28 |
| 3 | 1.43 | -4.28 |
| 4 | 4.28 | -4.28 |
| 5 | -4.28 | -1.43 |
| 6 | -1.43 | -1.43 |
| 7 | 1.43 | -1.43 |
| 8 | 4.28 | -1.43 |
| 9 | -4.28 | 1.43 |
| 10 | -1.43 | 1.43 |
| 11 | 1.43 | 1.43 |
| 12 | 4.28 | 1.43 |
| 13 | -4.28 | 4.28 |
| 14 | -1.43 | 4.28 |
| 15 | 1.43 | 4.28 |
| 16 | 4.28 | 4.28 |

| Port | x | y | facing |
|---|---|---|---|
| P1 | 0.00 | -7.50 | -90 deg |
| P2 | 7.50 | 0.00 | 0 deg |
| P3 | 0.00 | 7.50 | 90 deg |
| P4 | -7.50 | 0.00 | 180 deg |

</details>

## Used in

- [cube--sq15-2020x16-p2.85-micro-pvia](../../shapes/cube--sq15-2020x16-p2.85-micro-pvia/README.md)

## Files

- config: [boards/sq15-2020x16-p2.85-micro-pvia.yaml](../../../boards/sq15-2020x16-p2.85-micro-pvia.yaml)
- rebuild: `make all model BOARDS=sq15-2020x16-p2.85-micro-pvia && make docs`
- KiCad project, gerbers, BOM/CPL: `build/sq15-2020x16-p2.85-micro-pvia/` (not committed)
