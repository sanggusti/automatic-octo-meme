#!/usr/bin/env python3
"""Fetch pinned CC0 ground textures (Polyhaven) into assets/textures/.

Like fetch_models.py for Fuel: the manifest is the source of truth
(url + sha256 + license); this script only materializes it. Binaries
are gitignored; CI/renders run the fetch first.

Textures (Polyhaven, CC0-1.0, diffuse 4k JPG):
  aerial_grass_rock -- aerial moss-grass/soil mosaic; peat ground albedo
                      (the grass-soil gradation; no invented texture).
  burned_ground_01  -- charred ground; scorch decals under fire clusters.
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
