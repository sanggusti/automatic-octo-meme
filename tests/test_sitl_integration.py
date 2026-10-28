"""Live SITL integration tests. Need Docker + built image; opt-in only.

Run: DMB_RUN_SITL_TESTS=1 .venv/bin/python -m pytest tests/test_sitl_integration.py
"""

import os
import shutil
from concurrent.futures import ThreadPoolExecutor

import pytest

from dmb.scenarios import build_samples
from dmb.sim.bridge import GazeboSITLBridge

needs_sitl = pytest.mark.skipif(
    os.environ.get("DMB_RUN_SITL_TESTS") != "1" or shutil.which("docker") is None,
    reason="SITL integration tests need DMB_RUN_SITL_TESTS=1 and docker",
)


def _scripted_flight(seed: int = 1) -> dict:
    meta = build_samples("forest_fire", seeds=[seed])[0].metadata
    bridge = GazeboSITLBridge()
    try:
        bridge.reset(dict(meta))
        assert "Armed" in bridge.act("arm", {}).text
        assert "Takeoff" in bridge.act("takeoff", {"altitude_m": 5}).text
        assert bridge.drone.airborne
        png = bridge.capture_frame("probe")
        assert png is not None and png[:8] == b"\x89PNG\r\n\x1a\n"
        obs = bridge.act("goto", {"x": 2, "y": 2})
        assert "Moved" in obs.text or "Arrived" in obs.text or "En route" in obs.text
        assert "Landed" in bridge.act("land", {}).text
        assert not bridge.drone.airborne
        return {"container": bridge.container_id, "state": bridge.get_state()}
    finally:
        bridge.close()


@needs_sitl
def test_scripted_sitl_flight():
    result = _scripted_flight()
    assert result["container"]
    assert result["state"]["steps"] == 3  # takeoff, goto, land (arm is free)


@needs_sitl
def test_parallel_workers_are_isolated():
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(_scripted_flight, [1, 2]))
    assert first["container"] != second["container"]
    assert first["state"]["seed"] == 1
    assert second["state"]["seed"] == 2


def _short_rollout(bridge):
    bridge.act("arm", {})
    bridge.act("takeoff", {"altitude_m": 10})
    bridge.act("goto", {"x": 2, "y": 2})
    bridge.act("land", {})


@needs_sitl
def test_verdict_mock_vs_sitl_short_rollout():
    from dmb.sim.bridge import MockBridge
    from dmb.verdicts import compare_backends

    from dmb.sim.bridge import GazeboSITLBridge

    metas = [dict(s.metadata) for s in build_samples("forest_fire", seeds=[1])]
    report = compare_backends(
        MockBridge.from_metadata, GazeboSITLBridge.from_metadata, metas, _short_rollout
    )
    assert len(report) == 1
    assert report[0]["match"], report[0]["diffs"]
