# Compute Split — Where Each Workload Runs

## Hardware inventory (operator-provided)

- **Dev machine** (this repo): Apple Silicon Mac, no discrete GPU. Runs the
  harness, mock evals, unit tests, docs, and issue/PR workflow.
- **GPU workstation** (operator PC): RTX 5070 Ti, 16 GB VRAM. Target for the
  Unreal/Colosseum fidelity track.
- **Inference providers**: Baseten (paid hosted models), Modal (custom
  vLLM-served models). All LM inference is offloaded; nothing large runs
  locally.
- **Edge devices** (deployment concept): resource-scarce onboard computers
  running light vision models; see [edge-perception](edge-perception.md).

## Placement decision

| Workload | Placement | Rationale |
|---|---|---|
| inspect-ai harness, registry, analysis | Dev machine | Pure Python, trivial footprint |
| Mock-backend evals + unit tests | Dev machine | Zero external deps, instant |
| Gazebo + ArduPilot SITL (Track 1) | Dev machine / Linux container | Lightweight enough; also runs in CI containers |
| Colosseum/Unreal (Track 2) | GPU workstation | Needs discrete GPU + large build; dev machine cannot do it |
| Paid LM inference | Baseten | No local GPUs; OpenAI-compatible endpoint |
| Custom-model inference | Modal vLLM server | Pay-per-use GPUs; OpenAI-compatible endpoint |
| Perception in deployment | Edge device | Resource-scarce grounding; LM must not need raw frames |

## Trade-off analysis

**Why the LM never runs locally.** The dev machine has no CUDA device and the
workstation's 16 GB VRAM is reserved for rendering + physics. Both providers
expose the same OpenAI-compatible interface, so the harness carries no
per-provider code; swapping models is a model-id change, and cost/latency
differences show up in tracked metrics rather than architecture.

**Why two sim tracks.** Gazebo+SITL gives a real ArduPilot action surface
cheaply and headlessly — the fastest route to meaningful navigation evals.
Unreal/Colosseum gives photorealistic perception and GIS-scale terrain at the
cost of a heavyweight build and a GPU-bound, single-workstation bottleneck.
The `SimBridge` interface keeps scenario/task code identical across both, so
Track 1 results stay valid when Track 2 comes online.

**Why edge-first perception.** Streaming every frame to a hosted LM is
unaffordable (tokens, latency) and unrealistic (a real drone loses link).
The benchmark therefore scores the LM on navigation/orchestration decisions
over compact edge reports plus a small snapshot budget — the scarcity is part
of the test. Consequence: perception quality is factored out of LM scores by
construction; a separate edge-model eval (later workstream) covers detectors.

**Cost/latency pressures.** Long episodes × camera snapshots × hosted vision
models dominate spend. Controls: per-episode snapshot budget, heartbeat
interval, step budget, `--limit` during development, and mock-backend
iteration before any provider-backed run.

**Reversibility.** Placements are config, not code: `DMB_SIM_BACKEND`,
model ids, and budget env vars select the split per run. Moving a workload
(e.g. SITL into CI, UE onto a second workstation) changes deployment files
under `infra/`, never the eval tasks.
