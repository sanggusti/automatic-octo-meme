#!/usr/bin/env python3
"""Build the landslide_hard slope world SDF (real Fuel/P-D assets only).

A 240x320 m monsoon hillside tilted 12 deg about X: exposed rock
head-scarp at the crest, a widening mud-and-boulder debris flow down the
fall line, buried cars and at-risk homes at the toe, a blocked hillside
road, stranded-flank forest (pinned oak/pine), an evac post, and the
eval's victim draw (buried victims half-sunk, static ones standing).

All meshes/textures come from assets/models and assets/textures (pinned
in assets/manifest.yaml); only poses are generated. Rain is a downward
box emitter staged from smoke-generator (documented adaptation); if the
probe render shows it pillar or invisible, it is dropped and the world
ships static.

Usage: python assets/structures/build_slide.py landslide_hard
         --seed 7 --out /tmp/slide-slope
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
SLOPE_DEG = 12.0
SLOPE = math.radians(SLOPE_DEG)
TAN = math.tan(SLOPE)
GROUND_TEX = {
    "mud": "brown_mud_02.jpg",
    "rock": "rock_face_03.jpg",
    "road": "asphalt_02.jpg",
}

ROCKS = (
    "falling-rock-1",
    "falling-rock-2",
    "falling-rock-3",
    "falling-rock-4",
    "falling-rock-5",
    "falling-rock-6",
)


def surf_z(y: float, h_m: float, zc: float) -> float:
    """Ground surface height at downslope coordinate y (crest high)."""
    return zc - (y - h_m / 2) * TAN


def stage_slide(out_models: Path) -> None:
    """Staged copies: ground_tex (mud+rock+asphalt) + rain emitter."""
    stage_houses(out_models)
    missing = [n for n in GROUND_TEX.values() if not (TEXTURES_DIR / n).exists()]
    if missing:
        raise SystemExit(
            f"missing ground textures {missing}; run "
            "python assets/textures/fetch_textures.py first"
        )
    gtex = out_models / "ground_tex"
    if gtex.exists():
        shutil.rmtree(gtex)
    (gtex / "materials" / "textures").mkdir(parents=True)
    for n in GROUND_TEX.values():
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

    # Rain: downward box emitter. The +1.57 pitch about Y maps the
    # native +X jet to -Z (down); fast fall + quota cycling bounds the
    # streaks to the spawn volume (probe will confirm).
    smoke_orig = (MODELS_DIR / "smoke-generator" / "model.sdf").read_text()
    assert "<lifetime>2</lifetime>" in smoke_orig, "upstream smoke SDF changed"
    rain = out_models / "slide-rain"
    if rain.exists():
        shutil.rmtree(rain)
    shutil.copytree(MODELS_DIR / "smoke-generator", rain, symlinks=True)
    (rain / "model.sdf").write_text(
        '<?xml version="1.0" ?>\n<sdf version="1.6">\n'
        + _legacy_emitter_block(
            "slide_rain",
            "slide_rain",
            1.0,
            15,
            25,
            0,
            1500,
            "0.12 0.12 2.5",
            "0.65 0.70 0.80",
            "model://slide-rain/materials/textures/smoke.png",
            emitter_type="box",
            emitter_pose="0 0 0 0 1.5707 0",
            emitter_size="120 200 50",
            model_pose="0 0 0 0 0 0",
        )
        + "</sdf>\n"
    )
    cfg = rain / "model.config"
    cfg.write_text(
        cfg.read_text().replace(
            "<name>smoke_generator</name>", "<name>slide_rain</name>"
        )
    )


def layout_slide(rng: random.Random, w_m: float, h_m: float, zc: float) -> list[dict]:
    """Debris flow, flank forest, toe structures, evac post."""
    placed: list[dict] = []
    cx = w_m / 2

    def put(name, model, x, y, yaw=0.0, dz=0.0, pitch=0.0, roll=0.0):
        placed.append(
            {
                "name": name,
                "model": model,
                "x": round(x, 1),
                "y": round(y, 1),
                "z": round(surf_z(y, h_m, zc) + dz, 2),
                "yaw": round(yaw, 3),
                "pitch": pitch,
                "roll": roll,
            }
        )

    # Debris flow: boulders along the fall line, widening downslope.
    for i in range(110):
        y = rng.uniform(35, h_m - 15)
        spread = 10 + y * 0.14
        x = cx + rng.gauss(0, spread / 2)
        x = min(max(x, 10), w_m - 10)
        put(
            f"boulder_{i:02d}",
            ROCKS[i % len(ROCKS)],
            x,
            y,
            rng.uniform(-math.pi, math.pi),
            dz=0.2,
            pitch=rng.uniform(-0.4, 0.4),
            roll=rng.uniform(-0.4, 0.4),
        )
    # Flank forest (intact hillside each side of the scar).
    n = 0
    for _ in range(400):
        if n >= 90:
            break
        x = rng.uniform(5, w_m - 5)
        y = rng.uniform(5, h_m - 5)
        if abs(x - cx) < 28 + y * 0.10:
            continue
        put(
            f"flank_{n:02d}",
            "oak-tree" if rng.random() < 0.7 else "pine-tree",
            x,
            y,
            rng.uniform(-math.pi, math.pi),
        )
        n += 1
    # Buried cars at the toe, half-sunk and tilted.
    put("buried_car_0", "prius-hybrid", 105, 250, 0.4, dz=-0.5, pitch=0.28)
    put("buried_car_1", "prius-hybrid", 138, 278, -0.9, dz=-0.6, roll=0.22)
    # At-risk homes past the toe, facing the road.
    put("toe_house_0", "house-2", 58, 292, 1.57)
    put("toe_house_1", "house-2", 182, 296, 1.57)
    # Cordon along the blocked road (y = toe road).
    for i in range(6):
        put("road_cordon_%d" % i, "jersey-barrier", 30 + i * 36, 306, 1.57)
    # Evac post on the safe crest flank + response ambulance on the road.
    put("evac_tent_0", "tent", 198, 38, 0.3)
    put("evac_tent_1", "tent", 208, 46, -0.2)
    put("evac_amb", "ambulance", 42, 306, 1.57)
    return placed


def _tilted_box(name, x, y, z, sx, sy, tex, diffuse, ambient) -> list[str]:
    return [
        f'    <model name="{name}">',
        "      <static>true</static>",
        f"      <pose>{x} {y} {z} {-SLOPE:.4f} 0 0</pose>",
        '      <link name="link">',
        '        <collision name="collision">',
        f"          <geometry><box><size>{sx} {sy} 0.1</size></box></geometry>",
        "        </collision>",
        '        <visual name="visual">',
        f"          <geometry><box><size>{sx} {sy} 0.1</size></box></geometry>",
        "          <material>",
        f"            <ambient>{ambient}</ambient>",
        f"            <diffuse>{diffuse}</diffuse>",
        "            <pbr>",
        "              <metal>",
        f"                <albedo_map>model://ground_tex/materials/textures/{tex}</albedo_map>",
        "              </metal>",
        "            </pbr>",
        "          </material>",
        "        </visual>",
        "      </link>",
        "    </model>",
    ]


def world_sdf(
    name: str,
    w_m: float,
    h_m: float,
    zc: float,
    placed: list[dict],
    victims: list[dict] | None,
    seed: int,
) -> str:
    cx, cy = w_m / 2, h_m / 2
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
        '    <plugin filename="gz-sim-sensors-system" '
        'name="gz::sim::systems::Sensors">',
        "      <render_engine>ogre2</render_engine>",
        "    </plugin>",
        '    <light type="directional" name="sun">',
        "      <cast_shadows>true</cast_shadows>",
        "      <pose>0 0 100 0 0 0</pose>",
        "      <diffuse>0.68 0.68 0.69 1</diffuse>",
        "      <direction>-0.3 -0.3 -1</direction>",
        "    </light>",
        # Monsoon overcast: flat gray fog over the slope.
        "    <scene>",
        "      <ambient>0.62 0.62 0.63 1</ambient>",
        "      <background>0.58 0.60 0.63 1</background>",
        "      <fog>",
        "        <color>0.58 0.60 0.63 1</color>",
        "        <density>0.0</density>",
        "        <start>40</start>",
        "        <end>380</end>",
        "      </fog>",
        "      <sky/>",
        "    </scene>",
    ]
    # Mud slope, rock head-scarp, asphalt toe road (thin tilted boxes;
    # planes render black under ogre2).
    lines += _tilted_box(
        "mud_slope", cx, cy, zc - 0.05, w_m, h_m,
        GROUND_TEX["mud"], "1.0 0.97 0.92 1", "0.7 0.68 0.64 1",
    )
    lines += _tilted_box(
        "head_scarp", cx, 45, surf_z(45, h_m, zc) + 0.15, 130, 70,
        GROUND_TEX["rock"], "0.95 0.95 0.95 1", "0.6 0.6 0.6 1",
    )
    lines += _tilted_box(
        "toe_road", cx, 306, surf_z(306, h_m, zc) + 0.12, w_m, 14,
        GROUND_TEX["road"], "0.9 0.9 0.9 1", "0.6 0.6 0.6 1",
    )
    for p in placed:
        lines += [
            "    <include>",
            f"      <name>{p['name']}</name>",
            f"      <uri>model://{p['model']}</uri>",
            f"      <pose>{p['x']} {p['y']} {p['z']} {p['roll']} {p['pitch']} {p['yaw']}</pose>",
            "    </include>",
        ]
    lines += [
        "    <include>",
        "      <name>monsoon_rain</name>",
        "      <uri>model://slide-rain</uri>",
        f"      <pose>{cx} 180 55 0 0 0</pose>",
        "    </include>",
    ]
    vrng = random.Random(seed * 104729 + 7)
    for k, v in enumerate(victims or []):
        if v.get("category") not in ("human", "child"):
            continue
        mesh = ("standing-person", "male-visitor")[k % 2]
        vx, vy = float(v["x"]) * CELL_M, float(v["y"]) * CELL_M
        # Buried victims half-sunk: visible torso reads trapped.
        dz = -0.4 if v.get("mobility") == "buried" else 0.0
        lines += [
            "    <include>",
            f"      <name>victim_{k}_{v['category']}</name>",
            f"      <uri>model://{mesh}</uri>",
            f"      <pose>{vx:.1f} {vy:.1f} {surf_z(vy, h_m, zc) + dz:.2f} 0 0 {vrng.uniform(-3.14, 3.14):.3f}</pose>",
            "    </include>",
        ]
    lines += ["  </world>", "</sdf>"]
    return "\n".join(lines) + "\n"


def build(scenario: str, seed: int, out: Path) -> dict:
    config = load_scenario(scenario)
    width, height = int(config.grid["width"]), int(config.grid["height"])
    w_m, h_m = width * CELL_M, height * CELL_M
    zc = (h_m - h_m / 2) * TAN + 0.5
    rng = random.Random(seed)
    placed = layout_slide(rng, w_m, h_m, zc)
    victims = eval_victims(scenario, seed)

    out.mkdir(parents=True, exist_ok=True)
    (out / "world.sdf").write_text(
        world_sdf(f"{scenario}_{seed}", w_m, h_m, zc, placed, victims, seed)
    )
    ET.fromstring((out / "world.sdf").read_text())
    (out / "placements.json").write_text(
        json.dumps(
            {"scenario": scenario, "seed": seed, "slope_deg": SLOPE_DEG,
             "zc": zc, "placed": placed, "victims": victims},
            indent=2,
        )
    )
    stage_slide(out / "models")
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
    parser = argparse.ArgumentParser(description="Build slide slope world SDF.")
    parser.add_argument("scenario")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    stats = build(args.scenario, args.seed, Path(args.out))
    print(f"{args.scenario} seed={args.seed} -> {args.out}: {stats}")


if __name__ == "__main__":
    main()
