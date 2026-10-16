# sq30-2020x64-p3.4-tpl

8x8 WS2812B-2020 tile -- same form factor as thecube/denser_v4, with the 2020 pinout fixed.

<img src="model.png" width="480" alt="3D render">

## At a glance

| | |
|---|---|
| Shape | square, 30 mm edge, 4 ports |
| LEDs | 64 x WS2812B-2020 (8 x 8) |
| Footprint | `tbc:LED_WS2812B-2020_PLCC4_2.0x2.0mm` |
| LCSC | C52917434 |
| Pitch | 3.4 mm |
| Rotation | one rotation, DOUT to the right |
| Chain | raster |
| Edge connector | from the template |
| Back side | hand-drawn template `square30-dense` |
| Power vias | nearest |
| Router | internal |
| Revision | A |

## Name

| | |
|---|---|
| `sq30` | square, 30 mm edge |
| `2020x64` | 64 LEDs in the 2020 package |
| `p3.4` | 3.4 mm LED pitch |
| `tpl` | hand-drawn back side from a template |

## Build

| | |
|---|---|
| DRC | 0 errors, 0 warnings, 0 unconnected |
| Front track | 439 mm |
| Back track | 192 mm |
| In2 hops | 29.1 mm |
| Vias | 150 |

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

<details><summary>64 LEDs, 4 ports</summary>

| LED | x | y |
|---|---|---|
| 1 | -11.90 | -11.90 |
| 2 | -8.50 | -11.90 |
| 3 | -5.10 | -11.90 |
| 4 | -1.70 | -11.90 |
| 5 | 1.70 | -11.90 |
| 6 | 5.10 | -11.90 |
| 7 | 8.50 | -11.90 |
| 8 | 11.90 | -11.90 |
| 9 | -11.90 | -8.50 |
| 10 | -8.50 | -8.50 |
| 11 | -5.10 | -8.50 |
| 12 | -1.70 | -8.50 |
| 13 | 1.70 | -8.50 |
| 14 | 5.10 | -8.50 |
| 15 | 8.50 | -8.50 |
| 16 | 11.90 | -8.50 |
| 17 | -11.90 | -5.10 |
| 18 | -8.50 | -5.10 |
| 19 | -5.10 | -5.10 |
| 20 | -1.70 | -5.10 |
| 21 | 1.70 | -5.10 |
| 22 | 5.10 | -5.10 |
| 23 | 8.50 | -5.10 |
| 24 | 11.90 | -5.10 |
| 25 | -11.90 | -1.70 |
| 26 | -8.50 | -1.70 |
| 27 | -5.10 | -1.70 |
| 28 | -1.70 | -1.70 |
| 29 | 1.70 | -1.70 |
| 30 | 5.10 | -1.70 |
| 31 | 8.50 | -1.70 |
| 32 | 11.90 | -1.70 |
| 33 | -11.90 | 1.70 |
| 34 | -8.50 | 1.70 |
| 35 | -5.10 | 1.70 |
| 36 | -1.70 | 1.70 |
| 37 | 1.70 | 1.70 |
| 38 | 5.10 | 1.70 |
| 39 | 8.50 | 1.70 |
| 40 | 11.90 | 1.70 |
| 41 | -11.90 | 5.10 |
| 42 | -8.50 | 5.10 |
| 43 | -5.10 | 5.10 |
| 44 | -1.70 | 5.10 |
| 45 | 1.70 | 5.10 |
| 46 | 5.10 | 5.10 |
| 47 | 8.50 | 5.10 |
| 48 | 11.90 | 5.10 |
| 49 | -11.90 | 8.50 |
| 50 | -8.50 | 8.50 |
| 51 | -5.10 | 8.50 |
| 52 | -1.70 | 8.50 |
| 53 | 1.70 | 8.50 |
| 54 | 5.10 | 8.50 |
| 55 | 8.50 | 8.50 |
| 56 | 11.90 | 8.50 |
| 57 | -11.90 | 11.90 |
| 58 | -8.50 | 11.90 |
| 59 | -5.10 | 11.90 |
| 60 | -1.70 | 11.90 |
| 61 | 1.70 | 11.90 |
| 62 | 5.10 | 11.90 |
| 63 | 8.50 | 11.90 |
| 64 | 11.90 | 11.90 |

| Port | x | y | facing |
|---|---|---|---|
| P1 | 0.00 | -15.00 | -90 deg |
| P2 | 15.00 | 0.00 | 0 deg |
| P3 | 0.00 | 15.00 | 90 deg |
| P4 | -15.00 | 0.00 | 180 deg |

</details>

## Used in

- [cube--sq30-2020x64-p3.4-tpl](../../shapes/cube--sq30-2020x64-p3.4-tpl/README.md)

## Files

- config: [boards/sq30-2020x64-p3.4-tpl.yaml](../../../boards/sq30-2020x64-p3.4-tpl.yaml)
- rebuild: `make all model BOARDS=sq30-2020x64-p3.4-tpl && make docs`
- KiCad project, gerbers, BOM/CPL: `build/sq30-2020x64-p3.4-tpl/` (not committed)
