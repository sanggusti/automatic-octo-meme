"""T2 vegetation export (#50): T0 fuel grid -> UE foliage CSV.

Mirrors assets/vegetation/place_trees.py (T1 SDF) for the Unreal track:
one row per foliage instance with grid + metre coordinates, species
class, flammability, and peat depth. Import the CSV as a UE DataTable,
then scatter instanced foliage from it (steps in README.md). Species
classes are stable names the operator maps to the chosen art pack;
no decision depends on branches (docs/physics-assets.md).

Usage: python unreal/forest_fire/export_foliage.py forest_fire_peat --seed 1 --out /tmp/ue
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

CELL_M = 5.0


def load_fire(scenario: str) -> tuple[dict, int, int]:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from dmb.scenarios import load_scenario  # noqa: PLC0415

    config = load_scenario(scenario)
    fire = (config.raw.get("dynamics", {}) or {}).get("fire", {})
    grid = config.grid
    return fire, int(grid.get("width", 10)), int(grid.get("height", 10))


def peat_depths(fire: dict) -> dict[tuple[int, int], float]:
    peat = fire.get("peat") or {}
    depths: dict[tuple[int, int], float] = {}
    for block in peat.get("peat_blocks", []):
        for x in range(int(block["x0"]), int(block["x1"]) + 1):
            for y in range(int(block["y0"]), int(block["y1"]) + 1):
                depths[(x, y)] = float(block["depth"])
    for c in peat.get("peat_map", []):
        depths[(int(c["x"]), int(c["y"]))] = float(c["depth"])
    default = float(peat.get("depth_default", 0.0))
    return depths, default


def place(fire: dict, width: int, height: int, seed: int, threshold: float = 0.3):
    rng = random.Random(seed)
    fuel_map = {(c["x"], c["y"]): float(c["fuel"]) for c in fire.get("fuel_map", [])}
    default = float(fire.get("fuel_default", 0.0))
    depths, peat_default = peat_depths(fire)
    instances = []
    for x in range(width):
        for y in range(height):
            fuel = fuel_map.get((x, y), default)
            if fuel < threshold:
                continue
            peat = depths.get((x, y), peat_default)
            if peat > 0:
                species = "peat_swamp_tree" if rng.random() < 0.7 else "underbrush"
            elif fuel >= 0.6:
                species = "canopy_tree" if rng.random() < 0.7 else "underbrush"
            else:
                species = "underbrush" if rng.random() < 0.6 else "canopy_tree"
            instances.append(
                {
                    "name": f"{species}_x{x}_y{y}",
                    "species": species,
                    "x_cell": x,
                    "y_cell": y,
                    "x_m": round(x * CELL_M, 2),
                    "y_m": round(y * CELL_M, 2),
                    "flammability": round(fuel, 3),
                    "peat_depth": round(peat, 3),
                }
            )
    return instances


def main() -> None:
    parser = argparse.ArgumentParser(description="Export T0 fuel as UE foliage CSV.")
    parser.add_argument("scenario")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--threshold", type=float, default=0.3)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    fire, width, height = load_fire(args.scenario)
    instances = place(fire, width, height, args.seed, args.threshold)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "foliage.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "name", "species", "x_cell", "y_cell",
                "x_m", "y_m", "flammability", "peat_depth",
            ],
        )
        writer.writeheader()
        writer.writerows(instances)
    print(f"{len(instances)} instances -> {out / 'foliage.csv'}")


if __name__ == "__main__":
    main()
