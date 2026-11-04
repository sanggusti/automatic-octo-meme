"""Lush forest world builder (#firms): scenario -> Gazebo world SDF.

Unlike place_trees.py (one tree per fuel cell, grid-aligned, pine/oak
only), this builder grows a variative peat-swamp stand:

* clustered placement (seeded cluster centers + gaussian offsets) with
  rejection sampling on a minimum canopy spacing,
* seeded clearings (canopy gaps, kept away from ignition cells),
* jittered poses, random yaw, per-instance scale,
* species mix: oak overstory for peat scenarios (only verified
  broadleaf; pine/oak for generic scenarios),
* NO grass understory: both pinned grass models are plane-based and
  render black under ogre2 (see manifest),
* real smoke: smoke_generator columns on ignition cells, dense-fog haze
  banks downwind, flame_column derivative (smoke config, orange
  diffuse -- the manifest's documented adaptation),
* peat-tinted ground + linear scene fog for the Kalimantan haze.

All meshes/textures/emitters come from assets/models (pinned in
assets/manifest.yaml); only poses, scales, and the flame derivative's
diffuse are generated.

Usage: python assets/vegetation/build_world.py firms_peat_kalimantan_01
         --seed 7 --out /tmp/kalimantan --trees 1200
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

CELL_M = 5.0
MIN_SPACING_M = 5.5
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MODELS_DIR = REPO / "assets" / "models"

# model:// URIs resolve by resource-path directory name, not model.config
# <name> (fog-emitter's config name collides with smoke_generator's).
# Peat = oak overstory only: the only verified broadleaf (pine is
# botanically wrong for peat swamp; apple retired broken; no second
# broadleaf on Fuel -- see manifest). Placement still variative.
PEAT_MIX = (("oak-tree", 1.0),)
CLASSIC_MIX = (
    ("pine-tree", 0.60),
    ("oak-tree", 0.40),
)

FLAME_DIFFUSE = "1.0 0.45 0.1"


def load_scenario(scenario: str):
    sys.path.insert(0, str(REPO))
    from dmb.scenarios import load_scenario  # noqa: PLC0415

    return load_scenario(scenario)


def pick_species(rng: random.Random, mix) -> str:
    r = rng.random()
    acc = 0.0
    for name, weight in mix:
        acc += weight
        if r < acc:
            return name
    return mix[-1][0]


def seed_clearings(
    rng: random.Random, w_m: float, h_m: float, ign_m: list[tuple[float, float]]
) -> list[tuple[float, float, float]]:
    """3 canopy gaps, kept >=60 m from any ignition cell (fire needs fuel)."""
    out = []
    for _ in range(200):
        if len(out) == 3:
            break
        x, y = rng.uniform(60, w_m - 60), rng.uniform(60, h_m - 60)
        r = rng.uniform(25, 45)
        if all(math.dist((x, y), p) > 60 + r for p in ign_m):
            out.append((x, y, r))
    return out


def place_trees(
    rng: random.Random,
    w_m: float,
    h_m: float,
    target: int,
    clearings: list[tuple[float, float, float]],
    mix,
) -> list[dict]:
    centers = [
        (rng.uniform(0, w_m), rng.uniform(0, h_m))
        for _ in range(max(12, target // 25))
    ]
    accepted: list[dict] = []
    buckets: dict[tuple[int, int], list[tuple[float, float]]] = {}
    cell = MIN_SPACING_M

    def too_close(x: float, y: float) -> bool:
        bx, by = int(x / cell), int(y / cell)
        for ix in range(bx - 1, bx + 2):
            for iy in range(by - 1, by + 2):
                for px, py in buckets.get((ix, iy), ()):
                    if math.dist((x, y), (px, py)) < MIN_SPACING_M:
                        return True
        return False

    for _ in range(target * 40):
        if len(accepted) >= target:
            break
        cx, cy = rng.choice(centers)
        x, y = rng.gauss(cx, 80.0), rng.gauss(cy, 80.0)
        if not (2 < x < w_m - 2 and 2 < y < h_m - 2):
            continue
        if any(math.dist((x, y), (qx, qy)) < r for qx, qy, r in clearings):
            continue
        if too_close(x, y):
            continue
        buckets.setdefault((int(x / cell), int(y / cell)), []).append((x, y))
        species = pick_species(rng, mix)
        i = len(accepted)
        accepted.append(
            {
                "name": f"{species.replace('-', '_')}_{i:05d}",
                "species": species,
                "x": round(x, 2),
                "y": round(y, 2),
                "yaw": round(rng.uniform(-math.pi, math.pi), 3),
                "scale": round(rng.uniform(0.8, 1.3), 2),
            }
        )
    return accepted


def _legacy_emitter_block(
    name: str,
    kind: str,
    lifetime: float,
    min_vel: float,
    max_vel: float,
    scale_rate: float,
    rate: float,
    particle_size: str,
    diffuse: str,
    albedo_model_uri: str,
    emitter_type: str = "point",
    emitter_pose: str = "0 0 0 0 -1.57 0",
    emitter_size: str | None = None,
    model_pose: str = "0 0 0 0 0 0",
) -> str:
    # Ogre emitters shoot +X natively (hardcoded UNIT_X in
    # Ogre2ParticleEmitter.cc). The -1.57 pitch about Y maps +X to +Z
    # (up) but MUST sit on the emitter element: model-level pitch is
    # ignored by the particle system (renders proved: model-pitched
    # jets lie flat along +X). Never pitch both.
    size_el = f"\n                <size>{emitter_size}</size>" if emitter_size else ""
    return f"""    <model name="{name}">
        <pose>{model_pose}</pose>
        <static>true</static>
        <link name="link">
            <particle_emitter name="{kind}" type="{emitter_type}">
                <pose>{emitter_pose}</pose>
                <emitting>true</emitting>
                <rate>{rate}</rate>{size_el}
                <particle_size>{particle_size}</particle_size>
                <lifetime>{lifetime}</lifetime>
                <min_velocity>{min_vel}</min_velocity>
                <max_velocity>{max_vel}</max_velocity>
                <scale_rate>{scale_rate}</scale_rate>
                <material>
                    <diffuse>{diffuse}</diffuse>
                    <pbr>
                        <metal>
                            <albedo_map>{albedo_model_uri}</albedo_map>
                        </metal>
                    </pbr>
                </material>
            </particle_emitter>
        </link>
    </model>
