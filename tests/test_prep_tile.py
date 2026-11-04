"""Tile prep pipeline (#64): clips synthetic sources to UE inputs."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "unreal" / "peatforest" / "tools" / "prep_tile.py"
BBOX = (114.318, -2.86, 114.336, -2.842)


def _cog(path, arr, count=1, crs="EPSG:4326"):
    h, w = arr.shape[-2:]
    with rasterio.open(
        path, "w", driver="GTiff", height=h, width=w, count=count,
        dtype=arr.dtype, crs=crs,
        transform=from_bounds(*BBOX, w, h),
    ) as dst:
        dst.write(arr if count > 1 else arr[np.newaxis])


def test_prep_tile_runs(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    rng = np.random.RandomState(7)
    _cog(data / "copernicus_dem_S03E114.tif",
         (rng.rand(65, 65) * 13.0 + 1.0).astype("float32"))
    _cog(data / "worldcover_2021_S03E114.tif",
         rng.choice([10, 20, 30, 40, 80, 90], size=(216, 216)).astype("uint8"))
    _cog(data / "s2_20191023_T50MKB_visual.tif",
         (rng.rand(3, 200, 200) * 255).astype("uint8"), count=3)
    hotspots = [
        {"longitude": "114.3224", "latitude": "-2.8494",
         "acq_date": "2019-09-07", "frp": "8.1", "confidence": "58"},
        {"longitude": "114.3333", "latitude": "-2.8541",
         "acq_date": "2019-09-21", "frp": "16.7", "confidence": "79"},
    ]
    (data / "firms_tileC.json").write_text(json.dumps(hotspots))
    out = tmp_path / "out"
    subprocess.run(
        [sys.executable, str(TOOL), "--out", str(out),
         "--data", str(data)],
        check=True, capture_output=True,
    )
    from PIL import Image

    height = Image.open(out / "heightmap.png")
    assert height.size == (1009, 1009) and height.mode == "I;16"
    albedo = Image.open(out / "albedo.png")
    assert albedo.size == (1009, 1009) and albedo.mode == "RGB"
    meta = json.loads((out / "meta.json").read_text())
    assert meta["bbox"] == list(BBOX)
    assert meta["landscape_n"] == 1009
    assert meta["n_hotspots"] == 2
    assert meta["xy_scale_cm_per_quad"] == round(2000.0 / 1008 * 100, 3)
    masks = json.loads((out / "masks.json").read_text())
    assert masks["size"] == [216, 216]
    assert 0.0 < masks["forest_frac"] < 1.0
    fronts = json.loads((out / "fronts.json").read_text())
    assert fronts[0]["lon"] == 114.3224 and fronts[1]["frp"] == 16.7
