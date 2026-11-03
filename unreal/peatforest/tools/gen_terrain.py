"""Peatforest terrain + placement generator (#65, seeded).

Reads data/peatforest/*.tif + firms_tileC.json, writes <out>/ with:
  terrain.obj (500x500 verts, 4 m grid, cm, Z-up) + heights.json
  terrain_collision.obj (101x101 decimated shell, cm, Z-up, hidden)
  albedo_2k.png (S2 visual window, 2048px)
  placements.json (canopy trees from WorldCover forest mask + clumping noise)
  canals.json (straight water strips along wettest rows)
  ops.json (flat ops area near spawn) + meta.json

Grid mapping (same contract as forest_fire): grid (x=east, y=north) ->
UE cm (X=y*100, Y=x*100); spawn at tile SW corner (local NED origin).
OBJ verts use y=-east_cm because the UE import negates Y.
Tree count capped for StaticMeshActor perf; mesh assignment lives in
the UE builder config (stand-ins now, Quixel swap later).

Usage: python unreal/peatforest/tools/gen_terrain.py --seed 7 --out <dir>
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

BBOX = (114.318, -2.86, 114.336, -2.842)
SPAN_M = 2000.0
GRID_N = 500  # 4 m terrain grid
ALBEDO_N = 2048
MAX_TREES = 4000
UNDERSTORY_PER_TREE = 0  # understory deferred to foliage pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate peatforest terrain + placements.")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", required=True)
    parser.add_argument("--data", default="data/peatforest")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data = Path(args.data)
    rng = random.Random(args.seed)

    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds
    from PIL import Image

    def windowed(path, bounds=BBOX, size=None, resampling=Resampling.bilinear):
        with rasterio.open(path) as src:
            bb = transform_bounds("EPSG:4326", src.crs, *bounds)
            win = from_bounds(*bb, src.transform)
            kw = {}
            if size is not None:
                kw = {"out_shape": (src.count, size, size), "resampling": resampling}
            return src.read(window=win, **kw)

    # Terrain mesh from DEM (bilinear upsample to 4 m). Raster rows run
    # north-first; the mesh frame runs south-first, so flip rows: without
    # this the relief is N-S mirrored vs the (TRUE-placed) trees, fires,
    # canals and albedo (fixed in the hifi pass; heights.json follows).
    dem = windowed(data / "copernicus_dem_S03E114.tif",
                   size=GRID_N, resampling=Resampling.bilinear)[0].astype("float64")
    dem = np.ascontiguousarray(dem[::-1])
    step = SPAN_M / (GRID_N - 1)
    lines = ["# peatforest tile C terrain (DMB #65)", f"# seed {args.seed}"]
    for iy in range(GRID_N):
        north_m = iy * step
        for ix in range(GRID_N):
            east_m = ix * step
            h_cm = dem[iy, ix] * 100.0
            # Z-up OBJ: x=north, y=-east, z=height. UE imports Z verbatim
            # but NEGATES Y (bisected live: +y OBJ landed at NED -y), so
            # east is pre-negated to land the tile at +Y.
            lines.append(f"v {north_m * 100.0:.1f} {-east_m * 100.0:.1f} {h_cm:.1f}")
    for iy in range(GRID_N):
        for ix in range(GRID_N):
            # Planar UVs for the S2 albedo (PNG row 0 = tile north edge;
            # UE v=0 is the image top). Detail tiling multiplies these.
            lines.append(f"vt {ix / (GRID_N - 1):.5f} {1.0 - iy / (GRID_N - 1):.5f}")
    for iy in range(GRID_N - 1):
        for ix in range(GRID_N - 1):
            a = iy * GRID_N + ix + 1
            b = a + 1
            c = a + GRID_N
            d = c + 1
            lines += [f"f {a}/{a} {b}/{b} {c}/{c}",
                      f"f {b}/{b} {d}/{d} {c}/{c}"]  # +Z after Y-negation
    (out / "terrain.obj").write_text("\n".join(lines) + "\n")
    # Decimated collision shell (complex-as-simple cooks reliably at this
    # size; the 500x500 visual mesh silently yields no collision).
    # Decimated grid spanning the FULL tile: plain [::5] stops 16 m short.
    cidx = list(range(0, GRID_N, 5))
    if cidx[-1] != GRID_N - 1:
        cidx.append(GRID_N - 1)
    cn = len(cidx)
    clines = [f"# peatforest collision shell ({cn}x{cn})"]
    for iy in range(cn):
        for ix in range(cn):
            # Z-up OBJ, cm throughout (match the visual mesh exactly);
            # y=-east (import negates Y).
            clines.append(
                f"v {cidx[iy] * step * 100.0:.1f} {-cidx[ix] * step * 100.0:.1f} "
                f"{dem[cidx[iy], cidx[ix]] * 100.0:.1f}")
    for iy in range(cn - 1):
        for ix in range(cn - 1):
            a = iy * cn + ix + 1
            clines += [f"f {a} {a + 1} {a + cn}", f"f {a + 1} {a + cn + 1} {a + cn}"]
    (out / "terrain_collision.obj").write_text("\n".join(clines) + "\n")
    # Sidecar MUST be cm (key says heights_cm): consumers (grove bases,
    # fire/canals/spawn heights) use it against cm meshes. Meters here
    # buried every tree and spawned the drone 6.8 m underground (#65).
    heights = (dem[::10, ::10] * 100.0).round(1).tolist()  # 50x50 @40m
    (out / "heights.json").write_text(
        json.dumps({"step_m": step * 10, "n": len(heights),
                    "heights_cm": heights}))

    # Albedo from S2 visual.
    alb = windowed(data / "s2_20191023_T50MKB_visual.tif",
                   size=ALBEDO_N, resampling=Resampling.bilinear)
    Image.fromarray(np.moveaxis(alb, 0, -1).astype("uint8")).save(out / "albedo_2k.png")

    # Tree placements: forest-mask pixels + clumping noise, seeded shuffle.
    wc = windowed(data / "worldcover_2021_S03E114.tif",
                  resampling=Resampling.nearest)[0]
    hn, wn = wc.shape
    forest_ys, forest_xs = np.nonzero(wc == 10)
    # Clumping: keep pixels whose value-noise exceeds a threshold.
    lat = [[rng.random() for _ in range(9)] for _ in range(9)]

    def noise(fx, fy):
        gx, gy = fx * 8.0, fy * 8.0
        x0, y0 = min(7, int(gx)), min(7, int(gy))
        tx, ty = gx - x0, gy - y0
        sx, sy = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        return (lat[y0][x0] * (1 - sx) * (1 - sy)
                + lat[y0][x0 + 1] * sx * (1 - sy)
                + lat[y0 + 1][x0] * (1 - sx) * sy
                + lat[y0 + 1][x0 + 1] * sx * sy)

    cands = []
    for y, x in zip(forest_ys.tolist(), forest_xs.tolist()):
        if noise(x / wn, y / hn) > 0.35:
            # Jitter inside the 10 m pixel, keep clear of spawn corner.
            ex = (x + rng.random()) / wn * SPAN_M
            ny = (1.0 - (y + rng.random()) / hn) * SPAN_M
            if ex > 15.0 or ny > 15.0:
                cands.append((round(ex, 1), round(ny, 1)))
    rng.shuffle(cands)
    trees = cands[:MAX_TREES]
    (out / "placements.json").write_text(json.dumps(
        {"seed": args.seed, "count": len(trees),
         "trees": [{"x_m": x, "y_m": y} for x, y in trees]}, indent=1))

    # Canals: straight strips along the wettest rows (water+wetland).
    wet = np.isin(wc, [80, 90])
    row_wet = wet.sum(axis=1)
    top_rows = sorted(range(hn), key=lambda r: -row_wet[r])[:3]
    canals = []
    for r in top_rows:
        if row_wet[r] == 0:
            continue
        xs = np.nonzero(wet[r])[0]
        x0, x1 = xs.min() / wn * SPAN_M, (xs.max() + 1) / wn * SPAN_M
        ny = (1.0 - (r + 0.5) / hn) * SPAN_M
        canals.append({"from_m": [round(x0, 1), round(ny, 1)],
                       "to_m": [round(x1, 1), round(ny, 1)],
                       "width_m": 3.0})
    (out / "canals.json").write_text(json.dumps(canals, indent=1))

    # Ops area: flattest 20x20 m near SW corner (lowest DEM std).
    cell = int(20 / step)
    best, bi = 1e9, (0, 0)
    for iy in range(0, min(60, GRID_N - cell), 4):
        for ix in range(0, min(60, GRID_N - cell), 4):
            s = dem[iy:iy + cell, ix:ix + cell].std()
            if s < best:
                best, bi = s, (ix, iy)
    ox, oy = bi[0] * step + 10.0, bi[1] * step + 10.0
    ops = {"center_m": [round(ox, 1), round(oy, 1)], "size_m": 20,
           "slope_std_m": round(float(best), 3)}
    (out / "ops.json").write_text(json.dumps(ops, indent=1))

    hotspots = json.loads((data / "firms_tileC.json").read_text())
    meta = {
        "seed": args.seed, "bbox": list(BBOX), "span_m": SPAN_M,
        "dem_min_m": round(float(dem.min()), 2),
        "dem_max_m": round(float(dem.max()), 2),
        "n_trees": len(trees), "n_canals": len(canals),
        "n_hotspots": len(hotspots), "ops": ops,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    print(f"terrain {GRID_N}x{GRID_N} + {len(trees)} trees + "
          f"{len(canals)} canals + {len(hotspots)} hotspots -> {out}")


if __name__ == "__main__":
    main()
