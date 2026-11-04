"""Tests for the lush forest world builder."""

import json
import math
import xml.etree.ElementTree as ET

from assets.vegetation.build_world import MIN_SPACING_M, build


def test_build_world_peat(tmp_path):
    stats = build("firms_peat_kalimantan_01", 7, tmp_path / "world", 400)
    out = tmp_path / "world"
    assert stats["trees"] == 400
    assert stats["emitters"] == 6  # 2 ignitions x (firebed + smoke + haze)
    assert stats["victim_actors"] == 3  # seed-7 draw: 3 human, 0 child
    assert stats["species"] == {"oak-tree": 400}

    root = ET.fromstring((out / "world.sdf").read_text())
    includes = root.findall(".//include")
    names = [i.findtext("name") for i in includes]
    assert len(names) == len(set(names)), "instance names must be unique"
    uris = {i.findtext("uri") for i in includes}
    assert uris <= {
        "model://oak-tree",
        "model://smoke-generator",
        "model://flame_bed",
        "model://fog-emitter-dense",
        "model://standing-person",
        "model://male-visitor",
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

    flame = (out / "models" / "flame_bed" / "model.sdf").read_text()
    assert "<diffuse>1.0 0.45 0.1</diffuse>" in flame
    assert 'type="box"' in flame
    staged = (out / "models" / "smoke-generator" / "model.sdf").read_text()
    assert "<particle_emitter" in staged and "<plugin" not in staged
    assert "ignition-gazebo" not in (out / "world.sdf").read_text()

    # SDF requires names on collision/visual (gz rejects unnamed).
    sdf_text = (out / "world.sdf").read_text()
    assert "<collision>" not in sdf_text and "<visual>" not in sdf_text

    # Grass-soil ground: real aerial albedo + scorch decals per ignition.
    assert "model://ground_tex/materials/textures/aerial_grass_rock.jpg" in sdf_text
    assert sdf_text.count('model name="scorch_') == 2
    assert "burned_ground_01.jpg" in sdf_text
    gtex = out / "models" / "ground_tex" / "materials" / "textures"
    assert (gtex / "aerial_grass_rock.jpg").exists()
    assert (gtex / "burned_ground_01.jpg").exists()
    assert sdf_text.count("<uri>model://flame_bed</uri>") == 2
    assert sdf_text.count("<uri>model://smoke-generator</uri>") == 2
    assert "model://flame_column" not in sdf_text  # point flames retired
    assert "<emissive>" not in sdf_text  # ember blowout retired with it
    # People match the eval draw (seed 7: humans at 19/50, 83/6, 9/105).
    assert sdf_text.count("<uri>model://standing-person</uri>") == 2
    assert sdf_text.count("<uri>model://male-visitor</uri>") == 1
    assert "95.0 250.0 0" in sdf_text  # human (19,50) x5 m


def test_build_world_deterministic(tmp_path):
    a = build("firms_peat_sumatra_01", 3, tmp_path / "a", 200)
    b = build("firms_peat_sumatra_01", 3, tmp_path / "b", 200)
    assert a == b
    assert (tmp_path / "a" / "world.sdf").read_bytes() == (
        tmp_path / "b" / "world.sdf"
    ).read_bytes()
