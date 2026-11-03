---
name: unreal-colosseum
description: >
  Headless Unreal Engine + Colosseum workflows on the DMB workstation:
  source builds, custom drone-env projects, Python map generation, and
  packaged verification. Read this before touching UE installs, the
  Colosseum checkouts, unreal/forest_fire tooling, or anything that
  launches the editor, UBT, RunUAT, or a packaged env. Distilled from
  verified runs (issues #45/#46/#50); for generic UE Python patterns
  also see the surveyed sources at the bottom.
---

# Unreal + Colosseum (DMB workstation)

## Environment facts

- Engines: UE 5.6.1 at `D:\Epic Games\UE_5.6` (Colosseum work), UE 5.8.4
  alongside (Colosseum has no 5.8 branch; never build flight against it).
- Toolchain: VS2022 + NativeDesktop + Win10 SDK + cmake. AirLib has no
  pinned SDK, so the newest installed SDK is used.
- Checkouts: `D:\programming\Colosseum` (pinned source, main),
  `D:\programming\Colosseum-beta` (pinned beta client), envs under
  `D:\programming\Colosseum-env\`.
- `LauncherInstalled.dat` may not list the engines; UnrealVersionSelector
  then silently does nothing. Bypass it: call UBT/RunUAT by absolute path.

## Headless commands (all verified)

```powershell
# C++ libs (from a VS2022 x64 prompt):  build.cmd            (all configs)
# Project files (direct UBT, never the selector):
UnrealBuildTool.exe -projectfiles -project='<X>.uproject' -game -progress
# Editor target:  UnrealBuildTool.exe <X>Editor Win64 Development -project='<X>.uproject'
# Maps (PythonScriptPlugin must be enabled in the .uproject):
UnrealEditor-cmd.exe <X>.uproject -run=pythonscript -script='<s>.py' -unattended -nopause -nosplash
# Package:  RunUAT.bat BuildCookRun -project='<X>.uproject' -platform=Win64
#   -clientconfig=Development -cook -build -stage -pak -archive
#   -archivedirectory='<out>' -unattended -utf8output
```

Prefer `Start-Process` over `&` for engine binaries (the call operator
flakes with "a device which does not exist" in sandboxed shells), and
never pipe UBT output through `Select-Object -First N` (it kills UBT).

## Custom env recipe (Colosseum `unreal_custenv` + verified fixes)

1. C++ project with a game module depending on `AirSim`; copy the built
   `Unreal/Plugins` tree into it; `.uproject` enables the `AirSim` plugin
   (our checkout names it AirSim, not Colosseum).
2. `Config/DefaultGame.ini` must cook the maps plus `/AirSim/AirSimAssets`
   and `/AirSim/HUDAssets`, or the package misses plugin content.
3. Set the `.uproject` EngineAssociation to an INSTALLED engine; generate
   project files with UBT directly; build the Editor target.
4. Each map needs: PlayerStart on clear ground, WorldSettings GameMode
   override = `/Script/AirSim.AirSimGameMode` (without it there is no RPC
   server and the game idles on GameModeBase).
5. Verify every map by RELOADING it from disk and asserting actor counts +
   GameMode. Never build two maps with `new_level` in one `-cmd` session:
   the first map can silently save empty.

## Python map generation (patterns that survived contact)

- Materials: on constant expressions only `""` (first output) and `"R"`
  are valid pins; `"RGB"`/`"RGBA"` return `False` (assert every connect).
  No RGB composite exists on constants, so feed colors via 4x4 PNG
  swatches + TextureSample `"RGB"` (probed + vitez pattern),
  emissive-mirrored for a readable unlit placeholder look. Always
  delete-recreate materials on rebuild; always `save_asset` after edits.
- Textures: delete-recreate on reimport too (`replace_existing` alone
  leaves stale bulk data). The stdlib PNG writer's bytes render R/B
  swapped in-engine (PIL-correct file, blue flames live), so it
  pre-swaps to BGR order; pinned by `tests/test_terrain_gen.py`.
- Fog: 5.6 renamed the tint to `fog_inscattering_luminance`
  (`fog_inscattering_color` is deprecated and missing from Python).
- Lights: movable DirectionalLight + movable SkyLight, no lightmap bake
  (static lights + no bake = "lighting needs to be rebuilt" + black).
  Sun intensity 10, NEVER physical 75k lux: 75k whites every Scene
  capture to pure-255 on all maps (bisected B1/B2; skylight
  real_time_capture innocent, DXCache purge + clean recook no help).
  Scene brightness is emissive/fog-driven; true daylight needs a
  PostProcessVolume + exposure tuning (open follow-up).
- No `line_trace_single` under `-cmd` (returns None, no physics scene):
  bake analytic heights into the generator sidecar instead.
- Collision: terrain complex-as-simple; trees collide; fire/smoke/glow
  markers must be `NO_COLLISION` or the drone wedges on them.
- Grid mapping: grid (x=east, y=north) -> UE cm (X=y*500, Y=x*500);
  PlayerStart at the grid CORNER (trees sit at cell centers).
  Spawn-adjacent trees crowd the default camera (brown mass at frame
  edge is the nearest trunk, not a bug); check framing on the ground
  capture before trusting angles.

## Verify on packaged builds, not `-game`

The cook is the only place material shaders actually compile, and `-game`
rendering/capture has known quirks. The ladder is: build -> package ->
run packaged -> fly -> capture -> LOOK at every frame. Clean logs with
broken images are the norm for: inverted winding, unconnected BaseColor,
bad exposure, unlit scenes.
Exposure dead ends: NO exposure API exists in either PythonClient, and
float Scene captures return zeros (unsupported) — fix the lights, don't
chase those. Incremental cooks take ~20s; delete `Saved/Cooked` +
`Saved/StagedBuilds` for a clean recook (~1min).

## RPC / flight rules

- One vehicle per episode; RPC port 41451; settings.json needs a
  Multirotor entry or the server never starts.
- Never `.join()` a `moveToPositionAsync`: the move can be silently
  ignored and the join hangs forever even at clear altitude (verified
  twice, not just when wedged). Fire-and-poll the pose with a timeout,
  then `hoverAsync().join()` to cancel before the next leg.
  `rotateToYawAsync().join()` and `takeoff/landAsync().join()` are safe.
- Custom main-branch builds need the MAIN PythonClient
  (`D:\programming\Colosseum\PythonClient`); the beta client connects
  but cannot parse their poses. The beta binary needs the beta client.
- Never `simSetCameraPose` during verification: poses persist across
  `reset()` and poison later captures (including identical-byte
  "placeholder" frames). Fly the drone for angles; capture the default
  camera. If poses were touched, restart the game before trusting frames.
- Kill orphaned `python.exe` after a timeout kill (the watchdog kills
  the wrapper, the RPC client survives and holds no lock, but confuses
  the next run).

## Recording

Progress lives on the tracking issues: post versions, commands, and
evidence tables per step. The user compiles progress reports from them.
Promote key frames to `docs/img/` + a short evidence doc per env
(`runs/` is git-ignored); the full new-env walkthrough with gotchas
is `docs/custom-env-guide.md`.

## Surveyed sources

- Colosseum docs: `build_windows`, `unreal_custenv`, `unreal_proj`,
  `settings`, `image_apis`, `apis` (codexlabsllc.github.io/Colosseum).
- Fairhaven AGENTS.md (UE5 generated-world project: verify-by-screenshot
  ladder, pin-name gotcha, two-sided black foliage, exposure notes).
- vitez.me/scripting-unreal (`connect_material_property` pin names).
- fenggezaici/dcc-python-skills, `unreal-engine-5-3-python-scripting`
  chapters (actor/material/texture scripting patterns).
