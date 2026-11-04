# UE sim takeaways (ForestFire / Colosseum, UE 5.6)

Status 2026-11-04, REVIVED post-reboot: the v3 load hang was bisected
to Lumen (DynamicGlobalIlluminationMethod + Reflections) on 10M-tri
maps -- loads with Lumen off, hangs with it on. Fixes baked in:
`[ConsoleVariables]` Lumen-off + `GameDefaultMap=/Game/Peat/PeatBefore`
in DefaultEngine.ini (plain launches boot straight into Peat), plus
single-session map builds (split sessions rot the first map's ribbon
refs) and clean recooks after merged-mesh changes (a 10x-shrunk
charred mesh confused the incremental cook into a load hang).
Original shelve note kept below for the record; the old-map whiteout
(symptom 1) is still open but no longer on any critical path.

Status 2026-11-04: the packaged-Unreal path is SHELVED after three
sessions of recurring render/load failures with near-zero
observability. This note records what worked, what kept breaking,
and what a revival (or replacement) needs. Details live in
`docs/peatforest-report.md`, `docs/track2-runbook.md` §8,
`docs/custom-env-guide.md`, `docs/forest-fire-whiteout.md`.

## What genuinely worked (keep all of it)

- Real-data pipeline: Copernicus DEM + Sentinel-2 + WorldCover +
  FIRMS tile C, pinned in `assets/manifest.yaml`, reproducible at
  seed 7 (`unreal/peatforest/tools/`).
- Generators: 500x500 terrain, 16k-tree groves (6 variants),
  canals, FIRMS fronts, hidden-path network. Full suite green
  (145 passed, incl. 11 hi-fi contract tests).
- Flight stack: Colosseum RPC patterns that actually hold —
  takeoff/climb-first legs, `teleport_hold` + `settle_level`,
  fire-poll `moveToPositionAsync`, `simSetCameraPose` pitch control.
- Collision truth (bisected live, still valid): the shell BLOCKS;
  rest center = surface + 1.31 m; `simGetCollisionInfo` resets
  `has_collided` on EVERY read (use contact `time_stamp` + stall).
- Packaging mechanics: editor-cmd build (absolute `-script=` path),
  `DMB_MAPS=both` verdict file, RunUAT BuildCookRun to
  `ForestFire-Pkg`, bootstrap + inner exe launch.

## The failure ladder (three symptoms, one theme)

1. forest_fire map whiteout (from package 9): Scene all-white,
   seg/depth fine. Audits, recooks, material reverts, fresh shader
   compiles — all clean. NEVER root-caused. Open leads (driver
   DXCache purge, package-8 rebuild comparison) were never
   conclusive; work pivoted to peatland instead.
2. v3 peat "whiteout": NOT a rendering failure. The packaged game
   silently fell back to `GameDefaultMap` (`ForestFire_Burning` —
   the ORIGINAL whiteout map from (1)) because `PeatBefore`
   would not load: CLI map arg ignored, `simLoadLevel` returned
   False at runtime, actor census showed 301 old-map grid actors.
   Symptom 2 IS symptom 1 resurfacing through the fallback.
3. `PeatBefore` unloadable in the cooked game: the editor loads
   the same umap fine (18 actors), the cook succeeds, the pak
   contains every asset (ucas 268 MB, IoStore list complete) —
   yet the shipped game cannot open the map. ROOT CAUSE UNKNOWN.
   Unproven candidates: incremental-cook staleness after the
   delete-first umap recreation, a cooked-map/dependency edge
   case, bulk-data load failure. Nobody got a log out of the
   inner exe to check (see below).

## Why everything took 10x longer (observability gaps)

- The shipping inner exe (`ForestFire-Win64-Shipping.exe` —
  NOTE the name; kill patterns matching only `ForestFire` miss
  it) wrote NO log file anywhere while serving RPC normally.
- AirSim `LogMessage` is screen-only: RPC-side startup failures
  never reach any packaged log.
- RunUAT/cook logs are console-only; a truncated pipe (my v3
  mistake: kept 6 lines) destroys the only cook record. Persist
  full BuildCookRun output to a file, always.
- `simListSceneObjects` matches internal names
  (`StaticMeshActor_N`), never labels (`PeatTerrain` returns NaN
  poses); the actor census that cracked symptom 2 should be the
  FIRST step of every future whiteout drill, not the last.
- The game NEVER errors visibly on map fallback: it boots the
  default map and serves RPC as if all is well. Every flight
  script should assert the loaded map (actor census / known
  object pose) before capturing a single frame.

## Minimum bar to revive the UE path

1. Boot-assert the map in every run (census + a `simGetObjectPose`
   on a Peat actor); fail loudly on fallback.
2. Debug in PIE/editor, never in packaged, until maps load;
   clean-cook (`-clean`) with full saved logs before any bisect
   conclusion about content vs machine state.
3. Resolve symptom 1 first (old-map whiteout) with GPU-side
   tooling (RenderDoc/NSight frame capture) — it is the fallback
   target, so it poisons every later failure.
4. Set `GameDefaultMap` to a Peat map (or an empty assert map)
   so a fallback can never masquerade as a new bug.
5. Revisit the 369 MB merged canopy: split per-variant meshes,
   confirm Nanite bulk loads, keep an eye on import/cook limits.

## If UE stays shelved

The eval contract (local-NED grid, 5 m/cell, frames + depth +
collision + deterministic seeds) does not require Unreal. The
generators already emit plain OBJs + JSON sidecars; a lighter
backend (Godot, Isaac Sim, or a headless Blender/Mitsuba
renderer + analytic collision from `heights.json`, which the
touch verdict already validated) could consume them directly.

## Last green state

Branch `feat/peatforest-env` @ `57ed1ee` (pushed): v2.7 package
surveys green on both maps (23.7 m legs, white 0.0, touch
-0.5 vs -0.47 expect, contact events), 145 tests green. v3
content (16k trees, floor tint, constant path material) is
generated and editor-verified but NEVER flew — no v3 package
ever rendered. Promo GIFs were NOT recorded (blocked on v3).
