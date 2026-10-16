# cuboctahedron--sq30-2020x64-p2.95-pvia+tri30-2020x36-p2.95-shallow-pvia

The dense cuboctahedron: eight 36-LED triangles and six 8x8 squares, all 2020s at 2.95mm, 672 LEDs.

<img src="render.png" width="480" alt="render">

| | |
|---|---|
| Solid | cuboctahedron, 14 faces |
| Tiles | 6 x square, 8 x triangle |
| LEDs | 672 (6 x 64 + 8 x 36) |
| Size | 47 x 47 x 47 mm (with LEDs) |

## Boards

- **6 x [sq30-2020x64-p2.95-pvia](../../boards/sq30-2020x64-p2.95-pvia/README.md)**: 64 x WS2812B-2020 at 2.95 mm
- **8 x [tri30-2020x36-p2.95-shallow-pvia](../../boards/tri30-2020x36-p2.95-shallow-pvia/README.md)**: 36 x WS2812B-2020 at 2.95 mm

## Files

- config: [shapes/cuboctahedron--sq30-2020x64-p2.95-pvia+tri30-2020x36-p2.95-shallow-pvia.yaml](../../../shapes/cuboctahedron--sq30-2020x64-p2.95-pvia+tri30-2020x36-p2.95-shallow-pvia.yaml)
- rebuild: `make shapes SHAPES=cuboctahedron--sq30-2020x64-p2.95-pvia+tri30-2020x36-p2.95-shallow-pvia && make docs`
- 3D model: `build/shapes/cuboctahedron--sq30-2020x64-p2.95-pvia+tri30-2020x36-p2.95-shallow-pvia.glb` (not committed; opens in Blender or any glTF viewer)
