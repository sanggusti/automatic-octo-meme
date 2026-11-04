"""Tests for the lush forest world builder."""

import json
import math
import xml.etree.ElementTree as ET

from assets.vegetation.build_world import MIN_SPACING_M, build


def test_build_world_peat(tmp_path):
    stats = build("firms_peat_kalimantan_01", 7, tmp_path / "world", 400)
    out = tmp_path / "world"
    assert stats["trees"] == 400
    assert stats["emitters"] == 6  # 2 ignitions x smoke+flame+haze
    assert stats["species"] == {"oak-tree": 400}

    root = ET.fromstring((out / "world.sdf").read_text())
    includes = root.findall(".//include")
    names = [i.findtext("name") for i in includes]
    assert len(names) == len(set(names)), "instance names must be unique"
    uris = {i.findtext("uri") for i in includes}
    assert uris <= {
        "model://oak-tree",
        "model://smoke-generator",
        "model://flame_column",
        "model://fog-emitter-dense",
    }

    placements = json.loads((out / "placements.json").read_text())
    trees = placements["trees"]
    for t in trees:
        for qx, qy, r in placements["clearings"]:
            assert math.dist((t["x"], t["y"]), (qx, qy)) >= r
    sample = trees[::20]
    for i, a in enumerate(sample):
        for b in sample[i + 1 :]:
            assert (
                math.dist((a["x"], a["y"]), (b["x"], b["y"])) >= MIN_SPACING_M
            )

    flame = (out / "models" / "flame_column" / "model.sdf").read_text()
    assert "<diffuse>1.0 0.45 0.1</diffuse>" in flame
    staged = (out / "models" / "smoke-generator" / "model.sdf").read_text()
    assert "<particle_emitter" in staged and "<plugin" not in staged
    assert "ignition-gazebo" not in (out / "world.sdf").read_text()

    # SDF requires names on collision/visual (gz rejects unnamed).
    sdf_text = (out / "world.sdf").read_text()
    assert "<collision>" not in sdf_text and "<visual>" not in sdf_text


def test_build_world_deterministic(tmp_path):
    a = build("firms_peat_sumatra_01", 3, tmp_path / "a", 200)
    b = build("firms_peat_sumatra_01", 3, tmp_path / "b", 200)
    assert a == b
    assert (tmp_path / "a" / "world.sdf").read_bytes() == (
        tmp_path / "b" / "world.sdf"
    ).read_bytes()
