# Roadmap

Ordered workstreams; each owns a GitHub issue. Dependencies flow top-down.
Status as of 2026-10-27 in brackets.

1. **Inference spike** (#1) — first verified Baseten + Modal runs through the
   smoke and forest-fire tasks. [partial 2026-10-27: Modal verified, deployment
   stopped; Baseten still blocked on credits] Unblocks all real-model work.
2. **Sim spike (Track 1)** (#2) — pinned image builds; SITL+Gazebo boots;
   scripted GUIDED takeoff/hover/land; MAVLink message set documented;
   `GazeboSITLBridge` implemented against the `SimBridge` contract.
3. **Drone-spec assets** (#3) — replace placeholder specs with pulls from
   ArduPilot frame params + `ardupilot_gazebo` models; enforce
   capability gating in the solver.
4. **Scenario pack** (#4) — difficulty stratification, weather/time dynamics,
   per-disaster containment models replacing the v0 proxy.
5. **Recon advisor + human evals** (#5) — human-actor check, guided human-agent
   baseline tooling, first graded + baselined runs.
6. **Fidelity track (Track 2)** (#6) — Colosseum/Unreal on the GPU workstation,
   `ColosseumBridge`, one parported scenario.
7. **Baseline sweep** (#7) — 2–3 Baseten models + 1 Modal custom model over the
   full scenario pack; first published results table. [blocked on #1, #4]
8. **Results aggregation** (#8) — `runs/*/scores.json` → tables/plots script.
9. **Tsunami scenario** (#15) — task wiring + phase dynamics + golden scores.
10. **Scenario watcher** (#16) — L2 event log, T1 replay CLI, T2 backend
    capture, T3 composite design.
11. **Asset pack: vegetation + fire** (#17) — fuel grid, spread model, T1 flora.
12. **Asset pack: terrain + water** (#18) — surge/slip dynamics, T1 water/terrain.
13. **Asset pack: actors** (#19) — human/animal param schema + T1 figures.
