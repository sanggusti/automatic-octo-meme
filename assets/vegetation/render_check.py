#!/usr/bin/env python3
"""Headless render check for lush forest worlds.

Builds a world with build_world.py, appends static survey cameras
(nadir over the canopy, oblique toward the first ignition, low grazing
shot), and writes render.sdf + a camera topic list for grab_frame.py.

The actual render runs inside the sim container (see docs render
runbook); this script only prepares inputs and checks outputs:

  python assets/vegetation/render_check.py firms_peat_kalimantan_01 \\
      --seed 7 --out /tmp/render-k --trees 600
  # in container (staged out/models FIRST so Harmonic emitter copies
  # shadow the pinned originals):
  #   GZ_SIM_RESOURCE_PATH=/render/world/models:/render/models \\
  #     gz sim -s -r --headless-rendering /render/world/render.sdf &
  #   GZ_GRAB_TOPIC=<topic from cameras.json> grab_frame.py /render/out/0.png
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from assets.vegetation.build_world import CELL_M, build  # noqa: E402


def camera_model(name: str, pose: str) -> str:
    return f"""    <model name="{name}">
      <static>true</static>
      <pose>{pose}</pose>
      <link name="link">
        <sensor name="camera" type="camera">
          <camera>
            <horizontal_fov>1.047</horizontal_fov>
            <image><width>1280</width><height>720</height></image>
            <clip><near>0.5</near><far>3000</far></clip>
          </camera>
          <always_on>true</always_on>
          <update_rate>5</update_rate>
        </sensor>
      </link>
    </model>
"""


def add_cameras(text: str, world_name: str, ign_m: list) -> tuple[str, list[str]]:
    """Append 3 survey cameras; return (new text, image topics)."""
    ix, iy = (ign_m[0] if ign_m else (300.0, 300.0))
    cams = [
        # Nadir over canopy, offset 45 m from the ignition: columns rise
        # 100 m+ and a cam directly overhead sits inside the smoke.
        ("cam_nadir", f"{ix + 45} {iy + 45} 150 0 1.5708 0"),
        # Oblique toward ignition from 120 m out, 60 m up.
        ("cam_oblique", f"{ix - 85} {iy - 85} 60 0 0.5 0.7854"),
        # Low grazing shot across the stand toward the smoke.
        ("cam_low", f"{ix - 150} {iy} 12 0 0.08 0"),
    ]
    block = "\n".join(camera_model(n, p) for n, p in cams)
    new_text = text.replace("  </world>", block + "\n  </world>")
    ET.fromstring(new_text)
    topics = [
        f"/world/{world_name}/model/{n}/link/link/sensor/camera/image"
        for n, _ in cams
    ]
    return new_text, topics


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare headless render.")
    parser.add_argument("scenario")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", required=True)
    parser.add_argument("--trees", type=int, default=1500)
    args = parser.parse_args()
    out = Path(args.out)
    stats = build(args.scenario, args.seed, out, args.trees)
    placements = json.loads((out / "placements.json").read_text())
    text, topics = add_cameras(
        (out / "world.sdf").read_text(),
        f"{args.scenario}_{args.seed}",
        placements["ignitions_m"],
    )
    (out / "render.sdf").write_text(text)
    (out / "cameras.json").write_text(json.dumps(topics, indent=2))
    print(f"{args.scenario} seed={args.seed}: {stats}")
    print("topics:", json.dumps(topics, indent=2))


if __name__ == "__main__":
    main()
