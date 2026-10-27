# Edge-First Perception

## Principle

Vision runs on the edge device (light, cheap, always-on). The hosted LM is
the **navigator/orchestrator**: it receives compact reports and spends a
small snapshot budget only when a decision needs pixels. This mirrors real
disaster deployments — scarce compute, scarce bandwidth, intermittent link —
and keeps LM scores about decisions, not detector quality.

## Report occasions

| Trigger | When | Content |
|---|---|---|
| `novelty` | Edge sees a never-reported detection | New labels + positions |
| `heartbeat` | Every `heartbeat_every_steps` env steps | In-view count, totals found |
| `requested` | LM calls `request_edge_report` | Full scan + snapshot if budget remains |
| (future) | `takeoff`, `hazard-proximity`, link-loss | Lifecycle/safety events |

## Budgets (env-configurable)

- `DMB_EDGE_REPORT_INTERVAL_STEPS` (default 5): heartbeat cadence.
- `DMB_EDGE_MAX_SNAPSHOTS_PER_EPISODE` (default 8): on-demand frames per
  episode. Exhaustion degrades to report-only, never fails the episode.

## Implementation

- `dmb/perception/edge.py`: `EdgePerception` ABC, `TriggerConfig`,
  `FrameBudget`, `StubEdgePerception` (rule-based over `MockBridge` state).
- Real backends implement the same interface with an on-device model; trigger
  semantics and budget accounting do not change.
- Snapshots are referenced by `frame_ref` artifact ids; the registry stores
  the mapping so any report can be audited against its pixels later.

## What is NOT scored here

Detector precision/recall belongs to a future edge-model eval workstream.
Mission scorers treat edge reports as given input and score what the LM did
with them (coverage, prioritisation, safety, efficiency).
