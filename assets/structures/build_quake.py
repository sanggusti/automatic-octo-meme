#!/usr/bin/env python3
"""Build the earthquake_hard town world SDF (real Fuel structures only).

Layout mirrors the scenario hazards (5 m/cell): a collapsed downtown
core (industrial + homes + a 25 m rubble pile), a collapsed fire-station
landmark, standing house rows along a street grid, a relief camp, street
rubble, cordon barriers, response vehicles, and the eval's victim draw.

All meshes/textures come from assets/models and assets/textures (pinned
in assets/manifest.yaml); only poses are generated. Two documented
adaptations (same class as the peat flame_bed): staged house-1/house-2
copies gain a PBR albedo block because their script-only materials
render black under ogre2 (2026-11-04 probe).

Usage: python assets/structures/build_quake.py earthquake_hard
         --seed 7 --out /tmp/quake-town
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

from assets.vegetation.build_world import (  # noqa: E402
    MODELS_DIR,
    TEXTURES_DIR,
    _legacy_emitter_block,
    eval_victims,
    load_scenario,
)

CELL_M = 5.0
GROUND_TEX = "asphalt_02.jpg"

# model:// URI -> footprint diameter (m), from the 2026-11-04 scale probe
# (oblique vs 10 m poles) + COLLADA unit math. Italicised units respected
# by the loader: houses ~10-15 m, apartment ~20 m, station ~28 m.
ANCHORS = [
    # (model, gx, gy, yaw, role)
    ("collapsed-industrial-building", 30, 30, 0.3, "core"),
    ("collapsed-house", 27, 33, 1.1, "core"),
    ("collapsed-house", 33, 27, -0.6, "core"),
    ("urban-wall-debris", 30, 25, 0.0, "core-pile"),
    ("collapsed-industrial-building", 45, 15, 1.2, "industrial"),
    ("fire-station-collapsed", 15, 40, -0.2, "station"),
    ("apartment", 24, 30, 0.0, "downtown"),
    ("apartment", 36, 30, 0.0, "downtown"),
]

HOUSE_TEX = {
    "house-1": ("House_1/Diffuse", "House_1_Diffuse.png", "House_1_Normal.png"),
    "house-2": ("House_2/Diffuse", "House_2_Diffuse.png", "House_2_Normal.png"),
}


def stage_structures(out_models: Path) -> None:
    """Staged model copies (pinned originals untouched).

    ground_tex hosts asphalt_02; house-1/house-2 gain PBR albedo blocks
    (script-only materials render black under ogre2); smoke-generator +
    fog-emitter-dense are rehosted with the peat tuning (thin gray dust
    columns + wide haze banks).
    """
    stage_houses(out_models)
    if not (TEXTURES_DIR / GROUND_TEX).exists():
        raise SystemExit(
            f"missing ground texture {GROUND_TEX}; run "
            "python assets/textures/fetch_textures.py first"
        )
    gtex = out_models / "ground_tex"
    if gtex.exists():
        shutil.rmtree(gtex)
    (gtex / "materials" / "textures").mkdir(parents=True)
    shutil.copy(TEXTURES_DIR / GROUND_TEX, gtex / "materials" / "textures" / GROUND_TEX)
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

    stage_dust(out_models)


def stage_houses(out_models: Path) -> None:
    """Staged house-1/house-2 copies with PBR albedo blocks.

    Shared with the slide world (same black-script fix). Pinned
    originals untouched; staged dirs shadow them on the resource path.
    """
    for model, (script_name, albedo, normal) in HOUSE_TEX.items():
        dest = out_models / model
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(MODELS_DIR / model, dest, symlinks=True)
        sdf_path = dest / "model.sdf"
        sdf = sdf_path.read_text()
        marker = f"<name>{script_name}</name>"
        assert marker in sdf, f"upstream {model} SDF changed ({marker})"
        assert "albedo_map" not in sdf, f"upstream {model} gained PBR; re-vet"
        assert (dest / "materials" / "textures" / albedo).exists(), (
            f"{model} missing {albedo}"
        )
        # house-2 ships no normal map; only reference one that exists.
        normal_el = (
            f"                <normal_map>model://{model}/materials/textures/{normal}</normal_map>\n"
            if (dest / "materials" / "textures" / normal).exists()
            else ""
        )
        # Drop the script block: under ogre2 a failing script material
        # wins over (or breaks) the PBR block and the mesh renders
        # black (2026-11-04 town render). Diffuse white + PBR matches
        # the textured urban-wall-debris pattern.
        script_start = sdf.index("          <script>")
        script_end = sdf.index("          </script>\n") + len("          </script>\n")
        sdf = (
            sdf[:script_start]
            + "          <diffuse>1 1 1 1</diffuse>\n"
            + "            <pbr>\n"
            + "              <metal>\n"
            + f"                <albedo_map>model://{model}/materials/textures/{albedo}</albedo_map>\n"
            + normal_el
            + "              </metal>\n"
            + "            </pbr>\n"
            + sdf[script_end:]
        )
        assert "albedo_map" in sdf, f"PBR inject failed for {model}"
        assert "<script>" not in sdf, f"script strip failed for {model}"
        sdf_path.write_text(sdf)


def stage_dust(out_models: Path) -> None:
    """Staged dust columns + haze bank (thin gray smoke tuning)."""
    smoke_orig = (MODELS_DIR / "smoke-generator" / "model.sdf").read_text()
    for marker in ("<lifetime>2</lifetime>", "<min_velocity>10</min_velocity>"):
        assert marker in smoke_orig, f"upstream smoke SDF changed ({marker})"
    dest = out_models / "smoke-generator"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(MODELS_DIR / "smoke-generator", dest, symlinks=True)
    (dest / "model.sdf").write_text(
        '<?xml version="1.0" ?>\n<sdf version="1.6">\n'
        + _legacy_emitter_block(
            "smoke_generator",
            "smoke_generator",
            3.0,
            8,
            12,
            10,
            30,
            "2.5 2.5 2.5",
            "0.75 0.72 0.68",
            "model://smoke-generator/materials/textures/smoke.png",
        )
        + "</sdf>\n"
    )

    dense = out_models / "fog-emitter-dense"
    if dense.exists():
        shutil.rmtree(dense)
    shutil.copytree(MODELS_DIR / "fog-emitter-dense", dense, symlinks=True)
    orig = (MODELS_DIR / "fog-emitter-dense" / "model.sdf").read_text()
    for marker in (
        '<particle_emitter name="fog_generator" type="box">',
        "<size>0.5 8 0</size>",
        "<emitting>false</emitting>",
    ):
        assert marker in orig, f"upstream dense SDF changed ({marker}); re-vet"
    (dense / "model.sdf").write_text(
        '<?xml version="1.0" ?>\n<sdf version="1.6">\n'
        + _legacy_emitter_block(
            "fog_emitter_dense",
            "fog_generator",
            4.5,
            0.2,
            2.2,
            0.5,
            15,
            "4 4 4",
            "0.75 0.72 0.68",
            "model://fog-emitter-dense/materials/textures/fog.png",
            emitter_type="box",
            emitter_pose="0 0 0 0 -1.5707 0",
            emitter_size="0.5 8 0",
            model_pose="0 0 0 0 0 0",
        )
        + "</sdf>\n"
    )


def layout_town(rng: random.Random, w_m: float, h_m: float) -> list[dict]:
    """Standing houses on the block lattice + street rubble + camp."""
    placed: list[dict] = []
    for i, (model, gx, gy, yaw, role) in enumerate(ANCHORS):
        placed.append(
            {
                "name": f"{role}_{i:02d}",
                "model": model,
                "x": gx * CELL_M,
                "y": gy * CELL_M,
                "yaw": yaw,
            }
        )
    # Street grid: avenues at x/y in {50, 150, 250}, 20 m wide.
    streets = (50.0, 150.0, 250.0)

    def on_street(v: float) -> bool:
        return any(abs(v - s) < 12.0 for s in streets)

    def near_anchor(x: float, y: float, r: float) -> bool:
        return any(math.dist((x, y), (p["x"], p["y"])) < r for p in placed)

    # Houses: 25 m lattice inside blocks, yaw snapped to face streets.
    n = 0
    for gx in range(4, 57, 5):
        for gy in range(4, 57, 5):
            x, y = gx * CELL_M + rng.uniform(-3, 3), gy * CELL_M + rng.uniform(-3, 3)
            if on_street(x) or on_street(y):
                continue
            if near_anchor(x, y, 26.0):
                continue
            if math.dist((x, y), (40, 40)) < 30.0:  # relief camp lawn
                continue
            # Face the nearest street.
            dx = min(abs(x - s) for s in streets)
            dy = min(abs(y - s) for s in streets)
            yaw = (0.0 if dx < dy else math.pi / 2) + rng.uniform(-0.08, 0.08)
            if rng.random() < 0.5:
                yaw += math.pi
            model = "house-1" if (n % 2 == 0) else "house-2"
            placed.append(
                {"name": f"house_{n:03d}", "model": model, "x": round(x, 1),
                 "y": round(y, 1), "yaw": round(yaw, 3)}
            )
            n += 1
    # Street rubble: tunnel debris scattered near hazards + core.
    rubble_seeds = [(30, 30)] * 6 + [(45, 15)] * 4 + [(48, 42)] * 4 + [(15, 40)] * 3
    for i, (gx, gy) in enumerate(rubble_seeds):
        x = gx * CELL_M + rng.uniform(-18, 18)
        y = gy * CELL_M + rng.uniform(-18, 18)
        x = min(max(x, 8), w_m - 8)
        y = min(max(y, 8), h_m - 8)
        placed.append(
            {"name": f"rubble_{i:02d}", "model": "tunnel-wall-debris",
             "x": round(x, 1), "y": round(y, 1),
             "yaw": round(rng.uniform(-math.pi, math.pi), 3)}
        )
    # Tilted damaged houses by the aftershock zones (static lean reads
    # as structural damage; no new asset).
    for i, (gx, gy) in enumerate([(20, 15), (40, 48)]):
        placed.append(
            {"name": f"damaged_{i}", "model": "house-2" if i else "house-1",
             "x": gx * CELL_M, "y": gy * CELL_M, "yaw": 0.4 * i,
             "pitch": 0.12}
        )
    # Cordon ring around the core.
    for i in range(8):
        a = i * math.pi / 4 + 0.2
        placed.append(
            {"name": f"cordon_{i}", "model": "jersey-barrier",
             "x": round(150 + 45 * math.cos(a), 1),
             "y": round(150 + 45 * math.sin(a), 1),
             "yaw": round(a + math.pi / 2, 3)}
        )
    # Relief camp: tents + ambulance + spare barriers.
    for i, (dx, dy) in enumerate([(0, 0), (10, 2), (5, 10)]):
        placed.append(
            {"name": f"camp_tent_{i}", "model": "tent",
             "x": 40 + dx, "y": 40 + dy, "yaw": round(rng.uniform(0, 3.14), 2)}
        )
    placed.append(
        {"name": "camp_ambulance", "model": "ambulance",
         "x": 58, "y": 44, "yaw": 1.57}
    )
    # Street cars on the avenues.
    for i, (x, y, yaw) in enumerate(
        [(50, 100, 1.57), (150, 220, 1.57), (250, 60, 0.0)]
    ):
        placed.append(
            {"name": f"car_{i}", "model": "prius-hybrid", "x": x, "y": y,
             "yaw": yaw}
        )
    return placed


def world_sdf(
    name: str,
    w_m: float,
    h_m: float,
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
        "      <diffuse>0.85 0.78 0.66 1</diffuse>",
        "      <direction>-0.4 -0.4 -1</direction>",
        "    </light>",
        # Quake dust: warm gray scene fog over the town.
        "    <scene>",
        "      <ambient>0.62 0.58 0.54 1</ambient>",
        "      <background>0.70 0.67 0.62 1</background>",
        "      <fog>",
        "        <color>0.70 0.67 0.62 1</color>",
        "        <density>0.0</density>",
        "        <start>60</start>",
        "        <end>420</end>",
        "      </fog>",
        "      <sky/>",
        "    </scene>",
        # Town ground: real urban asphalt (CC0, pinned), thin box (planes
        # render black under ogre2).
        '    <model name="town_ground">',
        "      <static>true</static>",
        f'      <pose>{cx} {cy} -0.05 0 0 0</pose>',
        '      <link name="link">',
        '        <collision name="collision">',
        f"          <geometry><box><size>{w_m} {h_m} 0.1</size></box></geometry>",
        "        </collision>",
        '        <visual name="visual">',
        f"          <geometry><box><size>{w_m} {h_m} 0.1</size></box></geometry>",
        "          <material>",
        "            <ambient>0.7 0.7 0.7 1</ambient>",
        "            <diffuse>1.0 0.98 0.94 1</diffuse>",
        "            <pbr>",
        "              <metal>",
        f"                <albedo_map>model://ground_tex/materials/textures/{GROUND_TEX}</albedo_map>",
        "              </metal>",
        "            </pbr>",
        "          </material>",
        "        </visual>",
        "      </link>",
        "    </model>",
    ]
    for p in placed:
        pitch = p.get("pitch", 0.0)
        lines += [
            "    <include>",
            f"      <name>{p['name']}</name>",
            f"      <uri>model://{p['model']}</uri>",
            f"      <pose>{p['x']} {p['y']} 0 0 {pitch} {p['yaw']}</pose>",
            "    </include>",
        ]
    # Dust columns over the collapse sites + a haze bank downwind.
    for i, (dx, dy) in enumerate([(150, 150), (225, 75), (75, 200)]):
        lines += [
            "    <include>",
            f"      <name>dust_{i}</name>",
            "      <uri>model://smoke-generator</uri>",
            f"      <pose>{dx} {dy} 1 0 0 0</pose>",
            "    </include>",
        ]
    lines += [
        "    <include>",
        "      <name>dust_haze</name>",
        "      <uri>model://fog-emitter-dense</uri>",
        "      <pose>200 150 4 0 0 0</pose>",
        "    </include>",
    ]
    vrng = random.Random(seed * 104729 + 7)
    for k, v in enumerate(victims or []):
        if v.get("category") not in ("human", "child"):
            continue
        mesh = ("standing-person", "male-visitor")[k % 2]
        vx, vy = float(v["x"]) * CELL_M, float(v["y"]) * CELL_M
        lines += [
            "    <include>",
            f"      <name>victim_{k}_{v['category']}</name>",
            f"      <uri>model://{mesh}</uri>",
            f"      <pose>{vx:.1f} {vy:.1f} 0 0 0 {vrng.uniform(-3.14, 3.14):.3f}</pose>",
            "    </include>",
        ]
    lines += ["  </world>", "</sdf>"]
    return "\n".join(lines) + "\n"


def build(scenario: str, seed: int, out: Path) -> dict:
    config = load_scenario(scenario)
    width, height = int(config.grid["width"]), int(config.grid["height"])
    w_m, h_m = width * CELL_M, height * CELL_M
    rng = random.Random(seed)
    placed = layout_town(rng, w_m, h_m)
    victims = eval_victims(scenario, seed)

    out.mkdir(parents=True, exist_ok=True)
    (out / "world.sdf").write_text(
        world_sdf(f"{scenario}_{seed}", w_m, h_m, placed, victims, seed)
    )
    ET.fromstring((out / "world.sdf").read_text())
    (out / "placements.json").write_text(
        json.dumps(
            {"scenario": scenario, "seed": seed, "placed": placed,
             "victims": victims},
            indent=2,
        )
    )
    stage_structures(out / "models")
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
    parser = argparse.ArgumentParser(description="Build quake town world SDF.")
    parser.add_argument("scenario")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    stats = build(args.scenario, args.seed, Path(args.out))
    print(f"{args.scenario} seed={args.seed} -> {args.out}: {stats}")


if __name__ == "__main__":
    main()