"""


def stage_emitters(out_models: Path) -> None:
    """Harmonic-compatible emitter copies (pinned originals untouched).

    The Harmonic ParticleEmitter system ignores model <plugin> blocks
    (it only processes <particle_emitter> SDF elements), so the staged
    copies rehost each model's own numeric params in legacy link
    blocks. Albedo textures use model:// URIs (sdformat resolves them
    at parse); the color ramps are omitted (ogre-side ramp lookup
    fails for relative AND model:// paths). flame_column adds the
    orange diffuse (the manifest's documented adaptation).
    """
    smoke_orig = (MODELS_DIR / "smoke-generator" / "model.sdf").read_text()
    for marker in (
        "<lifetime>2</lifetime>",
        "<min_velocity>10</min_velocity>",
        "<max_velocity>20</max_velocity>",
        "<scale_rate>10</scale_rate>",
    ):
        assert marker in smoke_orig, f"upstream smoke SDF changed ({marker})"
    # Smoke/flame SHAPE tuning (documented adaptations, see manifest):
    # smoke keeps the model's velocity with denser rate/size/lifetime so
    # the column reads continuous instead of dotted; flame is a compact
    # fireball (low velocity, short life, dense rate) for a fire-vs-smoke
    # read at survey altitude.
    for name, model_name, diffuse, rate, psize, life, v0, v1 in [
        (
            "smoke-generator",
            "smoke_generator",
            "0.7 0.7 0.7",
            30,
            "2 2 2",
            2.5,
            10,
            15,
        ),
        ("flame_column", "flame_column", FLAME_DIFFUSE, 40, "2 2 2", 0.8, 3, 5),
    ]:
        dest = out_models / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(MODELS_DIR / "smoke-generator", dest, symlinks=True)
        (dest / "model.sdf").write_text(
            '<?xml version="1.0" ?>\n<sdf version="1.6">\n'
            + _legacy_emitter_block(
                model_name,
                model_name,
                life,
                v0,
                v1,
                10,
                rate,
                psize,
                diffuse,
                f"model://{name}/materials/textures/smoke.png",
            )
            + "</sdf>\n"
        )
        cfg = dest / "model.config"
        cfg.write_text(
            cfg.read_text().replace(
                "<name>smoke_generator</name>", f"<name>{model_name}</name>"
            )
        )

    # (canopy-broadleaf/apple retired: renders leafless-white even with
    # textures resolved. Oak tints retired: ogre2 ignores the legacy
    # pass diffuse. Both documented in the manifest.)

    # fog-emitter-dense: ship-state legacy block has emitting=false;
    # staged copy keeps the model's own numeric params (box type, wide
    # size, pitched emitter pose), flips emitting, and points the albedo
    # at a model:// URI (ramp omitted, see above).
    dense = out_models / "fog-emitter-dense"
    if dense.exists():
        shutil.rmtree(dense)
    shutil.copytree(MODELS_DIR / "fog-emitter-dense", dense, symlinks=True)
    orig = (MODELS_DIR / "fog-emitter-dense" / "model.sdf").read_text()
    for marker in (
        '<particle_emitter name="fog_generator" type="box">',
        "<pose>0 0 0 0 -1.5707 0</pose>",
        "<size>0.5 8 0</size>",
        "<particle_size>4 4 4</particle_size>",
        "<lifetime>4.5</lifetime>",
        "<min_velocity>0.2</min_velocity>",
        "<max_velocity>2.2</max_velocity>",
        "<scale_rate>0.5</scale_rate>",
        "<rate>15</rate>",
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
            "0.7 0.7 0.7",
            "model://fog-emitter-dense/materials/textures/fog.png",
            emitter_type="box",
            emitter_pose="0 0 0 0 -1.5707 0",
            emitter_size="0.5 8 0",
            model_pose="0 0 0 0 0 0",
        )
        + "</sdf>\n"
    )

def world_sdf(
    name: str,
    w_m: float,
    h_m: float,
    trees: list[dict],
    ign_m: list[tuple[float, float]],
    wind: tuple[float, float],
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
        "    <light type=\"directional\" name=\"sun\">",
        "      <cast_shadows>true</cast_shadows>",
        "      <pose>0 0 100 0 0 0</pose>",
        "      <diffuse>0.9 0.85 0.75 1</diffuse>",
        "      <direction>-0.4 -0.4 -1</direction>",
        "    </light>",
        # Kalimantan haze: linear scene fog over the whole stand.
        "    <scene>",
        "      <ambient>0.65 0.62 0.58 1</ambient>",
        "      <background>0.72 0.70 0.66 1</background>",
        "      <fog>",
        "        <color>0.72 0.70 0.66 1</color>",
        "        <density>0.0</density>",
        "        <start>80</start>",
        "        <end>520</end>",
        "      </fog>",
        "      <sky/>",
        "    </scene>",
        # Peat ground: dark organic slab under the grass texture patches.
        # A thin box, not <plane>: plane visuals render black under ogre2
        # (debug render 2026-11-04), boxes with the same material are fine.
        '    <model name="peat_ground">',
        "      <static>true</static>",
        f'      <pose>{cx} {cy} -0.05 0 0 0</pose>',
        '      <link name="link">',
        '        <collision name="collision">',
        f"          <geometry><box><size>{w_m} {h_m} 0.1</size></box></geometry>",
        "        </collision>",
        '        <visual name="visual">',
        f"          <geometry><box><size>{w_m} {h_m} 0.1</size></box></geometry>",
        "          <material>",
        "            <ambient>0.13 0.09 0.06 1</ambient>",
        "            <diffuse>0.15 0.10 0.07 1</diffuse>",
        "          </material>",
        "        </visual>",
        "      </link>",
        "    </model>",
    ]
    for t in trees:
        lines += [
            "    <include>",
            f"      <name>{t['name']}</name>",
            f"      <uri>model://{t['species']}</uri>",
            f"      <pose>{t['x']} {t['y']} 0 0 0 {t['yaw']}</pose>",
            # NOTE: no <scale> under <include> -- not valid SDF (gz warns
            # and ignores it). Size variation needs staged model copies.
            "    </include>",
        ]
    # No grass instances: both pinned grass models are plane-based and
    # render black under ogre2 (grass-plane is also a 500 m sprawl, not
    # a tuft). Understory awaits a mesh-based tuft asset.
    for i, (ix, iy) in enumerate(ign_m):
        lines += [
            "    <include>",
            f"      <name>fire_smoke_{i}</name>",
            "      <uri>model://smoke-generator</uri>",
            f"      <pose>{ix} {iy} 1 0 0 0</pose>",
            "    </include>",
            "    <include>",
            f"      <name>fire_flame_{i}</name>",
            "      <uri>model://flame_column</uri>",
            f"      <pose>{ix + 2} {iy + 1} 0.5 0 0 0</pose>",
            "    </include>",
        ]
        hx, hy = ix + wind[0] * 60, iy + wind[1] * 60
        lines += [
            "    <include>",
            f"      <name>haze_bank_{i}</name>",
            "      <uri>model://fog-emitter-dense</uri>",
            f"      <pose>{hx:.1f} {hy:.1f} 4 0 0 0</pose>",
            "    </include>",
        ]
    lines += ["  </world>", "</sdf>"]
    return "\n".join(lines) + "\n"


def build(
    scenario: str,
    seed: int,
    out: Path,
    trees_target: int = 1200,
) -> dict:
    config = load_scenario(scenario)
    width, height = int(config.grid["width"]), int(config.grid["height"])
    w_m, h_m = width * CELL_M, height * CELL_M
    fire = config.raw.get("dynamics", {}).get("fire", {})
    ign = [(d["x"] * CELL_M, d["y"] * CELL_M) for d in fire.get("ignition", [])]
    wind = tuple(fire.get("wind_dir", [1, 0]))
    peat = scenario.startswith("firms_peat")
    mix = PEAT_MIX if peat else CLASSIC_MIX

    rng = random.Random(seed)
    clearings = seed_clearings(rng, w_m, h_m, ign)
    trees = place_trees(rng, w_m, h_m, trees_target, clearings, mix)

    out.mkdir(parents=True, exist_ok=True)
    (out / "world.sdf").write_text(
        world_sdf(f"{scenario}_{seed}", w_m, h_m, trees, ign, wind)
    )
    ET.fromstring((out / "world.sdf").read_text())  # fail fast on bad XML
    fuel_default = float(fire.get("fuel_default", 0.0))
    (out / "fuel_tags.json").write_text(
        json.dumps(
            {t["name"]: round(fuel_default, 3) for t in trees}, indent=2
        )
    )
    (out / "placements.json").write_text(
        json.dumps(
            {
                "scenario": scenario,
                "seed": seed,
                "clearings": clearings,
                "ignitions_m": ign,
                "trees": trees,
            },
            indent=2,
        )
    )
    stage_emitters(out / "models")
    stats = {
        "trees": len(trees),
        "clearings": len(clearings),
        "emitters": 3 * len(ign),
        "species": {s: sum(1 for t in trees if t["species"] == s) for s, _ in mix},
    }
    (out / "stats.json").write_text(json.dumps(stats, indent=2))
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Build lush forest world SDF.")
    parser.add_argument("scenario")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out", required=True)
    parser.add_argument("--trees", type=int, default=1200)
    args = parser.parse_args()
    stats = build(args.scenario, args.seed, Path(args.out), args.trees)
    print(f"{args.scenario} seed={args.seed} -> {args.out}: {stats}")


if __name__ == "__main__":
    main()
