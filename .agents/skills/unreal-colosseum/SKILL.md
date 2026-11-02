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

- Materials: `connect_material_property` needs EXPLICIT pin names
  (`'RGB'` for Color3Vector, `'R'` for scalar) and returns `False` for
  bad pins — assert the return. `""` wires output `""`, which probes
  show as connected but renders black. Always `save_asset` after edits.
- Fog: 5.6 renamed the tint to `fog_inscattering_luminance`
  (`fog_inscattering_color` is deprecated and missing from Python).
- Lights: movable DirectionalLight + movable SkyLight, no lightmap bake
  (static lights + no bake = "lighting needs to be rebuilt" + black).
- No `line_trace_single` under `-cmd` (returns None, no physics scene):
  bake analytic heights into the generator sidecar instead.
- Collision: terrain complex-as-simple; trees collide; fire/smoke/glow
  markers must be `NO_COLLISION` or the drone wedges on them.
- Grid mapping: grid (x=east, y=north) -> UE cm (X=y*500, Y=x*500);
  PlayerStart at the grid CORNER (trees sit at cell centers).

## Verify on packaged builds, not `-game`

The cook is the only place material shaders actually compile, and `-game`
rendering/capture has known quirks. The ladder is: build -> package ->
run packaged -> fly -> capture -> LOOK at every frame. Clean logs with
broken images are the norm for: inverted winding, unconnected BaseColor,
bad exposure, unlit scenes.

## RPC / flight rules

- One vehicle per episode; RPC port 41451; settings.json needs a
  Multirotor entry or the server never starts.
- `moveToPositionAsync().join()` waits FOREVER when wedged (verified:
  30+ min against a decorative cube). Always run flights with a
  watchdog timeout, and prefer altitudes that clear map clutter.
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

## Surveyed sources

- Colosseum docs: `build_windows`, `unreal_custenv`, `unreal_proj`,
  `settings`, `image_apis`, `apis` (codexlabsllc.github.io/Colosseum).
- Fairhaven AGENTS.md (UE5 generated-world project: verify-by-screenshot
  ladder, pin-name gotcha, two-sided black foliage, exposure notes).
- vitez.me/scripting-unreal (`connect_material_property` pin names).
- fenggezaici/dcc-python-skills, `unreal-engine-5-3-python-scripting`
  chapters (actor/material/texture scripting patterns).
