# Peatforest fidelity PRD (#65, rev 2 — hi-fi pass)

Target refs: `generated_images/call_01a1a04be*.jpg` (lush peat forest:
layered broadleaf canopies, palms, undergrowth, mist) and
`generated_images/call_01a1a04bf*.jpg` (ground fire: flames in
undergrowth, charred trunks, smoke columns, embers, sepia haze).

## Parts (numbers)

- 4 tree variants, seeded split: emergent broadleaf 40% (3-tier
  ellipsoid canopy, 10-14 m), palm 25% (curved trunk, 9 fronds,
  8-11 m), round canopy 20% (2 blobs, 7-9 m), understory bush 15%
  (1 squashed blob, 1.5-2.5 m). Per-tree yaw + scale 0.85-1.2 +
  vertex-color tint jitter. Bark PBR on trunks; leaf-card PBR-alpha
  on canopies (masked).
- Charred: trunk + 2-3 branch stubs + optional fallen log, dark bark,
  no canopy. Same placement seed, burn mask unchanged (250 m).
- Ground: S2 albedo x tiled peat-mud detail (albedo + normal),
  lit (no emissive wash). Burn patches: charred-ground texture with
  radial alpha at each hotspot (~30 m).
- Fire per front: 3 crossed flame planes (scrolling procedural flame
  texture, emissive) + core plane + 3 stacked smoke sprites
  (translucent) + glow disc + 1 orange PointLight (no shadows).
- Atmosphere: sun 10 (whiteout guard, keep), warm low angle; burning
  fog stays heavy sepia.

## Acceptance (render-vs-ref)

1. Approach frame: individual crowns + trunk texture readable at
   120 m; >=3 variants distinguishable.
2. Near frame (<40 m): bark furrows + leaf cards (not Big Green Cone).
3. Fire frame: layered flames + smoke column + glow on ground;
   orange light on nearby trunks.
4. h100: closed-canopy read with gaps, burn scar visible, haze.
5. No whiteout (white 0.0), no walls, spawn/flight/eval still green.
6. Perf: capture round-trip p95 < 100 ms.
