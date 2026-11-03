"""Peatland heightfield generator (#50, stdlib only).

Writes terrain.obj (centimetre units, Y-up) + meta.json (spawn height,
grid mapping) for the UE map build. Gentle noise relief, a peat dome
under the drained eastern block, and a drainage-canal trench along the
peat boundary — the Indonesian peatland signature.

Usage: python unreal/forest_fire/tools/terrain_gen.py --seed 7 --out <dir>
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

CELL_M = 5.0
GRID = 10
SPAN_M = CELL_M * GRID  # 50 m tile
STEP_M = 1.0  # heightfield resolution
N = int(SPAN_M / STEP_M) + 1  # 51 x 51 verts


def smoothstep(a: float, b: float, x: float) -> float:
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def value_noise(seed: int):
    rng = random.Random(seed)
    # coarse control lattice over the tile, bilinearly interpolated
    lattice = [[rng.random() for _ in range(6)] for _ in range(6)]

    def at(fx: float, fy: float) -> float:
        gx, gy = fx / SPAN_M * 5.0, fy / SPAN_M * 5.0
        x0, y0 = min(4, int(gx)), min(4, int(gy))
        tx, ty = gx - x0, gy - y0
        sx, sy = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        return (
            lattice[y0][x0] * (1 - sx) * (1 - sy)
            + lattice[y0][x0 + 1] * sx * (1 - sy)
            + lattice[y0 + 1][x0] * (1 - sx) * sy
            + lattice[y0 + 1][x0 + 1] * sx * sy
        )

    return at


def height_m(noise, east_m: float, north_m: float) -> float:
    h = 0.4 + noise(east_m, north_m) * 1.1  # rolling 0.4..1.5 m
    h += 0.4 * smoothstep(24.0, 30.0, east_m)  # peat dome under drained block
    # drainage canal along the peat boundary (east = 25 m), 3 m wide
    d = abs(east_m - 25.0)
    h -= 0.9 * (1.0 - smoothstep(0.0, 1.5, d))
    # orientation mound at the NE corner (45, 45): proves import axes on capture
    h += 2.0 * math.exp(-((east_m - 45.0) ** 2 + (north_m - 45.0) ** 2) / (2 * 4.0**2))
    return h


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate peatland heightfield OBJ.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    noise = value_noise(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    verts = []
    for iy in range(N):
        north_m = iy * STEP_M
        for ix in range(N):
            east_m = ix * STEP_M
            h_cm = height_m(noise, east_m, north_m) * 100.0
            # Y-up OBJ: x = north, y = height, z = east (verified on import)
            verts.append((north_m * 100.0, h_cm, east_m * 100.0))

    lines = ["# peatland heightfield (DMB #50)", f"# seed {args.seed}"]
    lines += [f"v {x:.2f} {y:.2f} {z:.2f}" for x, y, z in verts]
    for iy in range(N - 1):
        for ix in range(N - 1):
            a = iy * N + ix + 1
            b = a + 1
            c = a + N
            d = c + 1
            # CCW from above in OBJ space (x=north, y=up, z=east): normals +Y.
            lines += [f"f {a} {b} {c}", f"f {b} {d} {c}"]
    (out / "terrain.obj").write_text("\n".join(lines) + "\n")

    heights = [
        [round(height_m(noise, ix * STEP_M, iy * STEP_M) * 100.0, 1)
         for ix in range(N)]
        for iy in range(N)
    ]
    (out / "heights.json").write_text(
        json.dumps({"step_m": STEP_M, "n": N, "heights_cm": heights}))

    spawn_h = height_m(noise, 0.0, 0.0)
    meta = {
        "seed": args.seed,
        "cell_m": CELL_M,
        "grid": {"width": GRID, "height": GRID},
        "mapping": "grid (x=east, y=north) -> UE cm (X=y*500+250, Y=x*500+250); spawn at grid corner (0,0), clear of center-planted trees",
        "spawn_cm": {"x": 0.0, "y": 0.0, "z": round(spawn_h * 100.0 + 8.0, 2)},
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    write_swatches(out / "swatches")
    print(f"terrain.obj ({N}x{N}) + meta.json -> {out} spawn_z={meta['spawn_cm']['z']}cm")


# Flat color swatches (sRGB) for UE TextureSample materials. The material
# pin API only exposes R/G/B/A outputs on constant expressions (no RGB
# composite), so per-part colors come from 4x4 PNGs instead. Values follow
# VISUAL_TARGET.md. Pure stdlib (zlib + struct).
SWATCHES = {
    "ground": (43, 29, 18),
    "trunk": (64, 41, 26),
    "canopy": (74, 107, 42),
    "canopy_peat": (47, 74, 30),
    "charred": (8, 8, 8),
    "flame": (255, 122, 26),
    "smoke": (207, 200, 189),
    "glow": (224, 74, 0),
    # Control swatches: unlit black bases + roughness/specular wiring.
    "black": (0, 0, 0),
    "white": (255, 255, 255),
}


def write_swatches(outdir: Path) -> None:
    import struct
    import zlib

    outdir.mkdir(parents=True, exist_ok=True)

    def chunk(ctype: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + ctype + data
        return c + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)

    # NOTE: bytes are written B,G,R, not R,G,B. The PNGs are valid either
    # way (PIL reads them back correctly), but UE 5.6's texture import
    # renders them R/B-swapped (flames vivid BLUE instead of orange,
    # trunks navy instead of brown; verified live 2026-11-03 on fresh
    # delete-first reimports). Pre-swapping here renders correctly in-engine.
    for name, (r, g, b) in SWATCHES.items():
        raw = b"".join(b"\x00" + bytes((b, g, r)) * 4 for _ in range(4))
        png = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw))
            + chunk(b"IEND", b"")
        )
        (outdir / f"{name}.png").write_bytes(png)


if __name__ == "__main__":
    main()
