#!/usr/bin/env python3
"""Headless render check for the quake town world.

Builds with build_quake.py, appends survey cameras (nadir over the
collapse core, oblique down the avenue, low street-level shot), and
writes render.sdf + cameras.json for grab_frame.py.

  python assets/structures/render_check_quake.py earthquake_hard \\
      --seed 7 --out /tmp/render-quake
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from assets.structures.build_quake import build  # noqa: E402
from assets.vegetation.render_check import camera_model  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare quake render.")
    parser.add_argument("scenario")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    stats = build(args.scenario, args.seed, out)
    cams = [
        ("cam_nadir", "195 195 150 0 1.5708 0"),
        ("cam_oblique", "65 65 60 0 0.5 0.7854"),
        ("cam_low", "20 150 12 0 0.08 0"),
    ]
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
