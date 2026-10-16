# truncated-octahedron--sq30-2020x64-p3.4-tpl+hex30-2020x169-p3.7-pvia

Six 8x8 squares and eight 169-LED hexagons of 2020s at the same LED density, 1736 LEDs.

<img src="render.png" width="480" alt="render">

| | |
|---|---|
| Solid | truncated-octahedron, 14 faces |
| Tiles | 8 x hexagon, 6 x square |
| LEDs | 1736 (8 x 169 + 6 x 64) |
| Size | 90 x 90 x 90 mm (with LEDs) |

## Boards

- **6 x [sq30-2020x64-p3.4-tpl](../../boards/sq30-2020x64-p3.4-tpl/README.md)**: 64 x WS2812B-2020 at 3.4 mm
- **8 x [hex30-2020x169-p3.7-pvia](../../boards/hex30-2020x169-p3.7-pvia/README.md)**: 169 x WS2812B-2020 at 3.7 mm

## Files

- config: [shapes/truncated-octahedron--sq30-2020x64-p3.4-tpl+hex30-2020x169-p3.7-pvia.yaml](../../../shapes/truncated-octahedron--sq30-2020x64-p3.4-tpl+hex30-2020x169-p3.7-pvia.yaml)
- rebuild: `make shapes SHAPES=truncated-octahedron--sq30-2020x64-p3.4-tpl+hex30-2020x169-p3.7-pvia && make docs`
- 3D model: `build/shapes/truncated-octahedron--sq30-2020x64-p3.4-tpl+hex30-2020x169-p3.7-pvia.glb` (not committed; opens in Blender or any glTF viewer)
