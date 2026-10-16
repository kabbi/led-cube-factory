# truncated-octahedron--sq30-5050x16-p7.112-tpl+hex30-5050x37-p8-pvia

Six squares and eight hexagons of 5050s, 392 LEDs.

<img src="render.png" width="480" alt="render">

| | |
|---|---|
| Solid | truncated-octahedron, 14 faces |
| Tiles | 8 x hexagon, 6 x square |
| LEDs | 392 (8 x 37 + 6 x 16) |
| Size | 91 x 91 x 91 mm (with LEDs) |

## Boards

- **6 x [sq30-5050x16-p7.112-tpl](../../boards/sq30-5050x16-p7.112-tpl/README.md)**: 16 x WS2812B at 7.112 mm
- **8 x [hex30-5050x37-p8-pvia](../../boards/hex30-5050x37-p8-pvia/README.md)**: 37 x WS2812B at 8 mm

## Files

- config: [shapes/truncated-octahedron--sq30-5050x16-p7.112-tpl+hex30-5050x37-p8-pvia.yaml](../../../shapes/truncated-octahedron--sq30-5050x16-p7.112-tpl+hex30-5050x37-p8-pvia.yaml)
- rebuild: `make shapes SHAPES=truncated-octahedron--sq30-5050x16-p7.112-tpl+hex30-5050x37-p8-pvia && make docs`
- 3D model: `build/shapes/truncated-octahedron--sq30-5050x16-p7.112-tpl+hex30-5050x37-p8-pvia.glb` (not committed; opens in Blender or any glTF viewer)
