"""Scenario-pack sweep: base disasters x fixed seeds (baseline table).

Large variants (scenarios with a ``variant_of`` key) are excluded: they run
via their own tasks so the published pack table stays comparable.
"""

from inspect_ai import Task, task

from dmb.scenarios import build_samples, list_scenarios, load_scenario
from dmb.scorers.mission import mission_score
from dmb.solvers.mission import drone_mission

PACK_SEEDS = [1, 2, 3]


def pack_scenarios() -> list[str]:
    """Base disasters only; ``*_large`` variants run via their own tasks."""
    return [n for n in list_scenarios() if "variant_of" not in load_scenario(n).raw]


@task
def scenario_pack():
    dataset = []
    for scenario in pack_scenarios():
        dataset.extend(build_samples(scenario, seeds=PACK_SEEDS))
    return Task(
        dataset=dataset,
        solver=[drone_mission()],
        scorer=mission_score(),
    )
