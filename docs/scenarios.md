# Scenarios

Six disaster types under `scenarios/`, each a YAML with: grid size, victim
categories (`human`/`child`/`animal` with count ranges and mobility),
hazard zones, weather options, time-of-day options, and difficulty knobs.

Sample axes: `(scenario, seed)` plus optional `weather=` (dynamics
overrides: fire wind/moisture, terrain raining) and `time_of_day=`
(visibility: dawn/dusk 0.8×, night 0.5× detection radius). Axes append to
the sample id (`forest_fire-seed-1-clear-dusk`) and are validated loudly.

Difficulty bands (score cutoffs easy < 0.55 < medium < 0.65 < hard;
distribution over seeds 1..100): earthquake 9/48/43, flash_flood
16/68/16, flood 12/88/0 (no hard band — open water, few hazards),
forest_fire 7/40/53, landslide 30/68/2, tsunami 7/56/37
(easy/medium/hard).

| Scenario | Kind | Grid | Notes |
|---|---|---|---|
| `forest_fire` | Wildfire + haze | 10×10 | Low visibility; fire-front hazards |
| `tsunami` | Coastal surge | 12×10 | Warning phases; surge + debris hazards |
| `flash_flood` | Valley surge | 12×10 | Rising water; drifting hazards |
| `flood` | Standing water | 14×10 | Large area; submerged power lines |
| `earthquake` | Urban rubble | 10×10 | Trapped victims; unstable structures |
| `landslide` | Slope debris | 10×12 | Low visibility; extending slip face |

## Determinism contract

A sample is `(scenario, seed)` plus optional weather/time-of-day axes.
`build_samples` places victims with a seeded RNG; `world_hash`
fingerprints the placement. Same seed ⇒ same world, always
(regression-tested). Bands + weather/time axes shipped in #4, following
the ESARBench precedent (600 seeded tasks, dynamic weather/time-of-day);
scale-up to 600+ tasks is #29.

## Adding a scenario

1. Copy an existing YAML, set the required keys (`name`, `kind`,
   `description`, `grid`, `victims`, `hazards`, `weather`, `difficulty`).
2. `build_samples("<name>", seeds=[...])` in a new `evals/<name>.py` task
   (or extend the shared mission solver).
3. Register expected score ranges after the first tracked run.
