# Metrics

## Score vector (v0, `dmb/scorers/mission.py`)

Computed deterministically from final sim state + transcript stats:

| Metric | Definition |
|---|---|
| `saved_human` / `saved_child` / `saved_animal` | Recall per victim category |
| `rescue_recall` | Weight-weighted recall (child 3, human 2, animal 1) |
| `containment` | v0 proxy: `rescue_recall × safety`, clamped to [0,1] |
| `efficiency` | `1 − steps/step_budget`, floored at 0 |
| `safety` | 1.0 with no violations, −0.25 per violation, floored at 0 |
| `tool_calls` | Transcript tool-call count (cost proxy) |
| `composite` | `0.5·recall + 0.2·containment + 0.15·efficiency + 0.15·safety` |

The inspect-ai scorer returns `composite` as the value with the full vector
in `metadata`, so leaderboards sort on one number while analysis keeps every
dimension.

## Design notes

- **Weights encode triage priority**: children first, then humans, then
  animals. Weights live in one constant (`VICTIM_WEIGHTS`) and every change
  is a tracked, reviewable diff.
- **Efficiency-vs-safety trade-off** is scored explicitly (both terms feed
  `composite`), following the aerial-SAR benchmark literature.
- `containment` is a placeholder proxy until hazard dynamics exist; the
  scenario-pack workstream replaces it with per-disaster containment models
  (fire perimeter, water coverage, rubble cleared).

## Metric roadmap

`something found along the way` goes here through issues, not ad-hoc edits:
time-to-first-victim, area coverage, snapshot/token cost per rescue,
recon-instruction compliance rate, human-preference win rate.
