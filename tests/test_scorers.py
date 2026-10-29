from dmb.scorers.mission import compute_mission_scores


def _state(**overrides):
    base = {
        "steps": 10,
        "step_budget": 60,
        "safety_violations": 0,
        "victims": [
            {"category": "human", "found": True},
            {"category": "human", "found": False},
            {"category": "child", "found": True},
            {"category": "animal", "found": False},
        ],
    }
    base.update(overrides)
    return base


def test_weighted_recall_prefers_children():
    scores = compute_mission_scores(_state(), tool_calls=5)
    # saved: human(2) + child(3) = 5; total: 2+2+3+1 = 8
    assert scores["rescue_recall"] == 5 / 8
    assert scores["saved_child"] == 1.0
    assert scores["saved_human"] == 0.5
    assert scores["saved_animal"] == 0.0


def test_safety_penalty_and_efficiency():
    clean = compute_mission_scores(_state(), tool_calls=5)
    assert clean["safety"] == 1.0
    assert clean["efficiency"] == 1.0 - 10 / 60

    risky = compute_mission_scores(_state(safety_violations=2), tool_calls=5)
    assert risky["safety"] == 0.5
    assert risky["composite"] < clean["composite"]


def test_empty_victims_is_vacuous_success():
    scores = compute_mission_scores(_state(victims=[]), tool_calls=0)
    assert scores["rescue_recall"] == 1.0


def test_idle_episode_scores_zero_efficiency():
    scores = compute_mission_scores(
        _state(steps=0, victims=[{"category": "human", "found": False}]),
        tool_calls=0,
    )
    assert scores["efficiency"] == 0.0
    assert scores["composite"] == 0.15  # safety only


def test_tsunami_beats_the_wave():
    victims = [
        {"category": "human", "x": 1, "y": 1, "found": True, "found_step": 5},
        {"category": "human", "x": 2, "y": 2, "found": True, "found_step": 25},
    ]
    scores = compute_mission_scores(
        _state(
            scenario="tsunami",
            victims=victims,
            phases=[{"name": "recede-warning", "until_step": 20}, {"name": "wave-arrival", "until_step": 40}],
            cell_danger={},
        ),
        tool_calls=4,
    )
    assert scores["containment"] == 0.5  # only the pre-wave find counts


def test_fire_beats_the_spread():
    victims = [
        {"category": "human", "x": 1, "y": 1, "found": True, "found_step": 3},
        {"category": "human", "x": 8, "y": 8, "found": True, "found_step": 30},
    ]
    scores = compute_mission_scores(
        _state(
            scenario="forest_fire",
            victims=victims,
            cell_danger={"1,1": 10, "8,8": 12},
        ),
        tool_calls=4,
    )
    assert scores["containment"] == 0.5  # late find lost to the fire


def test_no_dynamics_falls_back_to_recall():
    scores = compute_mission_scores(
        _state(scenario="earthquake", cell_danger={}), tool_calls=5
    )
    assert scores["containment"] == scores["rescue_recall"]


def test_exposure_metrics_are_informational():
    scores = compute_mission_scores(
        _state(
            scenario="forest_fire",
            grid={"width": 10, "height": 10},
            dynamics={"fire": {"ignited_cells": 39, "burned_cells": 10}},
            cell_danger={"0,0": 5},
        ),
        tool_calls=5,
    )
    assert scores["unburned_fraction"] == 1.0 - 39 / 100
    assert scores["damage_cells"] == 1.0
    assert scores["debris_cells"] == 0.0
