# UE Forest-Fire Environment (#50)

Literal peatland forest on the PC: placed trees, terrain elevation, fire
fronts. Before-disaster reference + burning variant of the same map;
sims run on it. Follows the ESARBench precedent (UE5 + AirSim-class
flight over GIS-mapped terrain) and the repo tier rule: T2 renders T0
semantics, never redefines them (docs/physics-assets.md).

## Toolchain (issue #46, operator-owned)

- **UE 5.6** via the Epic Games Launcher. The PC has UE 5.8.4 at
  `D:\Epic Games\UE_5.8`, which Colosseum cannot use (no 5.8 branch;
  main is 5.6-only, latest branch is `ue-5.7`). Install 5.6 alongside.
- Colosseum source build per `https://codexlabsllc.github.io/Colosseum/build_windows/`
  at the pinned commit in `manifest.yaml`.
- Copy `settings.json` to `%USERPROFILE%\Documents\AirSim\settings.json`
  (Multirotor, port 41451 — same contract as docs/track2-runbook.md §6).

## Build the map (operator, in UE 5.6)

1. **GIS terrain.** Download the DEM + peat-extent tiles in
   `manifest.yaml` (Central Kalimantan peatland). Import the DEM as a
   UE Landscape; flatten to peatland grade (near-flat, ~5 m relief)
   and carve straight drainage canals along the peat-block edge. Grid
   mapping stays 5 m/cell (docs/specs.md), so the 10x10 map is a
   50x50 m tile: build it as one tile of a larger landscape.
2. **Foliage.** Run `export_foliage.py` for `forest_fire_peat`, import
   `foliage.csv` as a DataTable, and scatter instanced meshes per row
   (`species` -> chosen art-pack mesh, `x_m`/`y_m` -> position).
   Re-running with the same seed reproduces the layout exactly.
3. **Fire timeline.** Run `export_fire_schedule.py` for the scenario +
   weather under test. Burning variant: Niagara flame + smoke systems
   keyed to the per-step cell sets, fog density keyed to `haze`
   (see `VISUAL_TARGET.md` phases). Before variant: same level with
   the timeline parked at step 0 and emitters disabled.
4. **Spawn.** Player start at the tile corner matching grid (0, 0);
   verify the Colosseum spawn pose, then package the env.

## Run evals on it

Same bridge contract as Blocks (docs/track2-runbook.md §3-§4):
hello flight first, then the verdict rollout against mock. Grid maps
to local NED metres around spawn (east = +x, north = +y).

## #50 acceptance status (this PR)

- [x] T0 peat/smolder/haze model + `forest_fire_peat` scenario + eval
- [x] T2 export path (foliage CSV + fire-schedule JSON) with tests
- [x] Visual target grounded in October 2026 peat-fire reporting
- [x] Asset pins, manifest-style (verified entries pinned; art + GIS
      tiles explicitly pending-operator, no invented URLs)
- [ ] Map built + packaged on the PC (needs #46 toolchain)
- [ ] Before-variant reference keyframes captured
- [ ] Drone spawns, hello flight green, eval end-to-end on burning map
- [ ] Env + pins recorded in runbook/specs (this README is the draft;
      specs update lands with the live verification)

Live legs stay on #50 after merge — see the PR body.
