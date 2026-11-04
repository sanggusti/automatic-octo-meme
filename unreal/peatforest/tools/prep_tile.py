"""Clip tile-C GIS sources to UE inputs (#64, seeded/deterministic).

Reads data/peatforest/{copernicus_dem_S03E114.tif, worldcover_2021_S03E114.tif,
s2_20191023_T50MKB_visual.tif, s2_20191023_T50MKB_SCL.tif, firms_tileC.json}
and writes <out>/{heightmap.png (16-bit), albedo.png, masks.json,
fronts.json, meta.json}.

Tile C: bbox [114.318, -2.86, 114.336, -2.842] (~2x2 km, ex-MRP peatland),
chosen for its 10-hotspot Sept 2019 cluster. Landscape import: 1009x1009
verts over 2000 m (XY scale 198.4 cm/quad); heights normalized 0-15 m into
16-bit with Z scale 3 (UE maps full range to 512*Z cm = 15.36 m).

Usage: python unreal/peatforest/tools/prep_tile.py --out <dir>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

BBOX = (114.318, -2.86, 114.336, -2.842)  # lon_min, lat_min, lon_max, lat_max
LANDSCAPE_N = 1009  # UE verts per side (1008 quads)
HEIGHT_RANGE_M = 15.0  # normalization range (tile relief 1.2-14.3 m)
Z_SCALE = 3.0  # 512*Z cm = 15.36 m full range at 16-bit

FOREST_CLASSES = {10}
WATER_CLASSES = {80, 90}
CLEARING_CLASSES = {20, 30, 40, 50, 60}


def main() -> None:
    parser = argparse.ArgumentParser(description="Clip tile-C GIS to UE inputs.")
    parser.add_argument("--out", required=True)
    parser.add_argument("--data", default="data/peatforest")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data = Path(args.data)

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
            return src.read(window=win, **kw), src.crs

    # DEM -> 16-bit heightmap (bilinear upsample to landscape size).
    dem, _ = windowed(data / "copernicus_dem_S03E114.tif",
                      size=LANDSCAPE_N, resampling=Resampling.bilinear)
    dem = dem[0].astype("float64")
    lo, hi = float(dem.min()), float(dem.max())
    norm = np.clip((dem - 0.0) / HEIGHT_RANGE_M, 0.0, 1.0)
    Image.fromarray((norm * 65535.0).round().astype("uint16")).save(out / "heightmap.png")

    # S2 visual -> 8-bit albedo at landscape size.
    alb, _ = windowed(data / "s2_20191023_T50MKB_visual.tif",
                      size=LANDSCAPE_N, resampling=Resampling.bilinear)
    Image.fromarray(np.moveaxis(alb, 0, -1).astype("uint8")).save(out / "albedo.png")

    # WorldCover -> class masks at 10 m (nearest, no smoothing).
    wc, _ = windowed(data / "worldcover_2021_S03E114.tif",
                     resampling=Resampling.nearest)
    wc = wc[0]
    masks = {
        "size": list(wc.shape),
        "forest_frac": float(np.isin(wc, list(FOREST_CLASSES)).mean()),
        "water_frac": float(np.isin(wc, list(WATER_CLASSES)).mean()),
        "clearing_frac": float(np.isin(wc, list(CLEARING_CLASSES)).mean()),
    }
    (out / "masks.json").write_text(json.dumps(masks, indent=1))

    # Hotspots -> fronts (lon/lat + date kept verbatim).
    hotspots = json.loads((data / "firms_tileC.json").read_text())
    fronts = [
        {"lon": float(h["longitude"]), "lat": float(h["latitude"]),
         "date": h["acq_date"], "frp": float(h["frp"]),
         "confidence": h["confidence"]}
        for h in hotspots
    ]
    (out / "fronts.json").write_text(json.dumps(fronts, indent=1))

    quad_m = 2000.0 / (LANDSCAPE_N - 1)
    meta = {
        "bbox": list(BBOX),
        "landscape_n": LANDSCAPE_N,
        "xy_scale_cm_per_quad": round(quad_m * 100.0, 3),
        "height_range_m": HEIGHT_RANGE_M,
        "z_scale": Z_SCALE,
        "dem_min_m": round(lo, 2),
        "dem_max_m": round(hi, 2),
        "n_hotspots": len(fronts),
        "masks": masks,
    }
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    print(f"tile -> {out} dem=[{lo:.1f},{hi:.1f}]m fronts={len(fronts)}")


if __name__ == "__main__":
    main()
