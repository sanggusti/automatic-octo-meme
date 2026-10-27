# Scenarios

Five disaster types under `scenarios/`, each a YAML with: grid size, victim
categories (`human`/`child`/`animal` with count ranges and mobility),
hazard zones, weather options, and difficulty knobs.

| Scenario | Kind | Grid | Notes |
|---|---|---|---|
| `forest_fire` | Wildfire + haze | 10×10 | Low visibility; fire-front hazards |
| `flash_flood` | Valley surge | 12×10 | Rising water; drifting hazards |
| `flood` | Standing water | 14×10 | Large area; submerged power lines |
| `earthquake` | Urban rubble | 10×10 | Trapped victims; unstable structures |
| `landslide` | Slope debris | 10×12 | Low visibility; extending slip face |

## Determinism contract

A sample is `(scenario, seed)`. `build_samples` places victims with a seeded
RNG; `world_hash` fingerprints the placement. Same seed ⇒ same world, always.
Difficulty stratification (easy/medium/hard seed bands, weather/time dynamics,
stochastic placement) is added by the scenario-pack workstream following the
ESARBench precedent (600 seeded tasks, dynamic weather/time-of-day).

## Adding a scenario

1. Copy an existing YAML, set the required keys (`name`, `kind`,
   `description`, `grid`, `victims`, `hazards`, `weather`, `difficulty`).
2. `build_samples("<name>", seeds=[...])` in a new `evals/<name>.py` task
   (or extend the shared mission solver).
3. Register expected score ranges after the first tracked run.
