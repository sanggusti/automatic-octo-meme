"""OBJ writers emit Z-up meshes with +Z/outward normals (#65).

UE imports Z verbatim (Y-up heightfields render as vertical walls) but
NEGATES Y: +y OBJ content landed at NED -y while builder-placed
markers at +Y landed +y (bisected live). Writers therefore emit
y=-east_cm; the sign is pinned below (a flip would strand terrain and
fire markers on opposite sides of the tile edge).
"""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds

ROOT = Path(__file__).resolve().parent.parent
BBOX = (114.318, -2.86, 114.336, -2.842)


def _parse_obj(obj_path):
    verts, uvs, faces = [], [], []
    for ln in Path(obj_path).read_text().splitlines():
        if ln.startswith("v "):
            verts.append([float(x) for x in ln.split()[1:4]])
        elif ln.startswith("vt "):
            uvs.append([float(x) for x in ln.split()[1:3]])
        elif ln.startswith("f "):
            faces.append([int(x.split("/")[0]) - 1 for x in ln.split()[1:4]])
    return np.array(verts), uvs, faces


def _face_normal_mean(obj_path):
    v, _, faces = _parse_obj(obj_path)
    n = np.zeros(3)
    for a, b, c in faces[:: max(1, len(faces) // 2000)]:
        n += np.cross(v[b] - v[a], v[c] - v[a])
    norm = np.linalg.norm(n)
    return (n / norm if norm > 0 else n), v.min(axis=0), v.max(axis=0)


def _face_count(obj_path):
    return sum(1 for ln in Path(obj_path).read_text().splitlines()
               if ln.startswith("f "))


def test_forest_fire_terrain_zup(tmp_path):
    tool = ROOT / "unreal" / "forest_fire" / "tools" / "terrain_gen.py"
    subprocess.run([sys.executable, str(tool), "--seed", "7", "--out", str(tmp_path)],
                   check=True, capture_output=True)
    n, lo, hi = _face_normal_mean(tmp_path / "terrain.obj")
    assert n[2] > 0.99, n
    # ForestFire terrain has real hills: flat means z-span well below extent
    # (a Y-up wall would have z-span ~= extent).
    assert hi[0] - lo[0] > 5 * (hi[2] - lo[2])
    # Pre-mirrored east: tile spans y in [-5000, 0], not [0, 5000].
    assert hi[1] == 0.0 and lo[1] == -5000.0, (lo[1], hi[1])


def _synth_data(data):
    rng = np.random.RandomState(7)
    yy, xx = np.mgrid[0:65, 0:65]
    arr = (8.0 + 0.09 * xx + 0.05 * yy  # gentle peat gradient, not white noise
           + 0.3 * np.sin(xx / 9.0) * np.cos(yy / 7.0)
           + rng.rand(65, 65) * 0.2).astype("float32")
    with rasterio.open(data / "copernicus_dem_S03E114.tif", "w", driver="GTiff",
                       height=65, width=65, count=1, dtype="float32",
                       crs="EPSG:4326",
                       transform=from_bounds(*BBOX, 65, 65)) as dst:
        dst.write(arr, 1)
    arr = rng.choice([10, 20, 30, 40, 80, 90], size=(40, 40)).astype("uint8")
    with rasterio.open(data / "worldcover_2021_S03E114.tif", "w", driver="GTiff",
                       height=40, width=40, count=1, dtype="uint8",
                       crs="EPSG:4326",
                       transform=from_bounds(*BBOX, 40, 40)) as dst:
        dst.write(arr, 1)
    arr = (rng.rand(3, 50, 50) * 255).astype("uint8")
    with rasterio.open(data / "s2_20191023_T50MKB_visual.tif", "w", driver="GTiff",
                       height=50, width=50, count=3, dtype="uint8",
                       crs="EPSG:4326",
                       transform=from_bounds(*BBOX, 50, 50)) as dst:
        dst.write(arr)
    hot = [{"longitude": "114.3224", "latitude": "-2.8494", "acq_date": "2019-09-07",
            "frp": "8.1", "confidence": "58"}]
    (data / "firms_tileC.json").write_text(json.dumps(hot))
    (data.parent / "firms_tileC.json").write_text(json.dumps(hot))  # gen.parent for groves


def test_peat_meshes_zup(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    _synth_data(data)
    gen = tmp_path / "gen"
    subprocess.run(
        [sys.executable, str(ROOT / "unreal" / "peatforest" / "tools" / "gen_terrain.py"),
         "--seed", "7", "--out", str(gen), "--data", str(data)],
        check=True, capture_output=True)
    subprocess.run(
        [sys.executable, str(ROOT / "unreal" / "peatforest" / "tools" / "gen_groves.py"),
         "--gen", str(gen), "--out", str(gen)],
        check=True, capture_output=True)
    extents = {}
    for name in ("terrain.obj", "terrain_collision.obj"):
        n, lo, hi = _face_normal_mean(gen / name)
        assert n[2] > 0.99, (name, n)
        assert hi[0] - lo[0] > 100 * (hi[2] - lo[2]), name
        # Pre-mirrored east: tile spans y in [-200000, 0].
        assert hi[1] == 0.0 and lo[1] == -200000.0, (name, lo[1], hi[1])
        extents[name] = (lo, hi)
    # Visual terrain carries planar UVs for the S2 albedo + tiled detail
    # (the hidden shell needs none).
    v, uvs, faces = _parse_obj(gen / "terrain.obj")
    assert len(uvs) == len(v) > 0, "terrain v/vt 1:1"
    # Collision shell must cover the same footprint as the visual mesh
    # (a meters-vs-cm slip shrinks it to a 20 m corner patch).
    for name in ("terrain.obj", "terrain_collision.obj"):
        lo, hi = extents[name]
        assert hi[0] - lo[0] == max(e[1][0] - e[0][0] for e in extents.values()), name
    # Sidecar units: heights.json is CM (key says heights_cm) scaled to the
    # DEM meters in meta.json. Meters here buried every tree and spawned
    # the drone 6.8 m underground (live #65).
    meta = json.loads((gen / "meta.json").read_text())
    hs = json.loads((gen / "heights.json").read_text())["heights_cm"]
    flat = [v for row in hs for v in row]
    hmin, hmax = min(flat), max(flat)
    assert hmin >= meta["dem_min_m"] * 100.0 - 1.0
    assert hmax <= meta["dem_max_m"] * 100.0 + 1.0
    assert (hmax - hmin) > 0.5 * (meta["dem_max_m"] - meta["dem_min_m"]) * 100.0
    assert hmax > 100.0, "heights look like meters, not cm"
    # Groves: non-empty parts stand +Z with finite normals, carry UVs
    # (masked leaf/frond materials need them) + vertex tints, and valid
    # indices. (A part may legitimately be empty, e.g. zero charred
    # trees near the hotspot.)
    checked = 0
    for name in ("trunk.obj", "canopy.obj", "frond.obj", "charred.obj"):
        if _face_count(gen / name) == 0:
            continue
        checked += 1
        v, uvs, faces = _parse_obj(gen / name)
        n, lo, hi = _face_normal_mean(gen / name)
        assert np.isfinite(n).all(), name
        assert hi[2] > lo[2], name
        assert len(uvs) == len(v) > 0, (name, "v/vt 1:1")
        assert max(max(f) for f in faces) < len(v), (name, "index range")
        assert min(min(f) for f in faces) >= 0, (name, "index range")
    assert checked >= 2, "synthetic run produced no grove geometry"
    # Variant split recorded and deterministic.
    variants = json.loads((gen / "variants.json").read_text())
    assert set(variants) == {"emergent", "palm", "round", "bush", "charred",
                             "logs"}, variants
    placement_n = len(json.loads((gen / "placements.json").read_text())["trees"])
    assert (variants["emergent"] + variants["palm"] + variants["round"]
            + variants["bush"] + variants["charred"] == placement_n)
