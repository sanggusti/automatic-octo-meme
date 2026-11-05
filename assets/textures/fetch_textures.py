#!/usr/bin/env python3
"""Fetch pinned CC0 ground textures (Polyhaven) into assets/textures/.

Like fetch_models.py for Fuel: the manifest is the source of truth
(url + sha256 + license); this script only materializes it. Binaries
are gitignored; CI/renders run the fetch first.

Textures (Polyhaven, CC0-1.0, diffuse 4k JPG):
  aerial_grass_rock -- aerial moss-grass/soil mosaic; peat ground albedo
                      (the grass-soil gradation; no invented texture).
  burned_ground_01  -- charred ground; scorch decals under fire clusters.
  asphalt_02        -- urban asphalt; quake town street grid albedo.
  brown_mud_leaves_01 -- wet mud + leaf litter; landslide debris-flow albedo.
  rock_face_03      -- exposed rock; landslide head-scarp albedo.
  sand_01           -- sand; tsunami beach/coast + flash-flood riverbank albedo.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent

TEXTURES = {
    "aerial_grass_rock.jpg": {
        "url": "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/4k/aerial_grass_rock/aerial_grass_rock_diff_4k.jpg",
        "sha256": "84bf24b80d097c1a38d0fbe5c84584b1ede3e2ab06b4af2721fd184a9f94d5a3",
    },
    "burned_ground_01.jpg": {
        "url": "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/4k/burned_ground_01/burned_ground_01_diff_4k.jpg",
        "sha256": "d5cde28f8a7ad34ab3dcea8dc0f4ed836c16688e96c40695c760dfb052b46e89",
    },
    "asphalt_02.jpg": {
        "url": "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/4k/asphalt_02/asphalt_02_diff_4k.jpg",
        "sha256": "d1601354507b6c4a46aa741b9134f9f23f738596a2bdcd20792e50ca554018e0",
    },
    "brown_mud_leaves_01.jpg": {
        "url": "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/4k/brown_mud_leaves_01/brown_mud_leaves_01_diff_4k.jpg",
        "sha256": "bfca3a9db391ac14750705d6903daaf09e221baa2e60e97836efb8a4d3e230a4",
    },
    "brown_mud_02.jpg": {
        "url": "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/4k/brown_mud_02/brown_mud_02_diff_4k.jpg",
        "sha256": "9477cb889f26c131c411a771cf057319738f857c6b7288747430122779106da5",
    },
    "rock_face_03.jpg": {
        "url": "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/4k/rock_face_03/rock_face_03_diff_4k.jpg",
        "sha256": "83148536c125cee3a2e2fc1368c8851ad4c87aef8b8bb35c5129d82d223effb3",
    },
    "sand_01.jpg": {
        "url": "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/4k/sand_01/sand_01_diff_4k.jpg",
        "sha256": "882e10aec3a0dd2eae3bc5c726f2dbb5c1aa8748211ec19d90728430d3253795",
    },
}


def fetch(dest: Path, check_only: bool = False) -> list[str]:
    dest.mkdir(parents=True, exist_ok=True)
    ready: list[str] = []
    for name, spec in TEXTURES.items():
        path = dest / name
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest == spec["sha256"]:
                ready.append(name)
                continue
            print(f"{name}: hash mismatch, re-downloading", file=sys.stderr)
            path.unlink()
        if check_only:
            print(f"{name}: MISSING", file=sys.stderr)
            continue
        print(f"{name}: downloading ...", flush=True)
        urllib.request.urlretrieve(spec["url"], path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != spec["sha256"]:
            path.unlink()
            raise SystemExit(f"{name}: sha256 mismatch after download")
        ready.append(name)
    return ready


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch pinned ground textures.")
    parser.add_argument("--dest", default=str(HERE))
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    ready = fetch(Path(args.dest), check_only=args.check_only)
    print(f"textures ready: {ready}")


if __name__ == "__main__":
    main()
