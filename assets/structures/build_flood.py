#!/usr/bin/env python3
"""Build flood_hard / flash_flood_hard / tsunami_hard world SDFs.

Three water worlds from real Fuel/P-D assets only (poses generated):

- flood_hard: 300 m river town under ~1.1 m of murky water; house and
  shop rows flooded to the sills, a school shelter + marina dock on a
  high-ground pad, rescue boats, channel buoys, submerged cars, drift
  debris, and a rain-veiled overcast sky.
- flash_flood_hard: 240x320 m valley settlement on a rain-swollen
  river; a truss bridge as the only high crossing, sand banks, flank
  forest + boulders, storm rain, one rescue boat working the channel.
- tsunami_hard: 300 m coastal strip; sand flat + surf, a wooden
  pier and harbor dock, port warehouse, scoured
  town with collapsed homes and a debris field, beached boats, and a
  relief post on the high ground.

Documented adaptations (same class as the quake house PBR fix):
staged rescue-randy-sitting drops a nested remote-Fuel include
(offline builds must not phone home), staged
school/ambulance/truss-bridge/pier gain PBR albedo blocks (their
mesh-internal texture refs fail under ogre2), rain is a downward box
emitter staged from smoke-generator, and floodwater is a thin
translucent PBR box
(Polyhaven ships no water diffuse; Flood Ill aerials show
mirror-calm gray water, matched with a diffuse gray PBR (high
metalness mirrors the blue default sky under ogre2, 2026-11-05 probe).

Usage: python assets/structures/build_flood.py flood_hard
         --seed 7 --out /tmp/flood-town
"""

from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO))

from assets.structures.build_quake import stage_houses  # noqa: E402
from assets.vegetation.build_world import (  # noqa: E402
    MODELS_DIR,
    TEXTURES_DIR,
    _legacy_emitter_block,
    eval_victims,
    load_scenario,
)

CELL_M = 5.0
GROUND_TEX = (
    "asphalt_02.jpg",
    "brown_mud_02.jpg",
    "aerial_grass_rock.jpg",
    "sand_01.jpg",
)

WATER_MAT = """\
          <material>
            <ambient>0.40 0.46 0.48 1</ambient>
            <diffuse>0.42 0.48 0.50 0.85</diffuse>
            <specular>0.2 0.22 0.24 1</specular>
            <pbr>
              <metal>
                <metalness>0.1</metalness>
                <roughness>0.55</roughness>
              </metal>
            </pbr>
          </material>"""

OVERWASH_MAT = """\
          <material>
            <ambient>0.32 0.36 0.37 1</ambient>
            <diffuse>0.34 0.39 0.40 0.60</diffuse>
            <specular>0.15 0.16 0.17 1</specular>
            <pbr>
              <metal>
                <metalness>0.1</metalness>
                <roughness>0.6</roughness>
              </metal>
            </pbr>
          </material>"""

GROUND_MAT = """\
          <material>
            <ambient>0.7 0.7 0.7 1</ambient>
            <diffuse>1.0 0.98 0.94 1</diffuse>
            <pbr>
              <metal>
                <albedo_map>model://ground_tex/materials/textures/{tex}</albedo_map>
              </metal>
            </pbr>
          </material>"""


def stage_flood_common(out_models: Path) -> None:
    """Shared staging: houses, ground_tex, randy, PBR fixes, rain."""
    stage_houses(out_models)
    missing = [n for n in GROUND_TEX if not (TEXTURES_DIR / n).exists()]
    if missing:
        raise SystemExit(
            f"missing ground textures {missing}; run "
            "python assets/textures/fetch_textures.py first"
        )
    gtex = out_models / "ground_tex"
    if gtex.exists():
        shutil.rmtree(gtex)
    (gtex / "materials" / "textures").mkdir(parents=True)
    for n in GROUND_TEX:
        shutil.copy(TEXTURES_DIR / n, gtex / "materials" / "textures" / n)
    (gtex / "model.config").write_text(
        '<?xml version="1.0"?>\n<model>\n'
        "  <name>ground_tex</name>\n"
        "  <version>1.0</version>\n"
        '  <sdf version="1.6">model.sdf</sdf>\n'
        "  <description>Pinned CC0 ground textures (URI host only)."
        "</description>\n</model>\n"
    )
    (gtex / "model.sdf").write_text(
        '<?xml version="1.0" ?>\n<sdf version="1.6">\n'
        '  <model name="ground_tex">\n'
        "    <static>true</static>\n"
        '    <link name="link"/>\n'
        "  </model>\n</sdf>\n"
    )
    stage_randy(out_models)
    stage_school_bus(out_models)
    stage_rain(out_models)


