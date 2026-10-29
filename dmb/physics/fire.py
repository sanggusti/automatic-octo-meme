"""Cellular wildfire spread with FBP-style per-cell rate of spread.

ROS(cell <- burning neighbor) =
    base_ros * fuel * (1 - moisture) * wind_alignment(direction)

Follows the Cell2Fire/FBP structure (per-cell fuel, weather, moisture,
topography over a homogeneous grid) minus calibrated fuel-type tables,
which are documented future work, not silent precision.
"""

from __future__ import annotations

import math

NEIGHBORS = [
    (-1, -1), (0, -1), (1, -1),
    (-1, 0),           (1, 0),
    (-1, 1),  (0, 1),  (1, 1),
]


def _norm(vec: tuple[float, float]) -> tuple[float, float]:
    n = math.hypot(*vec)
    return (vec[0] / n, vec[1] / n) if n else (0.0, 0.0)


class FireModel:
    def __init__(self, config: dict, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.base_ros = float(config.get("base_ros", 0.25))
        self.threshold = float(config.get("ignition_threshold", 1.0))
        self.burn_duration = int(config.get("burn_duration", 12))
        self.moisture = float(config.get("moisture", 0.3))
        self.wind_speed = float(config.get("wind_speed", 0.0))
        # Weather coupling (#17): an explicit weather option overrides the
        # raw wind/moisture, so identical seeds diverge documentably across
        # weather. No weather key = raw config (legacy behavior).
        self.weather_active = config.get("weather_active")
        modifiers = config.get("weather_modifiers", {})
        if self.weather_active is not None:
            if self.weather_active not in modifiers:
                raise ValueError(
                    f"Unknown fire weather {self.weather_active!r} "
                    f"(have {sorted(modifiers)})"
                )
            mod = modifiers[self.weather_active]
            self.wind_speed = float(mod.get("wind_speed", self.wind_speed))
            self.moisture = float(mod.get("moisture", self.moisture))
        self.fuel_default = float(config.get("fuel_default", 0.7))
        self.fuel_map = {
            (int(c["x"]), int(c["y"])): float(c["fuel"])
            for c in config.get("fuel_map", [])
        }
        wind_dir = tuple(config.get("wind_dir", [1, 0]))
        self.wind = _norm((float(wind_dir[0]), float(wind_dir[1])))
        self.ignited: dict[tuple[int, int], int] = {}
        self.exposure: dict[tuple[int, int], float] = {}
        for cell in config.get("ignition", []):
            key = (int(cell["x"]), int(cell["y"]))
            if 0 <= key[0] < width and 0 <= key[1] < height:
                self.ignited[key] = 0

    def fuel_at(self, cell: tuple[int, int]) -> float:
        return self.fuel_map.get(cell, self.fuel_default)

    def wind_alignment(self, direction: tuple[int, int]) -> float:
        """Downwind spread faster; upwind never fully blocked (floor 0.2)."""
        dx, dy = _norm((float(direction[0]), float(direction[1])))
        dot = dx * self.wind[0] + dy * self.wind[1]
        return max(0.2, 1.0 + dot * self.wind_speed * 0.15)

    def burning_cells(self, step: int) -> set[tuple[int, int]]:
        return {
            cell for cell, start in self.ignited.items()
            if start <= step < start + self.burn_duration
        }

    def burned_cells(self, step: int) -> set[tuple[int, int]]:
        return {
            cell for cell, start in self.ignited.items()
            if step >= start + self.burn_duration
        }

    def step(self, current_step: int) -> list[tuple[int, int]]:
        """Advance one step; return newly ignited cells."""
        new: list[tuple[int, int]] = []
        for cell in self.burning_cells(current_step):
            for dx, dy in NEIGHBORS:
                nb = (cell[0] + dx, cell[1] + dy)
                if not (0 <= nb[0] < self.width and 0 <= nb[1] < self.height):
                    continue
                if nb in self.ignited:
                    continue
                ros = (
                    self.base_ros
                    * self.fuel_at(nb)
                    * (1.0 - self.moisture)
                    * self.wind_alignment((dx, dy))
                )
                self.exposure[nb] = self.exposure.get(nb, 0.0) + ros
                if self.exposure[nb] >= self.threshold:
                    self.ignited[nb] = current_step
                    new.append(nb)
        return new

    def danger_steps(self) -> dict[tuple[int, int], int]:
        """Cell -> step it became dangerous (ignition)."""
        return dict(self.ignited)

    def snapshot(self) -> dict:
        return {
            "weather": self.weather_active,
            "wind_speed": self.wind_speed,
            "moisture": self.moisture,
            "ignited": sorted(f"{x},{y}@{s}" for (x, y), s in self.ignited.items()),
        }
