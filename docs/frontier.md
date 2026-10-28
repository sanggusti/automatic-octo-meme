# Frontier Plan — Feasibility & Improvement Roadmap

Can Disaster Mitigation Bench stand with the frontier of LM×drone
benchmarks? Verdict: **yes, with four closable gaps** (scale, dynamics,
perception, data flywheel). This doc records the evidence, the gaps, and
the phased improvements. Each phase owns a GitHub issue; status lives in
`docs/roadmap.md`.

## Frontier bars (evidence, inspected 2026-10-27)

| Benchmark | What sets the bar |
|---|---|
| ESARBench | UE5 + AirSim, 4 GIS-mapped environments, 600 tasks from real rescue cases, weather/time-of-day/stochastic dynamics, Success Rate + Clue Discovery metrics, heuristic-to-MLLM baselines |
| AeroVerse | One simulator feeding real + virtual pre-training sets, 5 finetuning instruction sets (scene/reason/nav/plan/act), 10+ metric eval, finetuned agent model +8.52% over baselines — the post-training flywheel precedent |
| Cell2Fire | Open-source cell-based fire spread on per-cell fuel/weather/moisture/topography with FBP-system rate-of-spread, >90% vs Prometheus at up to 30× speed — the physics-accuracy precedent |

Sources: `https://arxiv.org/html/2605.01371`,
`https://arxiv.org/html/2408.15511`,
`https://www.frontiersin.org/journals/forests-and-global-change/articles/10.3389/ffgc.2021.692706/full`

## Where we stand (2026-10-27)

- 6 scenarios × 3 seeds (18 samples); mock + verified SITL/Gazebo backends
  with real GUIDED flight (`GazeboSITLBridge`).
- Deterministic v0 metric vector (weighted rescue recall, containment
  proxy, efficiency, safety); metric roadmap in `docs/metrics.md`.
- Edge-first perception design; watcher L2/T3 replay and physics-asset
  packs specified, unbuilt (#16–#19).
- Modal inference verified; Baseten blocked on credits; human evals
  specified (#5).

Structural differentiators to keep: the recon-advisor second role,
edge-first scarcity, ArduPilot-native actions, inspect-ai rigor with human
baselines, fully reproducible open stack.

## Gaps

1. **Scale** — 18 vs hundreds of tasks. Closable via the seeded generator;
   SITL runs realtime, so SIM_SPEEDUP + parallel workers come first.
2. **Dynamics** — static hazards (+ tsunami phases); no validated
   spread/surge models. Adopt validated sub-models; never invent dynamics.
3. **Perception** — truth-based stub, no camera frames, no UE track.
4. **Flywheel** — no trajectory export for post-training. Watcher L2 is the
   data contract: one format feeds replay, SFT pairs, and RLVR rewards.

## Phases

- **A — eval rigor.** Difficulty scoring, intermediate metrics
  (first-find rate, coverage), human baselines, ≥100 seeded mock samples,
  heuristic + random baseline agents. Validated by: difficulty stratifies
  outcomes; heuristics green in CI.
- **B — physics accuracy.** FBP-style per-cell fire ROS/intensity with
  reference snapshot tolerance; surge/slip rules with snapshot tests;
  per-disaster containment on dynamics. Validated by: snapshot tests on
  fixed seeds; containment monotonic with controlled damage.
- **C — perception + fidelity.** SITL camera frames (truth-annotated),
  edge-VLM baseline behind the trigger/budget interface, UE/Colosseum GIS
  terrain. Validated by: budgeted frame flow; UE reproduces navigation
  verdicts (fidelity, not equality).
- **D — data flywheel.** L2 → SFT pairs (state → action + CoT) and RLVR
  episodes (metric rewards); finetune Modal custom model on train seeds;
  re-eval on held-out seeds; publish dataset. Validated by: positive delta
  on held-out seeds — null/negative falsifies the flywheel, not the bench.
- **E — release bar.** 600+ seeded tasks, full baseline table, one-command
  reproduction, results + limitations writeup. Validated by: fresh-clone
  reproduction from registry + seeds.

## Standing rules

- Determinism gates scale-ups (world/snapshot hashes).
- Train/test seeds disjoint, always.
- Real-world data pairing is out of scope until footage is sourced;
  sim-only is the honest claim.
- Rubric grading stays human; the simulated actor bounds, never replaces.