def stage_school_bus(out_models: Path) -> None:
    """Staged school/ambulance/bridge with PBR albedo blocks.

    These SDFs carry no <material> at all and their mesh-internal
    texture refs (bare *_diffuse.jpg / ambulance.png) fail to resolve
    under ogre2 (render log, 2026-11-05) — same black-mesh class as
    the quake houses. Inject diffuse-white + albedo_map.
    """
    for model, albedo in (("school", "school_diffuse.jpg"),
                          ("ambulance", "ambulance.png"),
                          ("truss-bridge", "truss_bridge_diffuse.jpg"),
                          ("pier", "pier_diffuse.jpg")):
        dest = out_models / model
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(MODELS_DIR / model, dest, symlinks=True)
        sdf_path = dest / "model.sdf"
        sdf = sdf_path.read_text()
        assert "<material>" not in sdf, f"upstream {model} gained material; re-vet"
        assert (dest / "materials" / "textures" / albedo).exists(), (
            f"{model} missing {albedo}"
        )
        anchor = "      </visual>"
        assert anchor in sdf, f"upstream {model} SDF changed; re-vet"
        sdf = sdf.replace(
            anchor,
            "        <material>\n"
            "          <diffuse>1 1 1 1</diffuse>\n"
            "          <pbr>\n"
            "            <metal>\n"
            f"              <albedo_map>model://{model}/materials/textures/{albedo}</albedo_map>\n"
            "            </metal>\n"
            "          </pbr>\n"
            "        </material>\n" + anchor,
        )
        assert "albedo_map" in sdf, f"PBR inject failed for {model}"
        sdf_path.write_text(sdf)


def stage_randy(out_models: Path) -> None:
    """Staged rescue-randy-sitting minus the nested remote include.

    The pinned SDF nests a https://fuel.ignitionrobotics.org include
    (Artifact Proximity Detector) that fails offline and is unrelated
    to the victim figure; drop the block, keep the mesh.
    """
    dest = out_models / "rescue-randy-sitting"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(MODELS_DIR / "rescue-randy-sitting", dest, symlinks=True)
    sdf_path = dest / "model.sdf"
    sdf = sdf_path.read_text()
    start = sdf.index("    <include>")
    end = sdf.index("   </include>\n") + len("   </include>\n")
    assert "fuel.ignitionrobotics.org" in sdf[start:end], "upstream randy changed; re-vet"
    sdf = sdf[:start] + sdf[end:]
    assert "fuel.ignitionrobotics.org" not in sdf, "randy strip failed"
    sdf_path.write_text(sdf)


def stage_rain(out_models: Path) -> None:
    """Staged storm rain (downward box emitter, slide tuning)."""
    smoke_orig = (MODELS_DIR / "smoke-generator" / "model.sdf").read_text()
    assert "<lifetime>2</lifetime>" in smoke_orig, "upstream smoke SDF changed"
    rain = out_models / "flood-rain"
    if rain.exists():
        shutil.rmtree(rain)
    shutil.copytree(MODELS_DIR / "smoke-generator", rain, symlinks=True)
    (rain / "model.sdf").write_text(
        '<?xml version="1.0" ?>\n<sdf version="1.6">\n'
        + _legacy_emitter_block(
            "flood_rain",
            "flood_rain",
            1.0,
            15,
            25,
            0,
            1500,
            "0.12 0.12 2.5",
            "0.65 0.70 0.80",
            "model://flood-rain/materials/textures/smoke.png",
            emitter_type="box",
            emitter_pose="0 0 0 0 1.5707 0",
            emitter_size="120 120 1",
            model_pose="0 0 40 0 0 0",
        )
        + "</sdf>\n"
    )


def _near(placed: list[dict], x: float, y: float, r: float) -> bool:
    return any(math.dist((x, y), (p["x"], p["y"])) < r for p in placed)


