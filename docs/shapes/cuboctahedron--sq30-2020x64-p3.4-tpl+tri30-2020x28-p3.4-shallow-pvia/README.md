# cuboctahedron--sq30-2020x64-p3.4-tpl+tri30-2020x28-p3.4-shallow-pvia

Eight 28-LED 2020 triangles and six hand-drawn 8x8 2020 squares, all at 3.4mm, 608 LEDs.

<img src="render.png" width="480" alt="render">

| | |
|---|---|
| Solid | cuboctahedron, 14 faces |
| Tiles | 6 x square, 8 x triangle |
| LEDs | 608 (6 x 64 + 8 x 28) |
| Size | 47 x 47 x 47 mm (with LEDs) |

## Boards

- **6 x [sq30-2020x64-p3.4-tpl](../../boards/sq30-2020x64-p3.4-tpl/README.md)**: 64 x WS2812B-2020 at 3.4 mm
- **8 x [tri30-2020x28-p3.4-shallow-pvia](../../boards/tri30-2020x28-p3.4-shallow-pvia/README.md)**: 28 x WS2812B-2020 at 3.4 mm

## Files

- config: [shapes/cuboctahedron--sq30-2020x64-p3.4-tpl+tri30-2020x28-p3.4-shallow-pvia.yaml](../../../shapes/cuboctahedron--sq30-2020x64-p3.4-tpl+tri30-2020x28-p3.4-shallow-pvia.yaml)
- rebuild: `make shapes SHAPES=cuboctahedron--sq30-2020x64-p3.4-tpl+tri30-2020x28-p3.4-shallow-pvia && make docs`
- 3D model: `build/shapes/cuboctahedron--sq30-2020x64-p3.4-tpl+tri30-2020x28-p3.4-shallow-pvia.glb` (not committed; opens in Blender or any glTF viewer)
