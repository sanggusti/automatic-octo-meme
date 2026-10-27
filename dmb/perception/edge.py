"""Edge-first perception: light on-device vision, event-driven LM reports.

Design (see docs/edge-perception.md): a small vision model runs on the edge
device and only escalates to the navigator LM on specific occasions —
periodic heartbeat, novel detection, or explicit LM request. Raw frames never
stream to the LM by default; the LM reasons over compact reports and a small
budget of on-demand snapshots. This grounds the benchmark in real
resource-scarce deployments.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Detection:
    label: str
    x: int
    y: int
    confidence: float


@dataclass
class EdgeReport:
    trigger: str  # "heartbeat" | "novelty" | "requested" | "takeoff" | ...
    step: int
    summary: str
    detections: list[Detection] = field(default_factory=list)
    frame_ref: str | None = None  # artifact id when a snapshot was attached


@dataclass
class TriggerConfig:
    heartbeat_every_steps: int = 5
    report_on_novelty: bool = True
    detection_radius: float = 3.0


class FrameBudget:
    """Caps how many full snapshots the LM may pull per episode."""

    def __init__(self, max_snapshots: int) -> None:
        self.max_snapshots = max_snapshots
        self.used = 0

    def request(self) -> bool:
        if self.used >= self.max_snapshots:
            return False
        self.used += 1
        return True


class EdgePerception(ABC):
    @abstractmethod
    def on_step(self, step: int) -> EdgeReport | None:
        """Maybe emit a heartbeat/novelty report after an env step."""

    @abstractmethod
    def on_demand(self, step: int) -> EdgeReport:
        """Explicit LM-requested report (consumes snapshot budget)."""


class StubEdgePerception(EdgePerception):
    """Rule-based stand-in driven by MockBridge state.

    Real backends implement this interface with an on-device model; the
    trigger semantics stay identical.
    """

    def __init__(
        self,
        bridge,  # MockBridge (duck-typed to avoid an import cycle)
        config: TriggerConfig,
        budget: FrameBudget,
    ) -> None:
        self.bridge = bridge
        self.config = config
        self.budget = budget
        self._known_ids: set[int] = set()
        self._last_heartbeat = 0

    def _scan(self) -> tuple[list[Detection], list]:
        detections: list[Detection] = []
        novel: list = []
        if not self.bridge.drone.airborne:
            return detections, novel
        for victim in self.bridge.victims_within(self.config.detection_radius):
            vid = id(victim)
            detections.append(
                Detection(
                    label=victim.category,
                    x=victim.x,
                    y=victim.y,
                    confidence=0.9,
                )
            )
            if vid not in self._known_ids:
                self._known_ids.add(vid)
                novel.append(victim)
                self.bridge.mark_found(victim)
        return detections, novel

    def on_step(self, step: int) -> EdgeReport | None:
        detections, novel = self._scan()
        if novel and self.config.report_on_novelty:
            desc = ", ".join(f"{v.category} at ({v.x},{v.y})" for v in novel)
            return EdgeReport(
                trigger="novelty",
                step=step,
                summary=f"New detections: {desc}.",
                detections=detections,
            )
        if step - self._last_heartbeat >= self.config.heartbeat_every_steps:
            self._last_heartbeat = step
            return EdgeReport(
                trigger="heartbeat",
                step=step,
                summary=(
                    f"Heartbeat: {len(detections)} in view, "
                    f"{len([v for v in self.bridge.victims if v.found])} total found."
                ),
                detections=detections,
            )
        return None

    def on_demand(self, step: int) -> EdgeReport:
        detections, novel = self._scan()
        if self.budget.request():
            frame_ref = f"snapshot-ep-{self.bridge.scenario}-step-{step}-{self.budget.used}"
        else:
            frame_ref = None
        summary = (
            f"On-demand scan: {len(detections)} in view "
            f"({len(novel)} new). Snapshot budget {self.budget.used}/"
            f"{self.budget.max_snapshots}."
        )
        if frame_ref is None:
            summary += " Budget exhausted: no frame attached, report only."
        return EdgeReport(
            trigger="requested", step=step, summary=summary,
            detections=detections, frame_ref=frame_ref,
        )