def layout_flood_town(rng: random.Random, w_m: float, h_m: float) -> list[dict]:
    """River town: flooded house/shop rows, high-ground pad, marina."""
    placed: list[dict] = []
    # High-ground pad corner (SW): school shelter + evac post.
    placed.append(
        {"name": "shelter_school", "model": "school", "x": 45, "y": 45,
         "z": 2.5, "yaw": 0.0}
    )
    for i, (dx, dy) in enumerate([(0, 0), (12, 3), (6, 12)]):
        placed.append(
            {"name": f"camp_tent_{i}", "model": "tent",
             "x": 70 + dx, "y": 60 + dy, "z": 2.5,
             "yaw": round(rng.uniform(0, 3.14), 2)}
        )
    placed.append(
        {"name": "camp_ambulance", "model": "ambulance",
         "x": 88, "y": 44, "z": 2.5, "yaw": 1.57}
    )
    # Marina dock + rescue boats in the water by the pad.
    placed.append(
        {"name": "marina", "model": "dock", "x": 110, "y": 30, "yaw": 0.0}
    )
    for i, (x, y) in enumerate([(150, 60), (210, 120)]):
        placed.append(
            {"name": f"rescue_boat_{i}", "model": "wam-v", "x": x, "y": y,
             "z": 1.1, "yaw": round(rng.uniform(-3.14, 3.14), 2)}
        )
    # Shop row downtown (flooded ground floors).
    for i in range(4):
        placed.append(
            {"name": f"shop_{i}", "model": "thrift-shop",
             "x": 130 + i * 14, "y": 150, "yaw": 0.0}
        )
    # House lattice, skipping the pad + marina + shop row.
    n = 0
    for gx in range(4, 57, 5):
        for gy in range(4, 57, 5):
            x, y = gx * CELL_M + rng.uniform(-3, 3), gy * CELL_M + rng.uniform(-3, 3)
            if x < 105 and y < 105:
                continue
            if math.dist((x, y), (110, 30)) < 40.0:
                continue
            if abs(y - 150) < 10.0 and 120 < x < 200:
                continue
            model = "house-1" if (n % 2 == 0) else "house-2"
            placed.append(
                {"name": f"house_{n:03d}", "model": model,
                 "x": round(x, 1), "y": round(y, 1),
                 "yaw": round(rng.choice([0.0, math.pi / 2]), 3)}
            )
            n += 1
    # Submerged cars (roofs awash) on the drowned avenues.
    for i, (x, y) in enumerate([(50, 150), (150, 220), (250, 150), (150, 60)]):
        placed.append(
            {"name": f"sunk_car_{i}", "model": "prius-hybrid",
             "x": x, "y": y, "z": -0.3,
             "yaw": round(rng.uniform(-3.14, 3.14), 2)}
        )
    # Drift debris rafts.
    for i in range(8):
        x = rng.uniform(20, w_m - 20)
        y = rng.uniform(110, h_m - 20)
        placed.append(
            {"name": f"drift_{i:02d}", "model": "tunnel-wall-debris",
             "x": round(x, 1), "y": round(y, 1), "z": 1.0,
             "yaw": round(rng.uniform(-math.pi, math.pi), 3)}
        )
    # Channel buoys up the town reach.
    for i in range(6):
        placed.append(
            {"name": f"buoy_{i}", "model": "mb-marker-buoy-red",
             "x": 150 + (14 if i % 2 else -14), "y": 120 + i * 28,
             "z": 1.1, "yaw": 0.0}
        )
    # Cordon around the shelter pad.
    for i in range(6):
        a = i * math.pi / 3
        placed.append(
            {"name": f"cordon_{i}", "model": "jersey-barrier",
             "x": round(60 + 42 * math.cos(a), 1),
             "y": round(60 + 42 * math.sin(a), 1),
             "yaw": round(a + math.pi / 2, 3)}
        )
    return placed


