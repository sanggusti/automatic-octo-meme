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
