# square-pyramid--sq30-3535x16-p6.2-pvia+tri30-3535x10-p6.2-shallow-rot

One square and four triangles, 56 LEDs: squares and triangles mating.

<img src="render.png" width="480" alt="render">

| | |
|---|---|
| Solid | square-pyramid, 5 faces |
| Tiles | 1 x square, 4 x triangle |
| LEDs | 56 (1 x 16 + 4 x 10) |
| Size | 34 x 26 x 34 mm (with LEDs) |

## Boards

- **1 x [sq30-3535x16-p6.2-pvia](../../boards/sq30-3535x16-p6.2-pvia/README.md)**: 16 x WS2812B-Mini at 6.2 mm
- **4 x [tri30-3535x10-p6.2-shallow-rot](../../boards/tri30-3535x10-p6.2-shallow-rot/README.md)**: 10 x WS2812B-Mini at 6.2 mm

## Files

- config: [shapes/square-pyramid--sq30-3535x16-p6.2-pvia+tri30-3535x10-p6.2-shallow-rot.yaml](../../../shapes/square-pyramid--sq30-3535x16-p6.2-pvia+tri30-3535x10-p6.2-shallow-rot.yaml)
- rebuild: `make shapes SHAPES=square-pyramid--sq30-3535x16-p6.2-pvia+tri30-3535x10-p6.2-shallow-rot && make docs`
- 3D model: `build/shapes/square-pyramid--sq30-3535x16-p6.2-pvia+tri30-3535x10-p6.2-shallow-rot.glb` (not committed; opens in Blender or any glTF viewer)
