"""Deterministic mission scorers.

The pure :func:`compute_mission_scores` derives the metric vector from final
sim state; the inspect-ai scorer wrapper reads that state from the sample
store (written by the solver) plus transcript statistics.
"""

from __future__ import annotations

from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import TaskState

from dmb.watch import record_score

# Rescue priority weights. Children first, then humans, then animals.
VICTIM_WEIGHTS = {"child": 3.0, "human": 2.0, "animal": 1.0}


def compute_mission_scores(final_state: dict, tool_calls: int) -> dict[str, float]:
    victims = final_state.get("victims", [])
    total_weight = sum(VICTIM_WEIGHTS.get(v.get("category", ""), 0.0) for v in victims)
    saved_weight = sum(
        VICTIM_WEIGHTS.get(v.get("category", ""), 0.0)
        for v in victims
        if v.get("found")
    )
    rescue_recall = (saved_weight / total_weight) if total_weight else 1.0

    per_category: dict[str, float] = {}
    for category in VICTIM_WEIGHTS:
        group = [v for v in victims if v.get("category") == category]
        per_category[f"saved_{category}"] = (
            sum(1 for v in group if v.get("found")) / len(group) if group else 1.0
        )

    steps = float(final_state.get("steps", 0) or 0)
    budget = float(final_state.get("step_budget", 0) or 0)
    found_any = any(v.get("found") for v in victims)
    # Idle-episode fix (#4): doing nothing scores efficiency 0, not 1.
    efficiency = (max(0.0, 1.0 - (steps / budget)) if budget else 0.0) if found_any else 0.0
    violations = int(final_state.get("safety_violations", 0))
    safety = 1.0 if violations == 0 else max(0.0, 1.0 - 0.25 * violations)

    beat = _containment_beat(final_state, victims, total_weight)
    containment = max(0.0, min(1.0, beat * safety))

    composite = 0.5 * rescue_recall + 0.2 * containment + 0.15 * efficiency + 0.15 * safety
    return {
        **per_category,
        "rescue_recall": rescue_recall,
        "containment": containment,
        "efficiency": efficiency,
        "safety": safety,
        "tool_calls": float(tool_calls),
        "found_any": 1.0 if found_any else 0.0,
        "first_find_step": float(final_state.get("first_find_step", -1)),
        "coverage": float(final_state.get("coverage", 0.0)),
        **_exposure_metrics(final_state, victims),
        "composite": composite,
    }


def _cell_beat(victims: list, total_weight: float, cell_danger: dict) -> float:
    """Weighted fraction found before their cell became dangerous."""
    beaten = 0.0
    for v in victims:
        if not v.get("found"):
            continue
        found_step = v.get("found_step", -1)
        if found_step < 0:
            beaten += VICTIM_WEIGHTS.get(v.get("category", ""), 0.0)
            continue
        danger = cell_danger.get(f"{v.get('x')},{v.get('y')}", float("inf"))
        if found_step <= danger:
            beaten += VICTIM_WEIGHTS.get(v.get("category", ""), 0.0)
    return (beaten / total_weight) if total_weight else 1.0


def _containment_beat(final_state: dict, victims: list, total_weight: float) -> float:
    """Per-kind containment beat (#4), before the safety multiplier.

    - tsunami: beat-the-wave — found before the wave-arrival phase starts.
    - fire / water / terrain kinds: beat-the-spread on cell danger steps.
    - no dynamics (earthquake): every danger is infinite, reducing to recall.
    """
    if final_state.get("scenario") == "tsunami":
        # Beat-the-wave: found before the wave-arrival phase STARTS, i.e.
        # before the previous phase's until_step.
        deadline = None
        prev_until = 0
        for phase in final_state.get("phases", []):
            if phase.get("name") == "wave-arrival":
                deadline = prev_until
                break
            prev_until = int(phase.get("until_step", 0))
        if deadline is not None:
            beaten = sum(
                VICTIM_WEIGHTS.get(v.get("category", ""), 0.0)
                for v in victims
                if v.get("found") and 0 <= v.get("found_step", -1) < deadline
            )
            return (beaten / total_weight) if total_weight else 1.0
    return _cell_beat(victims, total_weight, final_state.get("cell_danger", {}))


def _exposure_metrics(final_state: dict, victims: list) -> dict[str, float]:
    """Informational (not in composite): how big the disaster got."""
    grid = final_state.get("grid", {})
    cells = max(1, int(grid.get("width", 10)) * int(grid.get("height", 10)))
    dynamics = final_state.get("dynamics", {})
    fire = dynamics.get("fire", {})
    water = dynamics.get("water", {})
    terrain = dynamics.get("terrain", {})
    return {
        "damage_cells": float(len(final_state.get("cell_danger", {}))),
        "unburned_fraction": 1.0 - fire.get("ignited_cells", 0) / cells,
        "unflooded_fraction": 1.0 - water.get("flooded_cells", 0) / cells,
        "debris_cells": float(terrain.get("debris_cells", 0)),
        "buried_victims": float(
            sum(1 for v in victims if v.get("mobility") == "buried")
        ),
    }


def _count_tool_calls(state: TaskState) -> int:
    count = 0
    for message in state.messages:
        calls = getattr(message, "tool_calls", None)
        if calls:
            count += len(calls)
    return count


@scorer(metrics=[mean()])
def mission_score() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        sim_state = state.store.get("sim_state", {})
        if not sim_state:
            return Score(
                value=0.0,
                explanation="No sim state recorded; solver did not run the mission.",
            )
        breakdown = compute_mission_scores(sim_state, _count_tool_calls(state))
        record_score(str(state.sample_id), breakdown)
        return Score(
            value=breakdown["composite"],
            answer=str(breakdown),
            explanation=(
                f"recall={breakdown['rescue_recall']:.2f} "
                f"containment={breakdown['containment']:.2f} "
                f"efficiency={breakdown['efficiency']:.2f} "
                f"safety={breakdown['safety']:.2f}"
            ),
            metadata=breakdown,
        )

    return score
