#!/usr/bin/env python3
"""Headless render check for the flood/flash/tsunami worlds.

Builds with build_flood.py, appends survey cameras (nadir, oblique,
low), and writes render.sdf + cameras.json for grab_frame.py.

  python assets/structures/render_check_flood.py flood_hard \\
      --seed 7 --out /tmp/render-flood
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from assets.structures.build_flood import build  # noqa: E402
from assets.vegetation.render_check import camera_model  # noqa: E402

CAMS = {
    # nadir over the town reach / channel / surf, oblique across the
    # water, low shot skimming the floodwater.
    "flood_hard": [
        ("cam_nadir", "150 195 150 0 1.5708 0"),
        ("cam_oblique", "65 65 60 0 0.5 0.7854"),
        ("cam_low", "150 60 6 0 0.08 1.5708"),
        ("cam_pad", "110 110 25 0 0.5 -2.3562"),
    ],
    "flash_flood_hard": [
        ("cam_nadir", "120 200 150 0 1.5708 0"),
        ("cam_oblique", "40 80 60 0 0.5 0.7854"),
        ("cam_low", "120 40 6 0 0.08 1.5708"),
    ],
    "tsunami_hard": [
        ("cam_nadir", "150 195 150 0 1.5708 0"),
        ("cam_oblique", "235 235 60 0 0.5 -2.10"),
        ("cam_low", "230 45 6 0 0.08 3.1416"),
        ("cam_harbor", "120 130 25 0 0.5 -2.1"),
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare flood render.")
    parser.add_argument("scenario", choices=sorted(CAMS))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    stats = build(args.scenario, args.seed, out)
    cams = CAMS[args.scenario]
    block = "\n".join(camera_model(n, p) for n, p in cams)
    text = (out / "world.sdf").read_text().replace(
        "  </world>", block + "\n  </world>"
    )
    ET.fromstring(text)
    (out / "render.sdf").write_text(text)
    topics = [
        f"/world/{args.scenario}_{args.seed}/model/{n}/link/link/sensor/camera/image"
        for n, _ in cams
    ]
    (out / "cameras.json").write_text(json.dumps(topics, indent=2))
    print(f"{args.scenario} seed={args.seed}: {stats}")
    print("topics:", json.dumps(topics, indent=2))


if __name__ == "__main__":
    main()
