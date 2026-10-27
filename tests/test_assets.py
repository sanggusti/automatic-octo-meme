import pytest

from dmb.sim.assets import list_drone_specs, load_drone_spec


def test_specs_load_and_report_capabilities():
    names = list_drone_specs()
    assert "quad_iris_class" in names
    quad = load_drone_spec("quad_iris_class")
    assert quad.supports("guided_takeoff")
    assert quad.supports("non_gps_nav")
    assert not quad.supports("auto_mission")
    assert "forward-camera" in quad.sensors


def test_missing_spec_raises():
    with pytest.raises(OSError):
        load_drone_spec("does-not-exist")
