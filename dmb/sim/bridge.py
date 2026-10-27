"""Simulation backends behind one interface.

Track 1 (phase 1): Gazebo + ArduPilot SITL.
Track 2 (fidelity): Colosseum/Unreal (runs on the operator's GPU workstation).
``MockBridge`` is a deterministic grid world so evals, tools, and scorers run
anywhere with no simulator installed.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class DroneState:
    x: int = 0
    y: int = 0
    altitude_m: float = 0.0
    armed: bool = False
    airborne: bool = False
    battery_pct: float = 100.0


@dataclass
class Victim:
    category: str
    x: int
    y: int
    mobility: str = "static"
    found: bool = False
    rescued: bool = False


@dataclass
class Observation:
    text: str
    telemetry: dict
    edge_report: dict | None = None


class SimBridge(ABC):
    """Backend-agnostic episode interface. One instance per sample."""

    @abstractmethod
    def reset(self, metadata: dict) -> Observation:
        """Load (scenario, seed) from sample metadata; return initial obs."""

    @abstractmethod
    def act(self, action: str, params: dict) -> Observation:
        """Apply one primitive; return the resulting observation."""

    @abstractmethod
    def get_state(self) -> dict:
        """Full serialisable episode state for scorers and the registry."""

    @abstractmethod
    def close(self) -> None:
        """Release backend resources (sim instance, connections)."""


class MockBridge(SimBridge):
    """Deterministic grid world. No external dependencies."""

    def __init__(self, step_budget: int = 60, battery_drain_per_step: float = 1.0) -> None:
        self.step_budget = step_budget
        self.battery_drain = battery_drain_per_step
        self.drone = DroneState()
        self.victims: list[Victim] = []
        self.hazards: list[dict] = []
        self.width = 10
        self.height = 10
        self.steps = 0
        self.safety_violations = 0
        self.seed = 0
        self.scenario = "mock"

    @classmethod
    def from_metadata(cls, metadata: dict, **kwargs: object) -> "MockBridge":
        bridge = cls(**kwargs)  # type: ignore[arg-type]
        bridge.reset(metadata)
        return bridge

    def reset(self, metadata: dict) -> Observation:
        grid = metadata.get("grid", {})
        self.width = int(grid.get("width", 10))
        self.height = int(grid.get("height", 10))
        self.scenario = str(metadata.get("scenario", "mock"))
        self.seed = int(metadata.get("seed", 0))
        self.victims = [Victim(**v) for v in metadata.get("victim_placements", [])]
        self.hazards = list(metadata.get("hazards", []))
        self.drone = DroneState(battery_pct=100.0)
        self.steps = 0
        self.safety_violations = 0
        return self._observe("Episode start. Drone on pad at (0, 0), disarmed.")

    # -- primitives -----------------------------------------------------
    def _tick(self) -> None:
        self.steps += 1
        if self.drone.airborne:
            self.drone.battery_pct = max(0.0, self.drone.battery_pct - self.battery_drain)

    def _in_hazard(self, x: int, y: int) -> bool:
        for hz in self.hazards:
            cx, cy, r = int(hz.get("x", -1)), int(hz.get("y", -1)), float(hz.get("radius", 0))
            if math.hypot(x - cx, y - cy) <= r:
                return True
        return False

    def arm(self) -> Observation:
        self.drone.armed = True
        return self._observe("Armed.")

    def takeoff(self, altitude_m: float) -> Observation:
        if not self.drone.armed:
            return self._observe("Refused: arm before takeoff.")
        if altitude_m <= 0:
            return self._observe("Refused: altitude must be positive.")
        self.drone.airborne = True
        self.drone.altitude_m = altitude_m
        self._tick()
        return self._observe(f"Takeoff to {altitude_m:.1f} m.")

    def goto(self, x: int, y: int) -> Observation:
        if not self.drone.airborne:
            return self._observe("Refused: not airborne.")
        self.drone.x = max(0, min(self.width - 1, x))
        self.drone.y = max(0, min(self.height - 1, y))
        self._tick()
        if self._in_hazard(self.drone.x, self.drone.y):
            self.safety_violations += 1
            return self._observe(
                f"Moved to ({self.drone.x}, {self.drone.y}). WARNING: hazard zone."
            )
        return self._observe(f"Moved to ({self.drone.x}, {self.drone.y}).")

    def loiter(self, seconds: int = 5) -> Observation:
        if not self.drone.airborne:
            return self._observe("Refused: not airborne.")
        self._tick()
        return self._observe(f"Loitering {seconds}s at ({self.drone.x}, {self.drone.y}).")

    def land(self) -> Observation:
        self.drone.airborne = False
        self.drone.altitude_m = 0.0
        self._tick()
        return self._observe(f"Landed at ({self.drone.x}, {self.drone.y}).")

    def rtl(self) -> Observation:
        self.drone.x, self.drone.y = 0, 0
        self.drone.airborne = False
        self.drone.altitude_m = 0.0
        self._tick()
        return self._observe("Returned to launch and landed.")

    # -- interface ------------------------------------------------------
    def act(self, action: str, params: dict) -> Observation:
        handler = {
            "arm": lambda p: self.arm(),
            "takeoff": lambda p: self.takeoff(float(p.get("altitude_m", 10.0))),
            "goto": lambda p: self.goto(int(p["x"]), int(p["y"])),
            "loiter": lambda p: self.loiter(int(p.get("seconds", 5))),
            "land": lambda p: self.land(),
            "rtl": lambda p: self.rtl(),
        }.get(action)
        if handler is None:
            return self._observe(f"Unknown action: {action}")
        return handler(params or {})

    def victims_within(self, radius: float) -> list[Victim]:
        return [
            v
            for v in self.victims
            if math.hypot(v.x - self.drone.x, v.y - self.drone.y) <= radius
        ]

    def mark_found(self, victim: Victim) -> None:
        victim.found = True

    def _observe(self, event: str) -> Observation:
        telemetry = {
            "x": self.drone.x,
            "y": self.drone.y,
            "altitude_m": self.drone.altitude_m,
            "armed": self.drone.armed,
            "airborne": self.drone.airborne,
            "battery_pct": round(self.drone.battery_pct, 1),
            "steps": self.steps,
            "safety_violations": self.safety_violations,
        }
        return Observation(text=event, telemetry=telemetry)

    def get_state(self) -> dict:
        return {
            "scenario": self.scenario,
            "seed": self.seed,
            "steps": self.steps,
            "step_budget": self.step_budget,
            "safety_violations": self.safety_violations,
            "drone": {
                "x": self.drone.x,
                "y": self.drone.y,
                "altitude_m": self.drone.altitude_m,
                "armed": self.drone.armed,
                "airborne": self.drone.airborne,
                "battery_pct": self.drone.battery_pct,
            },
            "victims": [
                {
                    "category": v.category,
                    "x": v.x,
                    "y": v.y,
                    "found": v.found,
                    "rescued": v.rescued,
                }
                for v in self.victims
            ],
            "hazards": self.hazards,
        }

    def close(self) -> None:
        return None


class GazeboSITLBridge(SimBridge):
    """Track 1 backend: Gazebo world + ArduPilot SITL over MAVLink.

    Implemented in the sim-spike workstream (see docs/action-surface.md).
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "GazeboSITLBridge is implemented in the sim-spike issue. "
            "Use MockBridge until then."
        )

    def reset(self, metadata: dict) -> Observation:
        raise NotImplementedError

    def act(self, action: str, params: dict) -> Observation:
        raise NotImplementedError

    def get_state(self) -> dict:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class ColosseumBridge(SimBridge):
    """Track 2 backend: Colosseum/Unreal on the operator GPU workstation."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "ColosseumBridge is implemented in the fidelity-track issue. "
            "Use MockBridge until then."
        )

    def reset(self, metadata: dict) -> Observation:
        raise NotImplementedError

    def act(self, action: str, params: dict) -> Observation:
        raise NotImplementedError

    def get_state(self) -> dict:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError
