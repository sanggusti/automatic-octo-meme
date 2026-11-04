# FIRMS sim-to-real evaluation

How the Kalimantan peatland worlds connect to real satellite fire
observations, and what the numbers mean.

## Data

NASA FIRMS VIIRS archive (`data/firm/fire_archive_SV-C2_836814.csv`,
391,641 hotspots, 2019-09-01..2019-10-31). 289,844 fall in the
Indonesia bbox. Three peat events anchored from 0.5° cluster ranking:

| scenario | anchor | t0 | day-0 cells | FRP mean/max |
|---|---|---|---|---|
| firms_peat_sumatra_01 | -1.742, 103.997 | 2019-09-20 | 4 | 47.7 / 89.7 |
| firms_peat_kalimantan_01 | -2.808, 114.027 | 2019-09-13 | 2 | 45.8 / 89.3 |
| firms_peat_sumatra_02 (smoldering) | -3.683, 105.673 | 2019-10-14 | 3 | 3.4 / 5.4 |

Parser + equirectangular anchor-centered projector: `dmb/data/firms.py`.
Day-0 hotspot cells become scenario ignitions; day-1..7 NEW cells (not
present day-0) become the spread reference (`firms.ref_new_cells`).
Comparison happens at fine-cell scale (5 m cells) with a 75 m (15-cell)
tolerance for sub-pixel VIIRS drift.

## What the data supports (and does not)

Peat fires creep: day-1..7 yields 1-2 new fine cells per event. A
pixel-overlap score on 1-2 cells is coarse by construction, so the
methodology leans on three legs:

1. **Ignition realism (strong).** Scenarios start with the real
   ignition count, geometry, and intensity (FRP-mapped fuel).
2. **Persistence signature (strong).** Real peat fires stay in-block
   for 7 days. A sim that burns out or runs away in the same window
   disagrees with the signature; `spread_extent_ratio` quantifies it.
3. **Cell-tolerant overlap (weak but standard).**
   `spread_recall_75m` / `spread_precision_75m` at 75 m tolerance,
   reported with n.

Caveats, stated plainly:

* **Resolution mismatch.** VIIRS pixels are 375 m; sim cells are 5 m.
  Each reference cell stands for a whole pixel, so `spread_extent_ratio`
  (sim 5 m cells over real cells) is intrinsically inflated and is
  reported informational, not gated.
* **Tiny n.** With 1-2 reference cells, recall takes values in
  {0, 0.5, 1}. Report it alongside `n_ref_cells`, never alone.
* **No victim data.** Victims are synthetic-seeded; FIRMS carries no
  victim information. Rescue metrics stay sim-side.
* **No wall-time mapping.** Sim steps are not days; extent comparisons
  are order-of-magnitude, not calibrated.

## Baseline (greedy policy, drought-moderate, seed 7)

| scenario | sim burned | recall | precision | extent_ratio | n_ref |
|---|---|---|---|---|---|
| sumatra_01 | 180 | 0.50 | 1.00 | 30.0 | 2 |
| kalimantan_01 | 90 | 1.00 | 1.00 | 30.0 | 1 |
| sumatra_02 | 211 | 0.00 | 1.00 | 42.2 | 2 |

Read: the sim reaches some real spread cells (recall 0-1) while
burning ~30-40x more cells than the reference set -- the honest
over-spread signal at these params, and the input to spread
calibration (see physics tolerance bands). Precision 1.0 everywhere
means all burning stays within 75 m of real fire -- no phantom fronts.

Reproduce: `build_samples(<scenario>, [7], weather="drought-moderate")`,
`run_baseline(meta, "greedy")`, `compute_spread_scores(final, meta["firms"])`.

## Model runs (footage in `renders/`)

* `kalimantan-{nadir,oblique,low}.gif`: 5 s each, 3 perspectives of
  the 1500-tree Kalimantan world (live smoke/flame, headless Gazebo).
* `modal-firms-k1.gif`: Modal Qwen2.5-7B (text policy,
  `DMB_VISION=text`) on `firms_peat_kalimantan_01` seed 7, 34 actions:
  mission 0.150, spread 0.000, 0/5 found. Honest weak baseline --
  the 7B text model flies but doesn't recon effectively. Eval:
  `evals/firms_peat.py`; run: `runs/modal-firms-k1/`; log in `logs/`.

## Visual fidelity (see visual-prd.md)

Measured against the Commons reference pack (`refs/`). Headless
software-GL frames in `renders/`; GPU-worker frames pending.

| check | bar | measured | verdict |
|---|---|---|---|
| V1 nadir closure | 0.10-0.30 (degraded mosaic) | 0.14-0.21 @1500 trees | PASS (pristine 0.85 needs instancing) |
| V2 canopy hue/sat | 60-140 deg / >0.25 | 65 deg / 0.72 | PASS |
| V3 NN-distance CV | > 0.3 | 0.34 | PASS |
| V4 smoke at ignitions | visible <=100 m | yes (both ignitions) | PASS |
| V5 peat ground | <= (0.45,0.35,0.28) | (0.40,0.33,0.26) | PASS |
| V6 horizon haze | far-field near fog color | treeline fade visible | PASS (visual) |
| V7 no grid artefacts | no row/col period | clustered+jittered placement | PASS (by construction) |

Known gaps: single overstory species (oak; Fuel has no second
broadleaf), no understory layer (both Fuel grasses retired --
plane-based, black under ogre2), no water/roads/burn scars, smoke not
coupled to fire intensity. Full list in `visual-prd.md`.
