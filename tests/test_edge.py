from dmb.perception.edge import FrameBudget, StubEdgePerception, TriggerConfig
from dmb.sim.bridge import MockBridge


def _bridge():
    return MockBridge.from_metadata(
        {
            "scenario": "forest_fire",
            "seed": 1,
            "grid": {"width": 10, "height": 10},
            "victim_placements": [{"category": "human", "x": 1, "y": 0}],
            "hazards": [],
        }
    )


def test_novelty_report_fires_once_per_victim():
    bridge = _bridge()
    edge = StubEdgePerception(bridge, TriggerConfig(), FrameBudget(8))
    bridge.act("arm", {})
    assert edge.on_step(0) is None  # grounded: no detections
    bridge.act("takeoff", {"altitude_m": 10})
    report = edge.on_step(1)
    assert report is not None and report.trigger == "novelty"
    assert bridge.get_state()["victims"][0]["found"] is True
    # second scan: already known, and heartbeat interval not reached
    assert edge.on_step(2) is None


def test_snapshot_budget_is_enforced():
    bridge = _bridge()
    edge = StubEdgePerception(bridge, TriggerConfig(), FrameBudget(1))
    assert edge.on_demand(0).frame_ref is not None
    assert edge.on_demand(1).frame_ref is None
