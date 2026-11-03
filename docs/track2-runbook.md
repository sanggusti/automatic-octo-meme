# Track 2 Runbook — Colosseum on the GPU Workstation

Runs on the operator PC (RTX 5060 Ti 16 GB, corrected 2026-10-29 from
the 5070 Ti inventory guess), not the dev machine. Versions pinned
from the Colosseum README (inspected 2026-10-28): **main branch = UE 5.6**,
Windows 10 supported; Ubuntu 22.04 has a Vulkan caveat (Docker advised).

## 1. Build (on the PC, first time)

Follow the official guides (steps not duplicated here — they change):
- Binaries (fastest): `https://codexlabsllc.github.io/Colosseum/use_precompiled/`
- Build on Windows: `https://codexlabsllc.github.io/Colosseum/build_windows/`
- Settings reference: `https://codexlabsllc.github.io/Colosseum/settings/`
- Image APIs: `https://codexlabsllc.github.io/Colosseum/image_apis/`
- Core APIs: `https://codexlabsllc.github.io/Colosseum/apis/`

Record the Colosseum commit + UE version in `docs/specs.md` once built
(done 2026-10-29 — see `docs/specs.md` Track 2 table).

As-run on the workstation (2026-10-29): binaries route. The only release
with precompiled env binaries is `v2.0.0-beta` (2023-02-27): `Blocks.zip`
(320 MB, UE 5.1) from
`https://github.com/CodexLabsLLC/Colosseum/releases/download/v2.0.0-beta/Blocks.zip`.
Newer releases (v2.1.0–v2.3.0) are source-only. Source reference checkout:
`main` @ `c2703d0cc...` (2025-12-08, UE 5.6-only per README). The
wire-compatible client is the `v2.0.0-beta` tag @ `7b9658a11...`: the
main-branch client cannot parse this binary's `MultirotorState`
(`ValueError: Length of encoded data does not match number of
attributes`), so install the beta `PythonClient` (§2) for live runs.

## 2. Python client (on the PC, or any machine reaching it)

Install the client from the Colosseum repo's `PythonClient/` directory
(msgpack-rpc protocol, default port **41451**):

```bash
pip install msgpack-rpc-python numpy
pip install -e <colosseum-checkout>/PythonClient
python -c "import airsim; c = airsim.MultirotorClient(); c.confirmConnection(); print('linked')"
```

As-run on the workstation (Python 3.12.10, PowerShell, from repo root):

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]" msgpack-rpc-python numpy
.\.venv\Scripts\python -m pip install backports.ssl-match-hostname setuptools wheel
.\.venv\Scripts\python -m pip install --no-build-isolation --no-deps -e <beta-checkout>\PythonClient
.\.venv\Scripts\python -c "import airsim; c = airsim.MultirotorClient(); c.confirmConnection(); print('linked')"
```

Notes: stock `pip install -e .../PythonClient` fails because `setup.py`
imports `airsim` at build time (needs numpy + msgpackrpc importable in
the build env), hence `--no-build-isolation` (which needs `setuptools`
in the venv — 3.12 venvs omit it). `backports.ssl-match-hostname` is
needed on Python ≥ 3.10 for `tornado` 4.5 (a `msgpack-rpc-python` dep).
Install the client from the `v2.0.0-beta` checkout (§1), not main.

## 3. Hello flight (verifies our bridge contract)

```python
from dmb.sim.colosseum_bridge import ColosseumBridge
from dmb.scenarios import build_samples
md = dict(build_samples("forest_fire", seeds=[1])[0].metadata)
bridge = ColosseumBridge(host="<pc-ip>", vehicle_name="")
try:
    bridge.reset(md)
    print(bridge.act("arm", {}).text)
    print(bridge.act("takeoff", {"altitude_m": 5}).text)
    print(bridge.act("goto", {"x": 2, "y": 2}).text)
    print(bridge.act("land", {}).text)
    png = bridge.capture_frame("hello")
    print("frame bytes:", len(png) if png else None)
