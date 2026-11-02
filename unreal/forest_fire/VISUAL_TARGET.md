# Visual Target — Peatland Forest Fire (#50)

What the UE burning variant must read as, phase by phase. Grounded in
October 2026 reporting on the Indonesian peat fires; every behaviour
below maps to a T0 quantity so the look never contradicts the sim.

## References (inspected 2026-11-02)

- El Nino-driven peat fires, haze crisis, 120k+ hotspots, 175 Mt carbon:
  `https://phys.org/news/2026-10-indonesia-el-niodriven-peat-region.html`
- Peat smoulder, re-emergence, thicker smoke, API 1,300-1,600 in
  Kalimantan (hazardous = 300), restoration vow:
  `https://krro.com/2026/10/15/indonesia-blames-peatland-degradation-for-raging-fires-vows-restoration/`
- Haze visual guide, 895,657 ha burned, drained-peatland worst fires:
  `https://conven.org/indonesia/news/the-physical-toll-is-visceral-how-indonesias-fire-haze-affects-millions-visual-guide-indonesia/`
- GIS-mapped UE5+AirSim env precedent (ESARBench):
  `https://arxiv.org/abs/2605.01371` and
  `https://github.com/cammm123/esar`

## Behavioural facts the look must honour

1. The fire smoulders **downwards into dried peat** for weeks/months;
   water cannot stop it, only rain. Surface flame is the late stage.
2. Worst fires sit on **drained, dried-out peatland** (canals, plantation
   mosaic), not intact swamp forest.
3. Peat smoke is **thicker** than surface-fire smoke; smoulder can
   **re-emerge anytime**, away from the visible front.
4. Haze is the regional killer: sepia skies, sun as a dim disc,
   visibility down to tens of metres near the fire.

## Phases (T0 mapping)

| # | Look | T0 driver |
|---|---|---|
| 0 | Drained peatland mosaic: dark peat soil, swamp-forest blocks, straight drainage canals, palm rows at the margin. Hazy-blue horizon. | Before variant: no fire state |
| 1 | Ground smoulder: thin blue-grey smoke wisps rising from soil cracks and root holes; faint orange glow at the cracks after dusk. No flame. | `smoldering` cells, `haze` < 0.3 |
| 2 | Breakout: low orange flame in underbrush at scattered points, each with a white-grey smoke column leaning downwind. | New `ignited` cells, `burning` rising |
| 3 | Running fire: flame wall at the peat-block edge under wind, dark brown-grey smoke mass, ember drift downwind. | `burning` peak, `haze` > 0.7 |
| 4 | Haze aftermath: sepia/orange sky, dim-disc sun, charred black ground with smoking stumps, visibility tens of metres. | `burned` cells, `haze` ~ 1.0 |

## Palette (sRGB, eye-matched in-engine)

- Peat soil: near-black brown `#1a120b`-`#2b1d12`
- Swamp canopy: deep yellow-green `#2f4a1e`-`#4a6b2a`
- Fresh smoke: warm light grey `#cfc8bd`; aged haze: sepia `#b98d4f`
- Sky (haze): pale orange-tan `#d9a861` to grey `#8a7f70`
- Flame core: `#ff7a1a`, tips `#ffc42e`; night crack-glow: `#e04a00`

## UE mapping notes

- One step = 5 sim-seconds; play `fire_schedule.json` verbatim.
- Smouldering cells: ground smoke emitters + emissive crack decals,
  no flames. Burning cells: flame + column emitters. Burned cells:
  charred material swap, stump smoke while `haze` stays high.
- Fog density follows the `haze` curve, not a fixed value; phase 4
  must read opaque at drone altitude, matching T0 `visibility: low`.
- The drone must stay visible against smoke at snapshot range: verify
  with one captured keyframe per phase before calling the look done.
