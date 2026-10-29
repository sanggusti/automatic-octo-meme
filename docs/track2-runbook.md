# Track 2 Runbook — Colosseum on the GPU Workstation

Runs on the operator PC (RTX 5070 Ti), not the dev machine. Versions pinned
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

def rollout(bridge):
    bridge.act("arm", {})
    bridge.act("takeoff", {"altitude_m": 10})
    bridge.act("goto", {"x": 2, "y": 2})
    bridge.act("land", {})

metas = [dict(s.metadata) for s in build_samples("forest_fire", seeds=[1, 2, 3])]
report = compare_backends(
    MockBridge.from_metadata,
    lambda md: ColosseumBridge.from_metadata(md, host="<pc-ip>"),
    metas, rollout,
)
for entry in report:
    print(entry["seed"], entry["match"], entry["diffs"])
```

All-match is the bar. Mismatches are data: record diffs in issue #6.

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
