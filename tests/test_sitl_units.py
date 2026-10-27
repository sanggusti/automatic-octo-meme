"""Pure unit tests for SITL bridge helpers (no Docker needed)."""

import pytest

from dmb.sim.bridge import _offset_latlon, _offset_meters
from dmb.solvers.mission import _bridge_for_backend
from dmb.sim.bridge import GazeboSITLBridge, MockBridge


def test_latlon_offset_roundtrip():
    lat0, lon0 = -35.3632621, 149.1652374
    for east, north in [(0, 0), (25, 0), (0, 45), (-12.5, 33.3), (50, 50)]:
        lat, lon = _offset_latlon(lat0, lon0, east, north)
        east2, north2 = _offset_meters(lat0, lon0, lat, lon)
        assert abs(east2 - east) < 1e-6
        assert abs(north2 - north) < 1e-6


def test_latlon_offset_scale():
    # ~111 m per 0.001 deg latitude
    lat, _ = _offset_latlon(0.0, 0.0, 0.0, 111.195)
    assert abs(lat - 0.001) < 1e-5


def test_backend_selection():
    assert _bridge_for_backend("mock") is MockBridge
    assert _bridge_for_backend("gazebo-sitl") is GazeboSITLBridge
    with pytest.raises(ValueError):
        _bridge_for_backend("colosseum")  # not via this switch yet
