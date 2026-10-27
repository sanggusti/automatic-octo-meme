# Action Surface — ArduPilot-Derived Drone Tools

## Source of truth

Flight semantics follow ArduPilot Copter in **GUIDED mode**: `mode guided`
→ `arm throttle` → `takeoff <alt>` → position/loiter commands → `land`/`RTL`,
with missions and geofence available. The Track 1 backend speaks to real SITL
over MAVLink; exact message bindings are pinned in the sim-spike workstream.
Until then, `MockBridge` implements identical tool-level semantics on a grid.

## LM tools (`dmb/tools/drone.py`)

| Tool | Args | Effect |
|---|---|---|
| `arm` | — | Arm motors (required before takeoff) |
| `takeoff` | `altitude_m: float` | Climb and hover; refused if disarmed or non-positive |
| `goto_location` | `x: int, y: int` | Fly to coordinates (grid now; lat/lon or local-NED on SITL) |
| `loiter` | `seconds: int` | Hold position while edge perception scans |
| `land` | — | Land in place |
| `return_to_launch` | — | Abort: return and land |
| `get_telemetry` | — | Position, altitude, battery, steps, violations |
| `request_edge_report` | — | On-demand perception scan (consumes snapshot budget) |

Movement tools append any edge report (`[edge:<trigger>] ...`) so perception
arrives as a side channel of acting, matching deployment reality.

## Higher-level skills (operator-named)

- **Non-GPS navigation**: composite skill over optical-flow / visual-odometry
  position estimates; exposed as a tool once the SITL message set is pinned.
  Mock behavior: allowed everywhere; GPS-denied zones arrive with Track 1.
- **Nav-mesh path planning**: `goto` through a mesh-aware planner instead of
  direct flight; mock moves directly, SITL/Colosseum route around obstacles.
- Both skills must degrade honestly: if the backend cannot do them, the tool
  errors instead of pretending.

## Tooling contract for new backends

1. One bridge instance per sample; `close()` releases everything.
2. `act()` returns an `Observation(text, telemetry)`; never raises on
   pilot error — refusals are text the LM can learn from.
3. `get_state()` is JSON-serialisable and scorer-sufficient.
4. Tool names and arg shapes stay stable across backends; only the
   coordinate frame and dynamics change (documented per backend).
