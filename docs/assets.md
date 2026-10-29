# Assets — Drone Specification Pipeline

Vehicle capabilities are versioned data, not folklore. `assets/drones/*.yaml`
feeds sim backends (SITL params, Gazebo models) and task setup (which skills
a mission may assume).

## Spec schema (required keys)

`name`, `vehicle_class`, `provenance`, `capabilities`. Optional: `sensors`,
`sitl_params` (param overrides like `FRAME_CLASS`), `gazebo_model`.

`provenance` is load-bearing: `placeholder` values are honest stubs the
assets workstream replaces with pulls from ArduPilot sources:

1. **Frame parameter files** from ArduPilot (frame class/type, tuning).
2. **`ardupilot_gazebo` models/worlds** for Track 1 vehicle meshes + plugins.
3. **ArduPilot vehicle docs** for capability flags (GUIDED/AUTO support,
   sensor requirements).

## Current inventory

| Spec | Class | Provenance |
|---|---|---|
| `quad_iris_class` | multicopter | sourced (#3): Copter-4.6.3 gazebo-iris.parm + ardupilot_gazebo@80dc9664 |
| `fixedwing_scout` | fixed-wing | sourced (#3): Copter-4.6.3 gazebo-zephyr.parm + ardupilot_gazebo@80dc9664 |

Per-value citations live as comments in `assets/drones/*.yaml`; hub pins in
`assets/manifest.yaml`. Honest unknowns stay `null` (e.g. flight time —
ArduPilot sources don't state it) rather than invented.

## Rules

- A mission may only use capabilities the assigned spec declares
  (`DroneSpec.supports(...)`); the solver asserts this at episode start
  (`assert_mission_capable`, enforced since #3).
- Every spec change cites its source commit/URL in the PR.
- Capability flags the backend cannot honour fail loudly at reset, never
  silently downgrade.
