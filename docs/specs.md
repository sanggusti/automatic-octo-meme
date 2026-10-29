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

## Track 2 sim (code done in #27; live leg verified 2026-10-29 for #6)

| Item | Spec |
|---|---|
| Engine/sim | Colosseum (`CodexLabsLLC/Colosseum`, AirSim successor) on Unreal; env binary `Blocks.zip` from release `v2.0.0-beta` (2023-02-27) |
| Versions | Source `main` @ `c2703d0ccd15d5e72911461af0d064e671c8a29d` (2025-12-08, UE 5.6-only per README); binary UE 5.1; wire client `v2.0.0-beta` @ `7b9658a1169705ca86b21b3518fac5ba83fbe183` |
| Workstation | This PC: RTX 5060 Ti 16 GB (nvidia-smi; inventory said 5070 Ti), Windows 11 26H2, Python 3.12.10 venv, airsim 1.8.1 (beta client) |
| Client API | msgpack-rpc 127.0.0.1:41451; reset/enableApiControl/armDisarm/takeoff/land/goHome/moveToPosition/hover/simGetVehiclePose/getMultirotorState/simGetImages verified live. Main-branch client cannot parse this binary's MultirotorState — use the beta client |
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
- 2026-10-29: Asset credibility bundle (#3/#17/#18/#19): sourced drone
  specs + enforcement, fire/terrain weather coupling, mobility
  detectability, Fuel pins + manifest, T1/T2 plans; suite 66 green.
- 2026-10-29: #4 done; bands documented, time-of-day axis + edge
  visibility, per-kind containment (tsunami beat-the-wave), efficiency
  idle fix (0.3→0.15), exposure metrics; suite 74 green.
- 2026-10-29: #8 done; record (eval→registry) + table (registry→md/CSV)
  CLIs, 3 runs backfilled, output reproduces posted #7/flywheel tables.
- 2026-10-29: #6 closed; PC verdict re-run 3/3 non-vacuous match
  (recall 0.5/0.5/0.6 both backends, zero diffs). Track 2 API-faithful.
- 2026-10-29: #16 done; T2 Colosseum (record+keyframes) + Gazebo
  (record-path/playback, live) + T3 HTML + registry evidence + L2 audit.
- 2026-10-29: #7 done; 4-column pack matrix (spark 0.755, heuristic
  0.704, random 0.638, qwen-7b 0.535*); scripted coverage beats the 7B LM.
- 2026-10-29: Track 2 live (#6): Blocks binary runs on the PC, hello
  flight green (arm/takeoff/goto/land + native 256x144 frame), verdict
  mock-vs-Colosseum 3/3 match (forest_fire seeds 1-3, recall 0.0=0.0).
