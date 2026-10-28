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

Record the Colosseum commit + UE version in `docs/specs.md` once built.

## 2. Python client (on the PC, or any machine reaching it)

Install the client from the Colosseum repo's `PythonClient/` directory
(msgpack-rpc protocol, default port **41451**):

```bash
pip install msgpack-rpc-python numpy
pip install -e <colosseum-checkout>/PythonClient
python -c "import airsim; c = airsim.MultirotorClient(); c.confirmConnection(); print('linked')"
```

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
    lambda md: ColosseumBridge(host="<pc-ip>").from_metadata(md),
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
