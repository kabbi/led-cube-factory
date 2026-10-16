# triangular-prism--sq30-3535x16-p6.2-pvia+tri30-3535x10-p6.2-shallow-rot

Two triangles and three squares, 68 LEDs.

<img src="render.png" width="480" alt="render">

| | |
|---|---|
| Solid | triangular-prism, 5 faces |
| Tiles | 3 x square, 2 x triangle |
| LEDs | 68 (3 x 16 + 2 x 10) |
| Size | 30 x 37 x 33 mm (with LEDs) |

## Boards

- **3 x [sq30-3535x16-p6.2-pvia](../../boards/sq30-3535x16-p6.2-pvia/README.md)**: 16 x WS2812B-Mini at 6.2 mm
- **2 x [tri30-3535x10-p6.2-shallow-rot](../../boards/tri30-3535x10-p6.2-shallow-rot/README.md)**: 10 x WS2812B-Mini at 6.2 mm

## Files

- config: [shapes/triangular-prism--sq30-3535x16-p6.2-pvia+tri30-3535x10-p6.2-shallow-rot.yaml](../../../shapes/triangular-prism--sq30-3535x16-p6.2-pvia+tri30-3535x10-p6.2-shallow-rot.yaml)
- rebuild: `make shapes SHAPES=triangular-prism--sq30-3535x16-p6.2-pvia+tri30-3535x10-p6.2-shallow-rot && make docs`
- 3D model: `build/shapes/triangular-prism--sq30-3535x16-p6.2-pvia+tri30-3535x10-p6.2-shallow-rot.glb` (not committed; opens in Blender or any glTF viewer)
