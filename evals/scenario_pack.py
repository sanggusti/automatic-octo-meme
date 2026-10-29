"""Scenario-pack sweep: all six disasters x fixed seeds (baseline table)."""

from inspect_ai import Task, task

from dmb.scenarios import build_samples, list_scenarios
from dmb.scorers.mission import mission_score
from dmb.solvers.mission import drone_mission

PACK_SEEDS = [1, 2, 3]


@task
def scenario_pack():
    dataset = []
    for scenario in list_scenarios():
        dataset.extend(build_samples(scenario, seeds=PACK_SEEDS))
    return Task(
        dataset=dataset,
        solver=[drone_mission()],
        scorer=mission_score(),
    )
