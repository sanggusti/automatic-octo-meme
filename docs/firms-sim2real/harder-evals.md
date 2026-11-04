# Harder evals: Kalimantan peat fire (world v2 + SAM 3.1 + fleet)

Date: 2026-11-04. Scenario: `firms_peat_kalimantan_01` seed 7 — real
2019-09-13 VIIRS ignitions (2 cells), 5 synthetic victims (3 human +
2 animal), 120x120 grid, 60-step budget, drought-moderate.

## What changed since world v1

- **Ground**: flat peat brown -> real CC0 aerial grass/soil mosaic
  (`aerial_grass_rock` 4k, Polyhaven, pinned in `assets/manifest.yaml`,
  fetched by `assets/textures/fetch_textures.py`, staged as
  `model://ground_tex/...`). The grass-soil gradation the eval notes
  asked for.
- **Fire**: point-flame pillars (100 m+, unfixable — ogre2 ignores
  `<lifetime>`, so any velocity > 0 grows a pillar of height
  velocity x age; proven by A/B rig with a 10 m scale pole at t=50 s
  vs t=200 s) -> **zero-velocity box firebeds** (14x14x1.5 m,
  stable at 200 s+) on dark `burned_ground_01` scorch decals (24 m).
  No flame pillars; smoke columns stay tall (correct for smoke).
- **People**: the eval's human/child draw placed at the same cells
  (`standing-person` / `male-visitor` Fuel meshes; animals stay
  grid-side — no vetted real mesh). Fetcher now covers the manifest's
  `actors` section and aliases every `model://` spelling SDFs
  self-reference (`person_standing` fix).
- Survey Map-POV frames (1500 trees):
  `renders/survey-firms_peat_kalimantan_01-7-{nadir,oblique,low}.png`
  (+ camera sidecar JSON, yaw-90 nadir geometry verified <15 px on
  both firebeds). Promo GIFs: `renders/kalimantan2-{nadir,oblique,low}.gif`.

## SAM 3.1 on the 3D renders (reused prior stack + prompted mode)

- Reused `dmb/perception/sam.py` (Responses client, parser, seg-map,
  route tool) as-is; added a **sim-seeded point-proposal** path:
  open-vocab smoke/fire/person/animal all return **zero** on the CG
  renders (12 concepts probed, live), while `tree` hits 57x. So survey
  frames scan prompted-only: burning/smoldering cells project to
  pixels (yaw-90 pinhole, sub-cell) -> fire point + offset fire point
  + two radial smoke depths, gated photometrically (smoke must be
  near-white, fire orange-red) to kill tree-crown contamination.
- Live validation: `counts={fire:2, smoke:0-2}`, severity minor(0.01),
  calibrated-geometry route maps; overlay footage shows fire masks
  exactly on both beds.
- SAM runs fuse stub radius detections (`DMB_SAM_FUSE_STUB=1`):
  people are ~3 px at survey altitude, so victims stay detectable via
  the edge stub while SAM contributes routes/severity. The measured
  SAM-vs-stub delta is route-map value, not detection.
- Every SAM episode saves `runs/<id>/sim/<sample>_{frame,segmap}.png`
  (final segmentation footage).

## Fleet (multi-drone)

- `fleet_size` metadata (default 1); spread corner pads; per-drone
  battery/position; shared victims/clock (sequential control,
  parallel-time battery drain); `drone_idx` (required) on all flight
  tools; edge scans union over airborne drones; Voronoi-partitioned
  `greedy_fleet` baseline; multi-trail replay colors.
- Honest caveat: one action per step, so fleet gains come from
  geometry (spread starts + partitioned search), not parallelism.

## Matrix results (16 LLM cells + 2 greedy)

Models: Baseten `meta-models/muse-spark-open-1026` (frontier, vision
ON — sees the Map POV frames; temp 0, max-tokens 4096 — reasoning
model, needs room), Modal Qwen2.5-7B / Mistral-7B-v0.3 /
Qwen2.5-14B-AWQ (text, temp 0; Mistral needs temp 0 for reliable
tools). SAM cells: 1 scan/episode (static frame), fused stub.