finally:
    bridge.close()
```

Expected: armed → takeoff → arrived (2, 2) → landed, frame bytes > 0.

## 4. Verdict reproduction (fidelity bar)

Same rollout, two backends, compared verdicts (recall within 0.15, same
safety outcome, same found-any):

```python
from dmb.scenarios import build_samples
from dmb.sim.bridge import MockBridge
from dmb.sim.colosseum_bridge import ColosseumBridge
from dmb.verdicts import compare_backends

def rollout(bridge, meta):
    from dmb.perception.edge import FrameBudget, StubEdgePerception, TriggerConfig

    edge = StubEdgePerception(bridge, TriggerConfig(), FrameBudget(8))

    def do(action, params=None):
        obs = bridge.act(action, params or {})
        edge.on_step(bridge.get_state()["steps"])
        return obs

    do("arm")
    do("takeoff", {"altitude_m": 10})
    for victim in meta["victim_placements"][:2]:
        do("goto", {"x": victim["x"], "y": victim["y"]})
    do("land")

metas = [dict(s.metadata) for s in build_samples("forest_fire", seeds=[1, 2, 3])]
report = compare_backends(
    MockBridge.from_metadata,
    lambda md: ColosseumBridge.from_metadata(md, host="<pc-ip>"),
    metas, rollout,
)
for entry in report:
    print(entry["seed"], entry["match"], entry["diffs"])
    for label, scores in entry["scores"].items():
        print("  ", label, {k: round(scores[k], 3) for k in ("rescue_recall", "safety", "found_any")})
