# Physics Assets — Convincing Worlds for Decision Benchmarks

Status: T0 dynamics implemented in `dmb/physics/` (#26) — FBP-inspired cell
fire spread, surge-front water with drift, saturation-triggered slip with
debris burial. T1 plugins and T2 dressing remain in #17/#18.

Principle: physics must be **convincing where decisions depend on it** and
honestly simple elsewhere. A fire model that spreads wrong teaches the
benchmark to reward wrong plans; a tree that is only a billboard is fine if
no decision depends on branches. Every asset pack below ships with a
**plausibility + determinism check**, not just meshes.

## Fidelity tiers

- **T0 mock**: parameters on the grid (flammability per cell, water level per
  cell, slope per cell). Runs everywhere; defines the semantics.
- **T1 Gazebo**: meshes + plugins (vegetation instances, water planes with
  buoyancy/current, heightfield terrain, actor figures).
- **T2 Unreal**: photoreal dressing + engine physics on the same parameters.

Tiers share one parameter schema per asset type; higher tiers render, never
redefine, T0 semantics.

## Asset catalog

### Vegetation — forests, trees, bushes (fire fuel)

- Per-instance params: species class, height, canopy density, moisture,
  **flammability 0–1**.
- T0: fuel grid over the scenario; T1: instanced tree/bush meshes with
  per-instance flammability tags; T2: dressed forest.
- Sourcing (spike verifies): open model libraries / procedural generation
  for T1; marketplace/GIS vegetation for T2. Pin URL + hash + license.

### Fire spread — bush-to-bush transfer

- Model: seeded probabilistic cellular spread over the fuel grid —
  ignition probability per step from neighbor state × flammability ×
  wind × moisture. Defined in the asset issue, implemented once in T0,
  mirrored by a Gazebo plugin (T1) and particles (T2).
- Wind/weather coupling comes from the scenario's weather options, so
  identical seeds under different weather diverge documentably.
- Check: fixed-seed spread snapshot test + documented spread-rate tolerance.

### Water — floods, flash floods, tsunami

- Standing flood: water plane with level, current vectors, submerged-hazard
  tagging (e.g. power lines), buoyancy for floating victims/debris.
- Flash flood: surge front advancing on a seeded schedule; current strength
  affects victim drift and no-fly/low-altitude risk.
- Tsunami: receding-water warning phase → wave arrival → debris field;
  scenario YAML defines phase timings.
- T1 needs a water/buoyancy plugin (spike verifies available plugin vs.
  custom); T2 uses engine water on the same level/current parameters.

### Terrain & soils — landslide physics

- Heightfield terrain with slope, soil saturation, and a documented
  slope-stability rule producing seeded slip events (location, extent,
  debris path). Rain saturates; saturation + slope triggers.
- Debris alters traversability/visibility along the path; victims in the
  path become buried (detectability drops, rescue cost rises).
- Check: slip-event determinism per seed + stability-rule unit tests.

### Actors — humans, children, animals

- Params per actor: category, mobility (`static` | `trapped` | `buried` |
  `mobile`), detectability profile (visual size, thermal/audio cue flags
  for later backends), drift behavior in water.
- T0: grid tokens (exists). T1: articulated/static figures with category
  scaling; T2: animated meshes. Behavior beyond T0 params is cosmetic.
- Ethical rule: actors are rescue objectives with documented weights
  (`docs/metrics.md`); no gore, no suffering simulation — the benchmark
  scores decisions, not depictions.

## Cross-cutting rules

- `assets/manifest.yaml` pins every external file (URL, hash, license).
  Unpinned assets fail CI (manifest check is part of the assets issues).
- Seeds flow from sample → asset placement → dynamics; `world_hash`
  covers placements, and each dynamic model adds its own snapshot hash.
- When a backend cannot honour a parameter (e.g. no buoyancy plugin), it
  fails loudly at reset — never silent downgrade (same rule as drone specs).
