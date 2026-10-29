"""Track 2 backend: Colosseum/Unreal on the operator GPU workstation.

Same SimBridge contract as mock/SITL: grid victim/scoring semantics are
inherited from MockBridge; flight goes through Colosseum's Python client
(msgpack-rpc, default 127.0.0.1:41451). Grid maps to local NED metres
around the spawn pose (east = +x, north = +y).

Install the client from the Colosseum repo (see docs/track2-runbook.md);
import is lazy so other backends never need it. Live verification happens
on the workstation (issue #6); this module ships with fake-client tests.
"""

from __future__ import annotations

import math
import time

from dmb.sim.bridge import MockBridge


def _require_airsim():
    try:
        import airsim  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "ColosseumBridge needs the Colosseum PythonClient: "
            "see docs/track2-runbook.md"
        ) from exc
    return airsim


class ColosseumBridge(MockBridge):
    # MultirotorClient API surface: multicopters only.
    SUPPORTED_VEHICLE_CLASSES = frozenset({"multicopter"})

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 41451,
        vehicle_name: str = "",
        cell_m: float = 5.0,
        velocity: float = 5.0,
        client=None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.host = host
        self.port = port
        self.vehicle_name = vehicle_name
        self.cell_m = cell_m
        self.velocity = velocity
        self._client = client
        self._airsim = None
        self._home_ned: tuple[float, float, float] | None = None

    # -- lifecycle ------------------------------------------------------
    def reset(self, metadata: dict) -> object:
        obs = super().reset(metadata)
        if self._client is None:
            self._airsim = _require_airsim()
            self._client = self._airsim.MultirotorClient(ip=self.host, port=self.port)
            self._client.confirmConnection()
        self._client.reset()
        self._client.enableApiControl(True, self.vehicle_name)
        pose = self._client.simGetVehiclePose(self.vehicle_name)
        p = pose.position
        self._home_ned = (p.x_val, p.y_val, p.z_val)
        self._sync_from_pose()
        return obs

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.armDisarm(False, self.vehicle_name)
                self._client.enableApiControl(False, self.vehicle_name)
            except Exception:
                pass
            self._client = None

    # -- mapping helpers (NED metres <-> grid) ---------------------------
    def _grid_to_ned(self, x: int, y: int) -> tuple[float, float]:
        assert self._home_ned is not None
        hx, hy, _ = self._home_ned
        return hx + y * self.cell_m, hy + x * self.cell_m

    def _ned_to_grid(self, north: float, east: float) -> tuple[int, int]:
        assert self._home_ned is not None
        hx, hy, _ = self._home_ned
        return (
            max(0, min(self.width - 1, int(round((east - hy) / self.cell_m)))),
            max(0, min(self.height - 1, int(round((north - hx) / self.cell_m)))),
        )

    def _sync_from_pose(self) -> None:
        assert self._client is not None
        pose = self._client.simGetVehiclePose(self.vehicle_name)
        p = pose.position
        assert self._home_ned is not None
        gx, gy = self._ned_to_grid(p.x_val, p.y_val)
        self.drone.x, self.drone.y = gx, gy
        self.drone.altitude_m = max(0.0, self._home_ned[2] - p.z_val)
        state = self._client.getMultirotorState(self.vehicle_name)
        self.drone.airborne = str(state.landed_state) != "Landed"

    # -- primitives ------------------------------------------------------
    def arm(self):
        assert self._client is not None
        self._client.enableApiControl(True, self.vehicle_name)
        ok = bool(self._client.armDisarm(True, self.vehicle_name))
        self.drone.armed = ok
        if not ok:
            return self._observe("Refused: armDisarm rejected.")
        return self._observe("Armed (API control).")

    def takeoff(self, altitude_m: float):
        assert self._client is not None
        if not self.drone.armed:
            return self._observe("Refused: arm before takeoff.")
        if altitude_m <= 0:
            return self._observe("Refused: altitude must be positive.")
        self._client.takeoffAsync(vehicle_name=self.vehicle_name).join()
        assert self._home_ned is not None
        target_z = self._home_ned[2] - altitude_m
        pose = self._client.simGetVehiclePose(self.vehicle_name).position
        self._client.moveToPositionAsync(
            pose.x_val, pose.y_val, target_z, self.velocity,
            vehicle_name=self.vehicle_name,
        ).join()
        self.drone.airborne = True
        self._tick()
        self._sync_from_telemetry()
        return self._observe(f"Takeoff to {self.drone.altitude_m:.1f} m.")

    def goto(self, x: int, y: int):
        assert self._client is not None
        if not self.drone.airborne:
            return self._observe("Refused: not airborne.")
        tx = max(0, min(self.width - 1, x))
        ty = max(0, min(self.height - 1, y))
        north, east = self._grid_to_ned(tx, ty)
        assert self._home_ned is not None
        z = self._home_ned[2] - max(3.0, self.drone.altitude_m)
        self._client.moveToPositionAsync(
            north, east, z, self.velocity, vehicle_name=self.vehicle_name
        ).join()
        self._tick()
        self._sync_from_telemetry()
        if self._in_hazard(self.drone.x, self.drone.y):
            self.safety_violations += 1
            return self._observe(
                f"Moved to ({self.drone.x}, {self.drone.y}). WARNING: hazard zone."
            )
        return self._observe(f"Arrived ({self.drone.x}, {self.drone.y}).")

    def loiter(self, seconds: int = 5):
        assert self._client is not None
        if not self.drone.airborne:
            return self._observe("Refused: not airborne.")
        self._client.hoverAsync(vehicle_name=self.vehicle_name).join()
        time.sleep(min(seconds, 30))
        self._tick()
        self._sync_from_telemetry()
        return self._observe(f"Loitered at ({self.drone.x}, {self.drone.y}).")

    def land(self):
        assert self._client is not None
        self._client.landAsync(vehicle_name=self.vehicle_name).join()
        self.drone.airborne = False
        self.drone.altitude_m = 0.0
        self._tick()
        self._sync_from_telemetry()
        return self._observe(f"Landed at ({self.drone.x}, {self.drone.y}).")

    def rtl(self):
        assert self._client is not None
        self._client.goHomeAsync(vehicle_name=self.vehicle_name).join()
        self.drone.airborne = False
        self.drone.altitude_m = 0.0
        self._tick()
        self._sync_from_telemetry()
        return self._observe("Returned to launch and landed.")

    def _sync_from_telemetry(self) -> None:
        self._sync_from_pose()
        # MultirotorState carries no battery; mock-style drain keeps the
        # metric defined until a power model lands.
        self.drone.battery_pct = max(0.0, 100.0 - self.steps * self.battery_drain)

    def capture_frame(self, ref: str) -> bytes | None:
        """Native frame via simGetImages; rendered fallback on failure."""
        assert self._client is not None
        try:
            airsim = self._airsim or _require_airsim()
            requests = [
                airsim.ImageRequest("0", airsim.ImageType.Scene, False, False)
            ]
            responses = self._client.simGetImages(requests, self.vehicle_name)
            if responses and responses[0].image_data_uint8:
                return bytes(responses[0].image_data_uint8)
        except Exception:
            pass
        return super().capture_frame(ref)