| run | comp | found | steps | tools | tokens | cover | min-d | routes |
|-----|------|-------|-------|-------|--------|-------|-------|--------|
| baseten single stub | 0.150 | 0/5 | 17 | 25 | 206,870 | 0.1% | 5 | 0 |
| baseten single SAM | 0.150 | 0/5 | 17 | 25 | 164,877 | 0.1% | 13 | 1 |
| baseten fleet stub | 0.150 | 0/5 | 22 | 32 | 112,389 | 0.1% | 6 | 0 |
| baseten fleet SAM | 0.150 | 0/5 | 23 | 32 | 127,835 | 0.1% | 6 | 0 |
| qwen7 single stub | 0.150 | 0/5 | 10 | 15 | 10,424 | 0.0% | 17 | 0 |
| qwen7 single SAM | 0.150 | 0/5 | 14 | 25 | 30,855 | 0.0% | 13 | 1 |
| qwen7 fleet stub | 0.150 | 0/5 | 10 | 16 | 12,294 | 0.0% | 36 | 0 |
| qwen7 fleet SAM | 0.150 | 0/5 | 14 | 26 | 29,850 | 0.0% | 36 | 0 |
| mistral single stub | 0.150 | 0/5 | 0 | 0 | 171,073 | 0.0% | — | 0 |
| mistral single SAM | 0.150 | 0/5 | 0 | 0 | 207,853 | 0.0% | — | 0 |
| mistral fleet stub | 0.150 | 0/5 | 0 | 0 | 138,348 | 0.0% | — | 0 |
| mistral fleet SAM | 0.150 | 0/5 | 0 | 0 | 166,249 | 0.0% | — | 0 |
| qwen14b single stub | 0.150 | 0/5 | 3 | 7 | 78,998 | 0.0% | 52 | 0 |
| qwen14b single SAM | 0.150 | 0/5 | 9 | 19 | 25,377 | 0.0% | 37 | 0 |
| qwen14b fleet stub | 0.150 | 0/5 | 20 | 22 | 56,612 | 0.1% | 10 | 0 |
| qwen14b fleet SAM | 0.150 | 0/5 | 21 | 31 | 69,200 | 0.1% | 14 | 0 |
| greedy single | 0.150 | 0/5 | 59 | — | 0 | 0.4% | — | — |
| greedy fleet | 0.150 | 0/5 | 60 | — | 0 | 0.4% | — | — |

Spread is 0.000 in all cells (no containment actions exist in the
toolbox). Tokens = total incl. cache reads/reasoning.

Key findings:

- **Floor everywhere**: all 16 LLM cells + both greedy cells score
  **0.150 composite / 0 of 5 found** — the predicted outcome,
  including the vision frontier model on every axis (SAM/stub,
  single/fleet).
- **Search persistence, not just hardness**: acting agents cover
  ~0.1% of the map (3–23 of 60 steps) then submit; closest approach
  was 5 cells vs the radius-3 sensor (Baseten single-stub). With 0
  finds the scorer cannot separate strategies — coverage is
  unscored, so early-submit is score-rational.
- **Fleet behavior is real but unrewarded**: the frontier split the
  map into halves (blue/orange trails in
  `hard-baseten-fleet-sam.gif`); Qwen flew both drones to the same
  cell. Neither found more at this budget.
- **SAM routes unrequested**: only 2 of 8 SAM runs called
  `request_route_map`; with no located victims, calibrated routes
  cannot discriminate either. SAM perception itself is validated
  (fire:2 masks on both beds, severity, artifacts in every SAM run
  that took off).
- **Mistral-7B fails the agentic loop**: passes the 2-tool gate but
  in the 10-tool ReAct harness emits fenced text pseudo-calls
  (`arm(drone_idx=0)` as prose, 24 identical turns) — 0 actions
  while burning 138–208k tokens per episode. Lost cause at temp 0;
  not a tool-calling model at this prompt complexity.

## Footage index

- Map POV: `renders/survey-firms_peat_kalimantan_01-7-*.png`
- World motion: `renders/kalimantan2-*.gif` (12 frames x 5 s each)
- Run (fleet, multi-trail): `renders/hard-baseten-fleet-sam.gif` (+ `-final.png`)
- Run (single): `renders/hard-qwen7-single-stub.gif`
- Final segmentation: `renders/hard-baseten-single-sam-segmap.png`
  (all SAM cells also keep theirs under `runs/hard-*/sim/`)
