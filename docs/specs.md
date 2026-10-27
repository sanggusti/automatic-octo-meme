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

## Track 1 sim (target, owned by #2)

| Item | Spec |
|---|---|
| OS image | Ubuntu 22.04 (`infra/sim/Dockerfile`) |
| Renderer/sim | Gazebo Harmonic (`gz-harmonic`) |
| Plugin | `ArduPilot/ardupilot_gazebo` (main; pin a commit in #2) |
| ArduPilot | source ref TBD in #2; `waf configure --board sitl`, `waf copter` |
| Isolation | 1 SITL instance per worker via compose replicas |

## Track 2 sim (target, owned by #6)

| Item | Spec |
|---|---|
| Engine/sim | Colosseum (`CodexLabsLLC/Colosseum`, AirSim successor) on Unreal |
| Workstation | Operator PC, RTX 5070 Ti 16 GB VRAM |
| Isolation | 1 session per sample |

## Drone specs (owned by #3)

`assets/drones/*.yaml`, schema in `docs/assets.md`. Current inventory is
`placeholder` provenance and must not be cited as real capability data.

## Status log

- 2026-10-27: scaffold merged (#10). Modal auth failing — operator action.
  Baseten credits pending — provider runs blocked.
- 2026-10-27: Modal re-login verified; vLLM server deployed, smoke + mission
  evals pass, deployment stopped. Baseten still pending.