```

All-match is the bar AND the rollout must find victims on mock
(recall > 0): a 0.0=0.0 match is vacuous and does not clear the bar
(2026-10-29 run matched 0.0=0.0 — re-run required with this rollout).
Mismatches are data: record diffs in issue #6.

## 5. Notes

- One vehicle per episode; multi-vehicle sessions are later work.
- `simGetImages` scene frames are the native vision source on this track.
- `startRecording`/`stopRecording` wire watcher T2 capture (issue #16).
- Stuck builds: Colosseum Discord (linked from their README).

## 6. Workstation start/stop/update (as-run 2026-10-29)

Paths below are the ones used on the PC; adjust the drive if yours differs.

**Prerequisite: `settings.json`.** The beta binary needs an explicit
Multirotor config, otherwise it spawns the (missing from the pak) SUV car
asset and the RPC server never starts. Write to
`%USERPROFILE%\Documents\AirSim\settings.json`:

```json
{
  "SeeDocsAt": "https://codexlabsllc.github.io/Colosseum/settings/",
  "SettingsVersion": 1.2,
  "SimMode": "Multirotor",
  "ApiServerPort": 41451,
  "Vehicles": {
    "SimpleFlight": {
      "VehicleType": "SimpleFlight",
      "X": 0, "Y": 0, "Z": 0
    }
  }
}
```

**Start** (PowerShell; the `Blocks.exe` bootstrapper exits and the game
continues detached as `Blocks-Win64-DebugGame.exe`):

```powershell
& 'D:\programming\Colosseum-env\Blocks\Blocks.exe' -windowed -ResX=1280 -ResY=720
Get-NetTCPConnection -LocalPort 41451  # ready when this listens
```

First boot takes minutes (shader compile); later boots ~1 min. Game log:
`<Blocks>\Blocks\Saved\Logs\Blocks.log`.

**Stop:**

```powershell
Get-Process Blocks-Win64-DebugGame -ErrorAction SilentlyContinue | Stop-Process -Force
```

**Update.** Binary: re-download `Blocks.zip` (§1) and re-extract over
`D:\programming\Colosseum-env\Blocks`. Source checkouts:
`git -C <checkout> pull --ff-only` (shallow clones may need a fresh
`git clone --depth 1` instead). Then re-run the client install line from
§2 and the §3 hello flight to confirm the wire still matches.

## 7. Forest-fire env (issue #50, operator legs)

New-env walkthrough with all gotchas: `docs/custom-env-guide.md`
(toolchain, map generation, packaging, flight rules, troubleshooting
matrix with screenshots). Whiteout bisect record:
`docs/forest-fire-whiteout.md`.

Code-complete in-repo; live legs need the #46 toolchain (UE 5.6 +
Colosseum source build). The PC's UE 5.8.4
(`D:\Epic Games\UE_5.8`, verified 2026-11-02) cannot build Colosseum —
install UE 5.6 alongside, do not upgrade the env to 5.8.

1. Build the map per `unreal/forest_fire/README.md` (GIS terrain →
   foliage CSV → fire-schedule particles → before/burning variants).
2. Package, start, and run the §3 hello flight against the burning map
   (expect identical contract output; record frame bytes + a keyframe).
3. Run the §4 verdict rollout on `forest_fire_peat` seeds 1–3 and post
   the match table to #50.
4. Capture before-variant reference keyframes (one per visual-target
   phase in `unreal/forest_fire/VISUAL_TARGET.md`) into the issue.
5. Update `docs/specs.md` (env binary + pins) in the closing PR.

## 8. Peatforest env (issues #64/#65/#66, as-run 2026-11-03)

Real-data peatland maps (`PeatBefore` lush / `PeatBurning` charred +
fire). Full record: `docs/peatforest-report.md` (tile reasoning, pins,
seeds, counts, frame time, spawn/bounds, deviations, bug bisects).

1. Prep (pinned data in `assets/manifest.yaml`, `gis:`):
   `prep_tile.py --out data/peatforest/ue_inputs`,
   `gen_terrain.py --seed 7 --out data/peatforest/ue_gen`,
   `gen_groves.py --gen ... --out ...`, stage to
   `<project>/inputs/peatforest/`.
2. Build each map (`DMB_MAPS=before|burning`):
   `UnrealEditor-cmd.exe ForestFire.uproject -run=pythonscript
   -script=unreal/peatforest/tools/ue_build_peat.py -unattended
   -nopause -nosplash`; verdict lands in
   `<project>/Saved/PeatBuild_OK.txt`. Under a shell sandbox these
   runs need one-shot escalation (DDC + project writes are blocked).
3. Package: RunUAT `BuildCookRun ... -cook -build -stage -pak
   -archive -archivedirectory=ForestFire-Pkg` (stop any running game
   first — it locks the `.ucas` stage copy).
4. Fly: `ForestFire.exe PeatBurning -RenderOffScreen -ResX=1280
   -ResY=720`, MAIN PythonClient, RPC 41451. Spawn = tile SW corner
   (NED origin); bounds x,y in `[0,2000]` m; 5 m/cell grid.
5. Eval: `runs/peat_eval.py mock` (no game) then `both` (game up);
   expect mock/bridge match, recall ~0.5, safety 1.0.
6. Hi-fi v1 (structure landed, fidelity open — see report):
   `gen_textures.py` (leaf/flame/smoke alpha), `gen_groves.py` v2
   (4 variants + charred), stage `tex/` + `assets_raw/` (PBR pins)
   beside `ue_gen`, `DMB_MAPS=both` build. Materials need
   `used_with_nanite` (no `b_` prefix) or Nanite meshes render
   default-gray. Never connect `MaterialExpressionVertexColor`
   (editor access-violation crash, 3x).
7. Gotchas that cost a day: (a) the shell sandbox blocks LOOPBACK
   TCP — in-sandbox RPC clients die with WinError 10013 masked as
   "port never opened" while the game LISTENs fine. Run every
   survey/RPC/game command escalated. (b) Kill games BY NAME
   (bootstrap + inner exe): a stale inner holds 41451 and the next
   boot bind-fails into an invisible headless modal that blocks the
   game thread. (c) AirSim `LogMessage` is screen-only — RPC
   startup failures never reach the packaged log.
