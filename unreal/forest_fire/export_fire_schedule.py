"""T2 fire-schedule export (#50): T0 spread -> UE particle/fog timeline.

Runs FireModel for a scenario + weather and writes one JSON schedule:
per-step ignited / smoldering / burning / burned cell sets plus the haze
index. The UE burning variant plays this schedule (Niagara fire + smoke
emitters on the listed cells, fog density from haze); it never redefines
T0 semantics (docs/physics-assets.md). One step = 5 sim-seconds, the
mock-backend clock (dmb/sim/bridge.py).

Usage: python unreal/forest_fire/export_fire_schedule.py forest_fire_peat --weather drought-extreme --out /tmp/ue
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CELL_M = 5.0
STEP_SECONDS = 5.0


def load_fire(scenario: str, weather: str | None) -> tuple[dict, int, int]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from dmb.scenarios import load_scenario  # noqa: PLC0415

    config = load_scenario(scenario)
    if weather is not None and weather not in config.weather:
        raise ValueError(f"Weather {weather!r} not in {scenario} options {config.weather}")
    fire = dict((config.raw.get("dynamics", {}) or {}).get("fire", {}))
    if weather is not None:
        fire["weather_active"] = weather
    grid = config.grid
    return fire, int(grid.get("width", 10)), int(grid.get("height", 10))


def run_schedule(fire: dict, width: int, height: int, steps: int) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from dmb.physics.fire import FireModel  # noqa: PLC0415

    model = FireModel(fire, width, height)
    timeline = []
    for step in range(steps + 1):
        if step:
            model.step(step)
        timeline.append(
            {
                "step": step,
                "t_seconds": round(step * STEP_SECONDS, 1),
                "ignited": sorted(f"{x},{y}" for x, y in model.ignited),
                "smoldering": sorted(
                    f"{x},{y}" for x, y in model.smoldering_cells(step)
                ),
                "burning": sorted(f"{x},{y}" for x, y in model.burning_cells(step)),
                "burned": sorted(f"{x},{y}" for x, y in model.burned_cells(step)),
                "haze": model.haze_index(step),
            }
        )
    return {
        "cell_m": CELL_M,
        "step_seconds": STEP_SECONDS,
        "grid": {"width": width, "height": height},
        "summary": {
            "first_breakout": min(model.ignited.values()) if model.ignited else None,
            "total_ignited": len(model.ignited),
            "total_smolder": len(model.smolder),
        },
        "steps": timeline,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export T0 fire schedule as JSON.")
    parser.add_argument("scenario")
    parser.add_argument("--weather", default=None)
    parser.add_argument("--steps", type=int, default=60)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    fire, width, height = load_fire(args.scenario, args.weather)
    schedule = run_schedule(fire, width, height, args.steps)
    schedule["scenario"] = args.scenario
    schedule["weather"] = args.weather
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "fire_schedule.json"
    path.write_text(json.dumps(schedule, indent=1))
    summary = schedule["summary"]
    print(f"{args.steps + 1} steps -> {path} {summary}")


if __name__ == "__main__":
    main()
