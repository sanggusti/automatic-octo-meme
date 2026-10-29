# Specs — Pinned Versions, Endpoints, Budgets

Single source of truth for every concrete choice a coding agent needs. Status
is `verified` (observed in this repo/environment) or `pending` (blocked on an
owner). Change anything here through a reviewed PR that also updates the
affected issue.

## Runtime (verified 2026-10-27)

| Item | Spec |
|---|---|
| Python | 3.10.4 (venv `.venv`, setuptools backend) |
| inspect-ai | 0.3.280 |
| openai client | 3.39.0 (required by inspect-ai OpenAI-compatible provider) |
| pyyaml | 6.0.3 |
| pytest | 9.1.1 |
| Modal client | 1.1.4 |
| Model routing | `openai-api/<service>/<model>` → `<SERVICE>_API_KEY` + `<SERVICE>_BASE_URL` |

## Inference providers

| Item | Spec | Status |
|---|---|---|
| Baseten base URL | `https://inference.baseten.co/v1` | verified (provider docs) |
| Baseten model id | `openai-api/baseten/<slug>` | verified (routing) |
| Baseten slug | TBD at credit time; must support tool calling + vision | **pending (credits)** |
| Modal model id | `openai-api/modal/<name>` | verified (routing) |
| Modal server | `infra/modal/vllm_server.py`: CUDA 12.9 image, vLLM 0.21.0, `Qwen/Qwen2.5-7B-Instruct` on A10G, `--enable-auto-tool-choice --tool-call-parser hermes` | verified 2026-10-27 |
| Modal endpoint | `https://sanggusti--dmb-vllm-openai-compatible-serve.us-east.modal.run` (`/v1` suffix for `MODAL_BASE_URL`) | verified, deployment stopped after verification |
| Modal auth | operator `modal setup` completed 2026-10-27 | working (unsandboxed; sandbox DNS blocks Modal client) |
| Modal results | smoke accuracy 1.0; forest_fire limit-1 composite 0.627 (19 tool calls) | eval logs in `logs/`, registry `verify-modal-*` |

No provider-backed run has succeeded yet. First success criteria live in #1.

## Eval budgets (scaffold defaults)

| Knob | Default | Where |
|---|---|---|
| Agent message cap | 50 (`message_limit`) | `evals/forest_fire.py` |
| Episode step budget | 60 | `MockBridge` |
| Edge heartbeat | every 5 steps | `DMB_EDGE_REPORT_INTERVAL_STEPS` |
| Snapshot budget | 8 per episode | `DMB_EDGE_MAX_SNAPSHOTS_PER_EPISODE` |
| Sample seeds (v0) | `[1, 2, 3]` | per task |
| Victim weights | child 3, human 2, animal 1 | `dmb/scorers/mission.py` |

## Track 1 sim (verified in #2)

| Item | Spec |
|---|---|
| OS image | Ubuntu 22.04 arm64 (`infra/sim/Dockerfile` → `dmb/sim:track1`) |
| Renderer/sim | Gazebo Harmonic (`gz-harmonic` 8.x), headless server |
| Plugin | `ArduPilot/ardupilot_gazebo` @ `80dc9664` |
| ArduPilot | `Copter-4.6.3` (`92b0cd78`); `waf configure --board sitl`, `waf copter` |
| Boot | `infra/sim/entrypoint.sh`: `gz sim -s` + `sim_vehicle.py --no-mavproxy -I0`; SITL TCP 5760 |
| Isolation | 1 container (1 SITL + 1 Gazebo) per episode, random host port |
| Grid mapping | 5 m/cell, east=+x, north=+y from GPS home anchor |

## Track 2 sim (code done in #27; live run owned by #6)

| Item | Spec |
|---|---|
| Engine/sim | Colosseum (`CodexLabsLLC/Colosseum`, AirSim successor) on Unreal |
| Versions | UE 5.6 (main branch), Windows 10; Ubuntu 22.04 Vulkan caveat |
| Workstation | Operator PC, RTX 5070 Ti 16 GB VRAM |
| Client API | msgpack-rpc 127.0.0.1:41451; takeoff/land/goHome/moveToPosition/hover/simGetImages verified in client source |
| Grid mapping | Local NED metres around spawn (east=+x, north=+y), 5 m/cell |
| Isolation | 1 session per sample |

## Drone specs (owned by #3)

`assets/drones/*.yaml`, schema in `docs/assets.md`. Current inventory is
`placeholder` provenance and must not be cited as real capability data.

## Status log

- 2026-10-27: scaffold merged (#10). Modal auth failing — operator action.
  Baseten credits pending — provider runs blocked.
- 2026-10-27: Modal re-login verified; vLLM server deployed, smoke + mission
  evals pass, deployment stopped. Baseten still pending.
- 2026-10-27: Track 1 verified; scripted GUIDED flight + 2-parallel
  isolation pass; forest_fire runs on gazebo-sitl. Pre-arm settling needs
  ~1 min per fresh worker (bridge retries, reports vehicle reason).
- 2026-10-27: Phase A done; difficulty bands + first-find/coverage
  metrics live; greedy 0.78 vs random 0.65 over 100 seeds; 3 human
  baselines recorded (0.30/0.37/0.63).
- 2026-10-28: Phase B done; T0 fire/water/slip dynamics with snapshot
  suite; containment is beat-the-spread; suite 31 green.
- 2026-10-28: Phase C done; native SITL frames + vision tool results,
  edge-VLM baseline (stub-tested), Colosseum bridge (fake-tested) +
  verdict harness (mock-vs-SITL match live); suite 44 green.
- 2026-10-28: Phase D done; L2 recorder + SFT/RLVR export, 224-pair
  teacher set, LoRA finetune on Modal, held-out delta −0.049 (null;
  scan-spam mechanism), dataset + weights on HF; suite 50+ green.
- 2026-10-29: Baseten verified (muse-spark-open-1026, key scoped to that
  slug); smoke 1.0, forest_fire 0.608, pack 0.755 (18/18). #1 closed.
- 2026-10-29: Single-slug scope locked (docs/inference.md, #7); L2
  enriched with pos+detections; mock T2 replay renderer (GIF+PNG)
  built and proven on a fresh Baseten episode.
