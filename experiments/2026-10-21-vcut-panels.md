# V-cut panels vs tabs

2026-10-20/21. Result: `layout: vcut` + `panels/jlc-vcut.json`;
`sq15-micro-mix-24`, `sq8-...-11x6`; both 30 mm square panels moved to V-cuts.

**Question.** One panel of all the small tiles (6 x 2x2, 6 x 4x4, the rest
1x1) with as little post-processing after breaking out as possible; then:
should all square panels be V-cut?

## One mixed micro panel

V-cuts only, no tabs: edges break flush, no nubs. Fits 100 x 95 mm with
6 + 6 + 25 tiles, but a V-cut runs across the whole panel, so 15 mm and 8 mm
tiles need separate column and row bands, and every cell where a 15 mm band
crosses an 8 mm band is scrap:

```
   15 15 15 15  8 8 8 8 8
15  A  A  A  A  . . . . .
15  A  A  B  B  . . . . .
15  B  B  B  B  . . . . .
 8  .  .  .  .  c c c c c     (x5 rows)
```

Split into two panels instead, no scrap: most that fits 100 x 100 is 6 x 6
of the 15 mm tiles and 12 x 11 of the 8 mm; built smaller (12 + 12 at
90 x 70 mm, 66 at 88 x 58 mm).

## V-cut or tabs

V-cuts gain:

- no nubs: flush edges for tiles that butt together;
- no 2 mm gaps: a 30 mm 3x2 drops from 94 x 76 to 90 x 70 mm, and 3x3 fits
  100 x 100;
- snap along the lines.

Tabs + mousebites keep:

- any shape: V-cuts are straight lines, so triangles and hexagons stay tabbed;
- distance from edge copper: a tab touches only the copper-free run by each
  corner, while a V-cut runs past every connector pad. Ours sit 0.115 mm from
  the cut against JLC's usual 0.4 mm, so expect JLC to query the order (the
  score should only skim ~25 um off the pads' outer edge);
- mixed sizes without bands;
- a milled edge: a V-cut edge has 30 deg bevels and a rougher snapped band
  that can leave a small ridge;
- a stiffer panel: a grid scored through has ~1/3 thickness at each line.

Went with V-cuts for the squares (kept 3x2).

## Solder-mask bridges across the cut

The dense 2020 panel first failed panel DRC with 70 solder-mask bridges: the
template's mask openings on facing pads of neighbouring boards merge across
the cut line. It pairs two boards' nets and sits on the cut, which removes
it, so panel DRC waives exactly that case and lists it as
`waived:solder_mask_bridge`. The 3535 panel has none (smaller openings).
