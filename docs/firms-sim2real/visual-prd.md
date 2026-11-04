# Visual PRD: Kalimantan peatland fire world

Reference pack: `refs/ref-{canopy,landscape,fire,burn}.jpg` (Wikimedia
Commons; exact source URLs + licenses to be recorded in
`refs/sources.md`).

## What "close to Kalimantan" means, measurably

| # | Check | Reference | Pass bar |
|---|-------|-----------|----------|
| V1 | Nadir canopy closure | ref-landscape: degraded peatland mosaic, not pristine canopy | 0.10-0.30 green in nadir center crop (degraded mosaic; pristine 0.85 needs instancing -- open) |
| V2 | Canopy color | ref-canopy: deep saturated green, sunlit lime crowns | median hue 60-140 deg, saturation > 0.25 |
| V3 | Stand irregularity | ref-canopy: no rows, gaps, clumps | CV of nearest-neighbour distance > 0.3 |
| V4 | Smoke columns at ignitions | ref-fire: white-grey columns rising through canopy | column visible within 100 m of each ignition in oblique cam |
| V5 | Ground peat read | drained peat brown (unburnt); charred black is burn-scar work | rendered ground <= (0.45, 0.35, 0.28), no bright soil |
| V6 | Horizon haze | ref-canopy/ref-burn: distance washes to grey-white | treeline fade visible (visual) |
| V7 | No grid artefacts | ref-canopy | no detectable row/column period in nadir FFT |

V1-V3, V5, V7 are checkable headless from `cam_nadir` + placements.json;
V4, V6 need the oblique/low frames. Software-GL frames in `renders/`
are the verified baseline; GPU-worker frames will differ in
shadows/AA, not layout. Nadir cam sits 45 m off the ignition: columns
rise 100 m+ and a cam directly overhead whites out inside the smoke.

Measured (kalimantan_01 seed 7, 1500 oaks): V1 0.14-0.21 PASS, V2
hue 65 / sat 0.72 PASS, V3 CV 0.34 PASS, V4 PASS, V5 (0.40,0.33,0.26)
PASS, V6 PASS, V7 PASS by construction.

## Asset provenance (nothing invented)

* Tree meshes: `OpenRobotics/Oak tree` (verified broadleaf; peat
  overstory is oak-only -- pine is botanically wrong for peat swamp,
  the `facugu123/Tree` apple renders leafless-white, and Fuel has no
  second broadleaf; see manifest retirement notes).
* NO understory: both pinned grass models are plane-based and render
  black under ogre2 (`Grass Plane` is also a 500 m sprawl, not a tuft).
* Smoke: `caguero/smoke_generator` numerics + texture, rehosted in SDF
  `<particle_emitter>` elements (Harmonic ignores model `<plugin>`
  blocks -- verified against the gz-sim8 source); haze banks are
  `OpenRobotics/Fog Emitter Dense` numerics, same rehosting.
* Flames: `flame_column`, smoke numerics with orange `<diffuse>` (the
  documented adaptation).
* Pins (URL + sha256 + license) in `assets/manifest.yaml`; fetcher
  `assets/vegetation/fetch_models.py` is the single source of truth.

## Known gaps vs the references

* Single overstory species (oak). Fuel's tree catalog is oak/pine plus
  broken finds; a second broadleaf needs off-Fuel sourcing (open work).
* No grass/understory layer (both Fuel grasses retired; needs a
  mesh-based tuft asset).
* No river/water body yet (ref-canopy's river, ref-landscape's black
  canals). Peat hydrology is out of scope for this pass; ground reads as
  drained peat.
* No emergent trees (ref-canopy's 50 m emergents above the canopy deck).
  Per-instance scale (0.8-1.3x) gives two canopy layers at best.
* No burn scar / snags yet (ref-landscape, ref-fire foreground). The
  spread model burns cells but the world is a t=0 snapshot.
* Smoke is a static emitter config, not coupled to fire intensity.
