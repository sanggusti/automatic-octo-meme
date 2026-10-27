"""Deterministic mission scorers.

The pure :func:`compute_mission_scores` derives the metric vector from final
sim state; the inspect-ai scorer wrapper reads that state from the sample
store (written by the solver) plus transcript statistics.
"""

from __future__ import annotations

from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import TaskState

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
    efficiency = max(0.0, 1.0 - (steps / budget)) if budget else 0.0
    violations = int(final_state.get("safety_violations", 0))
    safety = 1.0 if violations == 0 else max(0.0, 1.0 - 0.25 * violations)

    # Damage containment proxy v0: coverage of the incident area without
    # violations. Refined per scenario once hazard dynamics exist.
    containment = max(0.0, min(1.0, rescue_recall * safety))

    composite = 0.5 * rescue_recall + 0.2 * containment + 0.15 * efficiency + 0.15 * safety
    return {
        **per_category,
        "rescue_recall": rescue_recall,
        "containment": containment,
        "efficiency": efficiency,
        "safety": safety,
        "tool_calls": float(tool_calls),
        "composite": composite,
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