def layout_flash_valley(rng: random.Random, w_m: float, h_m: float) -> list[dict]:
    """Valley settlement on a swollen river; bridge = high crossing."""
    placed: list[dict] = []
    cx = w_m / 2
    # Truss bridge across the 24 m channel at mid-valley (mesh span
    # runs along X at yaw 0; pi/2 lays it along the river).
    placed.append(
        {"name": "high_bridge", "model": "truss-bridge",
         "x": cx, "y": 160, "yaw": 0.0}
    )
    # Rescue boat + buoys working the channel.
    placed.append(
        {"name": "rescue_boat_0", "model": "wam-v", "x": cx + 4, "y": 220,
         "z": 0.9, "yaw": 1.57}
    )
    for i in range(4):
        placed.append(
            {"name": f"buoy_{i}", "model": "mb-marker-buoy-red",
             "x": cx + (8 if i % 2 else -8), "y": 60 + i * 70,
             "z": 0.9, "yaw": 0.0}
        )
    # Homes on both banks (rows clear of the channel + banks).
    n = 0
    for side in (-1, 1):
        for i in range(8):
            x = cx + side * (34 + (i % 3) * 26 + rng.uniform(-4, 4))
            y = 30 + (i // 3) * 110 + rng.uniform(-8, 8) + (0 if i < 6 else 40)
            if not (8 < x < w_m - 8 and 8 < y < h_m - 8):
                continue
            model = "house-1" if (n % 2 == 0) else "house-2"
            placed.append(
                {"name": f"bank_house_{n:02d}", "model": model,
                 "x": round(x, 1), "y": round(y, 1),
                 "yaw": round(-side * math.pi / 2 + rng.uniform(-0.1, 0.1), 3)}
            )
            n += 1
    # Shops by the bridge landing (east bank).
    for i in range(2):
        placed.append(
            {"name": f"shop_{i}", "model": "thrift-shop",
             "x": cx + 30 + i * 12, "y": 146, "yaw": 0.0}
        )
    # Flank forest + boulders above the flood line.
    t = 0
    for _ in range(60):
        side = rng.choice([-1, 1])
        x = (rng.uniform(4, 26) if side < 0 else rng.uniform(w_m - 26, w_m - 4))
        y = rng.uniform(4, h_m - 4)
        model = rng.choice(["pine-tree", "oak-tree"])
        placed.append(
            {"name": f"flank_{t:02d}", "model": model,
             "x": round(x, 1), "y": round(y, 1),
             "yaw": round(rng.uniform(0, 6.28), 2)}
        )
        t += 1
    for i in range(10):
        side = rng.choice([-1, 1])
        x = (rng.uniform(26, 44) if side < 0 else rng.uniform(w_m - 44, w_m - 26))
        placed.append(
            {"name": f"sluice_rock_{i:02d}",
             "model": f"falling-rock-{(i % 6) + 1}",
             "x": round(x, 1), "y": round(rng.uniform(10, h_m - 10), 1),
             "yaw": round(rng.uniform(0, 6.28), 2)}
        )
    # Washed cars on the banks + evac post on the east rise.
    for i, (x, y) in enumerate([(cx - 40, 100), (cx + 52, 260)]):
        placed.append(
            {"name": f"wash_car_{i}", "model": "prius-hybrid",
             "x": x, "y": y, "z": -0.2,
             "yaw": round(rng.uniform(-3.14, 3.14), 2)}
        )
    placed.append(
        {"name": "evac_post", "model": "tent", "x": w_m - 14, "y": 160, "yaw": 0.4}
    )
    placed.append(
        {"name": "evac_ambulance", "model": "ambulance",
         "x": w_m - 16, "y": 178, "yaw": 1.57}
    )
    return placed


def layout_tsunami_coast(rng: random.Random, w_m: float, h_m: float) -> list[dict]:
    """Coastal strip: surf + pier + harbor, scoured town, high ground."""
    placed: list[dict] = []
    # Pier reaching into the surf (mesh runs +Y; yaw pi aims -Y).
    placed.append(
        {"name": "pier", "model": "pier", "x": 150, "y": 68, "yaw": math.pi}
    )
    # Harbor dock + port warehouse.
    placed.append(
        {"name": "harbor", "model": "dock", "x": 55, "y": 45, "yaw": 0.0}
    )
    placed.append(
        {"name": "port_warehouse", "model": "depot",
         "x": 242, "y": 122, "yaw": 0.0}
    )
    # Beached boats in the scour zone (keeled over).
    for i, (x, y, roll) in enumerate([(100, 150, 0.5), (200, 132, -0.45)]):
        placed.append(
            {"name": f"beached_{i}", "model": "wam-v", "x": x, "y": y,
             "z": 0.4, "yaw": round(rng.uniform(-3.14, 3.14), 2),
             "roll": roll}
        )
    # One boat still afloat off the harbor.
    placed.append(
        {"name": "rescue_boat_0", "model": "wam-v", "x": 60, "y": 100,
         "z": 1.0, "yaw": 0.8}
    )
    # Scour zone: collapsed homes + debris field across the mid-town.
    for i, (x, y) in enumerate([(120, 150), (180, 165), (150, 120)]):
        placed.append(
            {"name": f"collapsed_{i}", "model": "collapsed-house",
             "x": x, "y": y, "yaw": round(rng.uniform(-3.14, 3.14), 2)}
        )
    for i in range(10):
        x = rng.uniform(60, w_m - 60)
        y = rng.uniform(95, 205)
        model = "urban-wall-debris" if i % 2 == 0 else "tunnel-wall-debris"
        placed.append(
            {"name": f"scour_{i:02d}", "model": model,
             "x": round(x, 1), "y": round(y, 1),
             "yaw": round(rng.uniform(-math.pi, math.pi), 3)}
        )
    # Standing homes on the high ground (north) + shops by the depot.
    n = 0
    for gx in range(4, 57, 5):
        for gy in range(44, 57, 5):
            x, y = gx * CELL_M + rng.uniform(-3, 3), gy * CELL_M + rng.uniform(-3, 3)
            if math.dist((x, y), (242, 122)) < 34.0:
                continue
            model = "house-1" if (n % 2 == 0) else "house-2"
            placed.append(
                {"name": f"house_{n:03d}", "model": model,
                 "x": round(x, 1), "y": round(y, 1),
                 "yaw": round(rng.choice([0.0, math.pi]), 3)}
            )
            n += 1
    for i in range(2):
        placed.append(
            {"name": f"shop_{i}", "model": "thrift-shop",
             "x": 200 + i * 14, "y": 118, "yaw": 0.0}
        )
    # Buried cars in the scour + buoys marking the debris field.
    for i, (x, y) in enumerate([(130, 180), (170, 100), (90, 130)]):
        placed.append(
            {"name": f"scour_car_{i}", "model": "prius-hybrid",
             "x": x, "y": y, "z": -0.4,
             "yaw": round(rng.uniform(-3.14, 3.14), 2)}
        )
    for i in range(4):
        placed.append(
            {"name": f"buoy_{i}", "model": "mb-round-buoy-orange",
             "x": 80 + i * 45, "y": 92, "z": 1.0, "yaw": 0.0}
        )
    for i in range(2):
        placed.append(
            {"name": f"chan_buoy_{i}", "model": "mb-marker-buoy-red",
             "x": 40 + i * 30, "y": 60, "z": 1.0, "yaw": 0.0}
        )
    # Relief post on the high ground.
    for i, (dx, dy) in enumerate([(0, 0), (11, 3)]):
        placed.append(
            {"name": f"camp_tent_{i}", "model": "tent",
             "x": 60 + dx, "y": 262 + dy,
             "yaw": round(rng.uniform(0, 3.14), 2)}
        )
    placed.append(
        {"name": "camp_ambulance", "model": "ambulance",
         "x": 82, "y": 260, "yaw": 1.57}
    )
    return placed


def _box(name: str, cx: float, cy: float, cz: float, sx: float, sy: float,
         sz: float, mat: str) -> list[str]:
    return [
        f'    <model name="{name}">',
        "      <static>true</static>",
        f"      <pose>{cx} {cy} {cz} 0 0 0</pose>",
        '      <link name="link">',
        '        <collision name="collision">',
        f"          <geometry><box><size>{sx} {sy} {sz}</size></box></geometry>",
        "        </collision>",
        '        <visual name="visual">',
        f"          <geometry><box><size>{sx} {sy} {sz}</size></box></geometry>",
        mat,
        "        </visual>",
        "      </link>",
        "    </model>",
    ]


LAYOUTS = {
    "flood_hard": layout_flood_town,
    "flash_flood_hard": layout_flash_valley,
    "tsunami_hard": layout_tsunami_coast,
}

SKY = {
    # (ambient, background/fog color, fog start, fog end, sun diffuse)
    "flood_hard": ("0.55 0.57 0.60 1", "0.62 0.65 0.68 1", 80, 500,
                   "0.70 0.72 0.75 1"),
    "flash_flood_hard": ("0.45 0.47 0.52 1", "0.50 0.53 0.58 1", 60, 420,
                          "0.60 0.62 0.68 1"),
    "tsunami_hard": ("0.66 0.64 0.60 1", "0.74 0.72 0.68 1", 100, 600,
                     "0.90 0.85 0.76 1"),
}


def world_sdf(
    name: str,
    scenario: str,
    w_m: float,
    h_m: float,
    placed: list[dict],
    victims: list[dict] | None,
    seed: int,
) -> str:
    cx, cy = w_m / 2, h_m / 2
    ambient, fog, fog_start, fog_end, sun = SKY[scenario]
    lines = [
        '<?xml version="1.0" ?>',
        '<sdf version="1.9">',
        f'  <world name="{name}">',
        '    <physics name="1ms" type="ignored">',
        "      <max_step_size>0.001</max_step_size>",
        "    </physics>",
        '    <plugin filename="gz-sim-physics-system" '
        'name="gz::sim::systems::Physics"/>',
        '    <plugin filename="gz-sim-scene-broadcaster-system" '
        'name="gz::sim::systems::SceneBroadcaster"/>',
        '    <plugin filename="gz-sim-particle-emitter-system" '
        'name="gz::sim::systems::ParticleEmitter"/>',
        # No world-level shader-param system: it configures per-visual
        # (coast-water carries its own) and aborts the server when
        # attached to the world (2026-11-05 probe).
        '    <plugin filename="gz-sim-sensors-system" '
        'name="gz::sim::systems::Sensors">',
        "      <render_engine>ogre2</render_engine>",
        "    </plugin>",
        '    <light type="directional" name="sun">',
        "      <cast_shadows>true</cast_shadows>",
        "      <pose>0 0 100 0 0 0</pose>",
        f"      <diffuse>{sun}</diffuse>",
        "      <direction>-0.4 -0.4 -1</direction>",
        "    </light>",
        "    <scene>",
        f"      <ambient>{ambient}</ambient>",
        f"      <background>{fog}</background>",
        "      <fog>",
        f"        <color>{fog}</color>",
        "        <density>0.0</density>",
        f"        <start>{fog_start}</start>",
        f"        <end>{fog_end}</end>",
        "      </fog>",
        "      <sky/>",
        "    </scene>",
    ]
    if scenario == "flood_hard":
        lines += _box("town_ground", cx, cy, -0.05, w_m, h_m, 0.1,
                      GROUND_MAT.format(tex="asphalt_02.jpg"))
        lines += _box("floodwater", cx, cy, 1.1, w_m, h_m, 0.1, WATER_MAT)
        lines += _box("high_ground", 55, 55, 1.25, 70, 70, 2.5,
                      GROUND_MAT.format(tex="aerial_grass_rock.jpg"))
    elif scenario == "flash_flood_hard":
        lines += _box("valley_ground", cx, cy, -0.05, w_m, h_m, 0.1,
                      GROUND_MAT.format(tex="aerial_grass_rock.jpg"))
        lines += _box("riverbed", cx, cy, -0.03, 34, h_m, 0.1,
                      GROUND_MAT.format(tex="brown_mud_02.jpg"))
        lines += _box("bank_west", cx - 25, cy, -0.02, 16, h_m, 0.1,
                      GROUND_MAT.format(tex="sand_01.jpg"))
        lines += _box("bank_east", cx + 25, cy, -0.02, 16, h_m, 0.1,
                      GROUND_MAT.format(tex="sand_01.jpg"))
        lines += _box("riverwater", cx, cy, 0.9, 24, h_m, 0.1, WATER_MAT)
    elif scenario == "tsunami_hard":
        lines += _box("beach", cx, 45, -0.05, w_m, 90, 0.1,
                      GROUND_MAT.format(tex="sand_01.jpg"))
        lines += _box("town_ground", cx, 195, -0.05, w_m, 210, 0.1,
                      GROUND_MAT.format(tex="asphalt_02.jpg"))
        lines += _box("sea", cx, 35, 1.0, w_m, 70, 0.1, WATER_MAT)
        lines += _box("overwash", cx, 150, 0.35, w_m, 120, 0.1, OVERWASH_MAT)
    for p in placed:
        lines += [
            "    <include>",
            f"      <name>{p['name']}</name>",
            f"      <uri>model://{p['model']}</uri>",
            f"      <pose>{p['x']} {p['y']} {p.get('z', 0)} "
            f"{p.get('roll', 0.0)} {p.get('pitch', 0.0)} {p['yaw']}</pose>",
            "    </include>",
        ]
    # Rain over all three worlds (storm for flood/flash, drizzle for
    # the tsunami backwash so promo footage has motion). No
    # coast-water tiles: the Gerstner mesh renders ~100x over its
    # nominal 60 m (loader ignores the cm unit) and its cubemap-driven
    # blue cannot be recolored via shader params (2026-11-05 probe).
    lines += [
        "    <include>",
        "      <name>storm_rain</name>",
        "      <uri>model://flood-rain</uri>",
        f"      <pose>{cx} {cy} 0 0 0 0</pose>",
        "    </include>",
    ]
    vrng = random.Random(seed * 104729 + 7)
    meshes = ("standing-person", "male-visitor", "rescue-randy-sitting")
    for k, v in enumerate(victims or []):
        if v.get("category") not in ("human", "child"):
            continue
        vx, vy = float(v["x"]) * CELL_M, float(v["y"]) * CELL_M
        if scenario == "tsunami_hard" and v.get("mobility") != "mobile":
            z = 0.2
        elif scenario == "tsunami_hard":
            z = 0.9
        elif scenario == "flash_flood_hard" and abs(vx - w_m / 2) < 12.0:
            z = 0.9  # swept in the channel
        elif scenario == "flash_flood_hard":
            z = 0.1  # stranded on the bank (dry ground)
        else:
            z = 0.8  # wading chest-deep in the floodwater
        lines += [
            "    <include>",
            f"      <name>victim_{k}_{v['category']}</name>",
            f"      <uri>model://{meshes[k % 3]}</uri>",
            f"      <pose>{vx:.1f} {vy:.1f} {z} 0 0 {vrng.uniform(-3.14, 3.14):.3f}</pose>",
            "    </include>",
        ]
    lines += ["  </world>", "</sdf>"]
    return "\n".join(lines) + "\n"


def build(scenario: str, seed: int, out: Path) -> dict:
    if scenario not in LAYOUTS:
        raise SystemExit(f"unknown flood scenario {scenario!r}")
    config = load_scenario(scenario)
    width, height = int(config.grid["width"]), int(config.grid["height"])
    w_m, h_m = width * CELL_M, height * CELL_M
    rng = random.Random(seed)
    placed = LAYOUTS[scenario](rng, w_m, h_m)
    victims = eval_victims(scenario, seed)

    out.mkdir(parents=True, exist_ok=True)
    (out / "world.sdf").write_text(
        world_sdf(f"{scenario}_{seed}", scenario, w_m, h_m, placed, victims, seed)
    )
    ET.fromstring((out / "world.sdf").read_text())
    (out / "placements.json").write_text(
        json.dumps(
            {"scenario": scenario, "seed": seed, "placed": placed,
             "victims": victims},
            indent=2,
        )
    )
    # Wipe the staging root: stage functions only refresh dirs they
    # know, so a retired staged model (e.g. the brief wam-v scale
    # experiment) would otherwise shadow the pinned original forever.
    shutil.rmtree(out / "models", ignore_errors=True)
    stage_flood_common(out / "models")
    by_model: dict[str, int] = {}
    for p in placed:
        by_model[p["model"]] = by_model.get(p["model"], 0) + 1
    stats = {
        "includes": len(placed),
        "victim_actors": sum(
            1 for v in victims if v.get("category") in ("human", "child")
        ),
        "by_model": by_model,
    }
    (out / "stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Build flood world SDFs.")
    parser.add_argument("scenario", choices=sorted(LAYOUTS))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    stats = build(args.scenario, args.seed, Path(args.out))
    print(f"{args.scenario} seed={args.seed} -> {args.out}: {stats}")


if __name__ == "__main__":
    main()

