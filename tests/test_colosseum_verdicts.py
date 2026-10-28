"""Colosseum bridge (fake client) + verdict harness tests. No server needed."""

import io

from PIL import Image

from dmb.scenarios import build_samples
from dmb.sim.bridge import MockBridge
from dmb.sim.colosseum_bridge import ColosseumBridge
from dmb.verdicts import compare_backends


class _Vec:
    def __init__(self, x, y, z):
        self.x_val, self.y_val, self.z_val = x, y, z


class _Pose:
    def __init__(self, x, y, z):
        self.position = _Vec(x, y, z)


class _State:
    def __init__(self, landed):
        self.landed_state = "Landed" if landed else "Flying"


class _Future:
    def __init__(self, fn=None):
        self._fn = fn

    def join(self):
        if self._fn:
            self._fn()


class FakeMultirotorClient:
    """Scriptable stand-in for airsim.MultirotorClient."""

    def __init__(self):
        self.pose = [0.0, 0.0, 0.0]
        self.landed = True
        self.armed = False
        self.calls: list[str] = []

    def confirmConnection(self):
        self.calls.append("confirm")

    def reset(self):
        self.calls.append("reset")
        self.pose = [0.0, 0.0, 0.0]
        self.landed = True

    def enableApiControl(self, flag, vehicle=""):
        self.calls.append(f"api={flag}")

    def armDisarm(self, arm, vehicle=""):
        self.calls.append(f"arm={arm}")
        self.armed = arm
        return True

    def simGetVehiclePose(self, vehicle=""):
        return _Pose(*self.pose)

    def getMultirotorState(self, vehicle=""):
        return _State(self.landed)

    def takeoffAsync(self, timeout_sec=20, vehicle_name=""):
        def go():
            self.landed = False
            self.pose[2] -= 3.0

        return _Future(go)

    def moveToPositionAsync(self, x, y, z, velocity, timeout_sec=3e38, vehicle_name=""):
        def go():
            self.pose = [x, y, z]

        return _Future(go)

    def hoverAsync(self, vehicle_name=""):
        return _Future()

    def landAsync(self, timeout_sec=60, vehicle_name=""):
        def go():
            self.landed = True
            self.pose[2] = 0.0

        return _Future(go)

    def goHomeAsync(self, timeout_sec=3e38, vehicle_name=""):
        def go():
            self.pose = [0.0, 0.0, 0.0]
            self.landed = True

        return _Future(go)

    def simGetImages(self, requests, vehicle=""):
        buf = io.BytesIO()
        Image.new("RGB", (32, 32), (9, 9, 9)).save(buf, format="PNG")
        return [type("Resp", (), {"image_data_uint8": buf.getvalue()})()]


def _metadata():
    return dict(build_samples("forest_fire", seeds=[1])[0].metadata)


def test_colosseum_flight_lifecycle():
    bridge = ColosseumBridge(client=FakeMultirotorClient(), cell_m=5.0)
    bridge.reset(_metadata())
    assert "Armed" in bridge.act("arm", {}).text
    assert bridge.act("takeoff", {"altitude_m": 5}).text.startswith("Takeoff")
    assert bridge.drone.airborne
    assert bridge.drone.altitude_m == 5.0
    obs = bridge.act("goto", {"x": 2, "y": 2})
    assert "(2, 2)" in obs.text
    assert "Landed" in bridge.act("land", {}).text
    assert not bridge.drone.airborne
    bridge.close()


def test_colosseum_capture_frame_native_bytes():
    import types

    bridge = ColosseumBridge(client=FakeMultirotorClient())
    bridge.reset(_metadata())
    bridge._airsim = types.SimpleNamespace(
        ImageRequest=lambda *args: ("req", args), ImageType=types.SimpleNamespace(Scene=0)
    )
    png = bridge.capture_frame("n1")
    bridge.close()
    assert png is not None
    img = Image.open(io.BytesIO(png))
    img.verify()
    assert img.size == (32, 32)  # fake native bytes, not the rendered map


def _short_rollout(bridge):
    bridge.act("arm", {})
    bridge.act("takeoff", {"altitude_m": 10})
    bridge.act("goto", {"x": 2, "y": 2})
    bridge.act("land", {})


def test_verdict_mock_vs_mock_matches():
    metas = [dict(s.metadata) for s in build_samples("forest_fire", seeds=[1, 2])]
    report = compare_backends(
        MockBridge.from_metadata, MockBridge.from_metadata, metas, _short_rollout
    )
    assert len(report) == 2
    assert all(entry["match"] for entry in report), report
