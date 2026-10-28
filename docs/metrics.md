# Metrics

## Score vector (v0, `dmb/scorers/mission.py`)

Computed deterministically from final sim state + transcript stats:

| Metric | Definition |
|---|---|
| `saved_human` / `saved_child` / `saved_animal` | Recall per victim category |
| `rescue_recall` | Weight-weighted recall (child 3, human 2, animal 1) |
| `containment` | Beat-the-spread: weight-weighted fraction of victims found before their cell became dangerous, × safety |
| `efficiency` | `1 − steps/step_budget`, floored at 0 |
| `safety` | 1.0 with no violations, −0.25 per violation, floored at 0 |
| `tool_calls` | Transcript tool-call count (cost proxy) |
| `found_any` | 1.0 if ≥1 victim found, else 0.0 (mean = first-find rate) |
| `first_find_step` | Episode step of first find (−1 if none) |
| `coverage` | Unique cells visited / total cells |
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
- `containment` is beat-the-spread on dynamics (`dmb/physics/`): each cell
  records the step it became dangerous, each victim the step it was found.
  Without dynamics every danger step is infinite and it reduces to recall ×
  safety. Per-disaster refinements (fire perimeter held, water coverage
  searched, rubble cleared) remain future work.

## Difficulty scoring (`dmb/difficulty.py`)

Every sample carries `difficulty_score: {score 0..1, band}` computed
deterministically from victim count, mean distance from origin, hazard
coverage, visibility, and mobility mix. Bands (easy < 0.55 < medium < 0.65
< hard) are calibrated on seeds 1..100 across scenarios. Validation: a
fixed-effort probe scores easy > medium > hard
(`tests/test_baselines.py`).

## Metric roadmap

`something found along the way` goes here through issues, not ad-hoc edits:
time-to-first-victim, area coverage, snapshot/token cost per rescue,
recon-instruction compliance rate, human-preference win rate.
