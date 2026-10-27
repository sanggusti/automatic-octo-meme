# Scenario Watcher — Observability & Replay

Goal: any benchmark run must be **replayable** — a reviewer can step through
what the model perceived, decided, and did, in sim time, and audit every
score against visible evidence.

## Three evidence layers

| Layer | Content | Source | Status |
|---|---|---|---|
| L1 transcript | LM messages, tool calls + results, scores | inspect-ai `.eval` log | exists (`inspect view`) |
| L2 event log | timestamped sim events: actions, edge reports, victim/hazard transitions, scorer inputs | new `dmb/watch/` recorder | specified here, built in watcher issue |
| L3 sim capture | backend-native replay artifacts | `--record-path` / `startRecording` / frame dumps | specified here, wired per backend |

No single layer is sufficient: L1 shows reasoning, L2 shows episode
causality, L3 shows what "really happened" in the world.

## L2 event-log format (contract)

One JSONL file per sample: `runs/<run_id>/trajectories/<sample_id>.jsonl`.
Every line is one event:

```json
{"t": 12.5, "step": 7, "kind": "action", "tool": "goto_location",
 "args": {"x": 4, "y": 6}, "obs": "Moved to (4, 6)."}
{"t": 13.1, "step": 7, "kind": "edge", "trigger": "novelty",
 "summary": "New detections: child at (5,6).", "frame_ref": "snapshot-..."}
{"t": 13.1, "step": 7, "kind": "state", "rescued": 2, "violations": 0}
```

- `t`: sim seconds since episode start (monotonic; backends map wall→sim).
- `kind`: `action` | `edge` | `state` | `score` | `note`.
- The recorder is a `Watcher` interface (`on_start/on_event/on_end`) fed by
  the solver; backends never write it directly.
- Retention: L2 is small (text) — keep forever. L3 artifacts are budgeted
  (see below).

## L3 per backend (verified mechanisms)

- **Mock**: trajectory renderer — replay L2 into an SVG/frame sequence
  (grid, drone path, detections, hazard overlays). No external dependency.
- **Gazebo (Track 1)**: launch the sample's sim with
  `gz sim --record-path runs/<id>/sim/<sample> ...`; playback any episode
  with `gz sim --playback <path>`. `--record-resources` captures models and
  textures when a run must be self-contained. Recording can also be set in
  SDF via the `LogRecord` plugin. Reference: Gazebo Sim logging docs,
  `gazebosim.org/api/sim/7/log.html`.
- **Colosseum/Unreal (Track 2)**: `client.startRecording()` /
  `client.stopRecording()` / `client.isRecording()` around the episode, with
  recorded data configured through settings; `simGetImages` for keyframes.
  Inherited from the AirSim API surface — the Track 2 issue verifies each
  call against Colosseum before relying on it. Reference: AirSim Core APIs,
  `microsoft.github.io/AirSimExtensions/apis`.

## Replay modes (user-facing)

- **T0 transcript replay** — `inspect view` on the `.eval` log. Available now.
- **T1 event replay** — CLI reading L2 JSONL: step, filter by kind, print the
  episode as a narrated timeline. First watcher deliverable.
- **T2 sim playback** — backend-native (`--playback`, recorded video).
  Proves the world behaved as the transcript claims.
- **T3 composite replay** — one timeline syncing L1+L2+L3 (transcript beside
  sim view beside edge reports). The "replay mode" target; built after T1+T2
  exist. UI shape (web timeline vs. notebook) decided in the watcher issue.

## Budgets & rules

- L3 capture is per-sample and opt-out, never opt-in: a run without replay
  evidence is incomplete.
- Snapshot/frame budgets from `docs/specs.md` apply; L3 video (if any) is
  capped per episode and downsampled.
- The registry links all three layers per sample; `scores.json` must be
  reproducible from L2 alone (audit rule).
