# Physics Assets — Convincing Worlds for Decision Benchmarks

Status: T0 dynamics in `dmb/physics/` (#26) + weather coupling (#17/#18)
+ T1 source pins with hashes (#17/#19) + vegetation placement script.
T1 world builds and T2 dressing remain (tracked in #6).

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

- Model: deterministic exposure-accumulation cellular spread over the
  fuel grid (Phase B kept determinism over the originally specified
  probabilistic ignition: same seed + weather ⇒ bit-identical spread,
  which the snapshot tests pin). ROS = base × fuel × (1−moisture) ×
  wind-alignment; ignite at exposure ≥ threshold.
- Wind/weather coupling (#17): `weather_modifiers` per scenario override
  wind/moisture; `build_samples(..., weather=...)` makes weather a sample
  axis. Same seed diverges across weather by construction (tested).
- Spread-rate tolerance (forest_fire seeds 1–3 @60 steps, ignited cells):
  haze-heavy 2 (ignitions only — wet+still self-contains), haze-moderate
  39, clear 43. Seed-independent (fixed ignition + uniform fuel).
- Check: fixed-seed spread snapshot test + the tolerance bands above.
- T1: `assets/vegetation/place_trees.py` emits SDF `<include>` per fuel
  cell (seeded pine/oak from pinned Fuel models) + `fuel_tags.json`
  sidecar (instance → flammability). T2 plan: UE particle fire driven by
  the same per-cell ignited/burning/burned schedule; no T0 redefinition.

### Water — floods, flash floods, tsunami

- Standing flood: water plane with level, current vectors, submerged-hazard
  tagging (e.g. power lines), buoyancy for floating victims/debris.
- Flash flood: surge front advancing on a seeded schedule; current strength
  affects victim drift and no-fly/low-altitude risk.
- Tsunami: receding-water warning phase → wave arrival → debris field;
  scenario YAML defines phase timings.
- T1 spike outcome (#18): stock plugins — `gz-sim-buoyancy-system`
  (volume-from-collision buoyancy) + `gz-sim-hydrodynamics-system`
  (current/drag), both shipping with Gazebo incl. Harmonic. No custom
  plugin needed: water plane mesh at z=level, T0 surge schedule drives
  the level/current parameters. T2 plan: UE engine water on the same
  level/current parameters; debris field = instanced meshes on T0 debris
  cells.

### Terrain & soils — landslide physics

- Heightfield terrain with slope, soil saturation, and a documented
  slope-stability rule producing seeded slip events (location, extent,
  debris path). Rain saturates; saturation + slope triggers.
- Debris alters traversability/visibility along the path; victims in the
  path become buried (detectability drops, rescue cost rises).
- Stability rule (T0, tested): saturation += sat_rate × rain_multiplier
  (when raining) each step; at threshold, the steepest candidate slips
  once per episode; debris runs debris_len cells along debris_dir.
  Weather coupling (#18): landslide `overcast` sets raining=false
  (slip @20 vs @11 under rain-heavy, tested).
- T1: SDFormat heightmap geometry (grayscale PNG → heightfield) for
  slope terrain; debris = tinted decal strip on T0 debris cells. T2
  plan: UE landscape import from the same heightmap + GIS refinement.
- Check: slip-event determinism per seed + stability-rule unit tests.

### Actors — humans, children, animals

- Params per actor: category, mobility (`static` | `trapped` | `buried` |
  `mobile`), detectability profile (visual size, thermal/audio cue flags
  for later backends), drift behavior in water.
- T0: grid tokens (exists) + mobility-validated schema
  (static/trapped/buried/mobile; unknown mobility fails at reset) +
  water drift for mobile flooded victims (exists).
- Detectability profile (#19, enforced in the edge stub, mirrored by T1):
  static/mobile full radius @0.9 confidence; trapped 0.75× @0.7; buried
  ⅓× @0.5. Debris burial (landslide) and water drift feed this directly.
- T1: pinned Fuel figures (manifest) with category scaling — human 1.0,
  child 0.7 (scaled standing-person), animal = procedural placeholder
  until a CC0 mesh is vetted (GSO hits are toy scans). T2: animated
  meshes; behavior beyond T0 params stays cosmetic.
- Ethical rule: actors are rescue objectives with documented weights
  (`docs/metrics.md` VICTIM_WEIGHTS, unchanged by this work); no gore,
  no suffering simulation — the benchmark scores decisions, not
  depictions.

## Cross-cutting rules

- `assets/manifest.yaml` pins every external file (URL, hash, license).
  Unpinned assets fail CI (manifest check is part of the assets issues).
- Seeds flow from sample → asset placement → dynamics; `world_hash`
  covers placements, and each dynamic model adds its own snapshot hash.
- When a backend cannot honour a parameter (e.g. no buoyancy plugin), it
  fails loudly at reset — never silent downgrade (same rule as drone specs).
