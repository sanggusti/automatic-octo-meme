"""Fidelity-v2 pins: dense canopy, BGR pre-swap, path network (#68-#72).

Data-dependent (reads data/peatforest/ue_gen), like test_obj_winding.py.
Regenerate with: gen_textures.py --seed 7 (plus --pbr-src) and
gen_terrain.py --seed 7 before running.
"""
import json
import math
from pathlib import Path

from PIL import Image

GEN = Path("data/peatforest/ue_gen")


def _rgba(name):
    im = Image.open(GEN / name).convert("RGBA")
    return list(im.getdata())


def test_leaf_card_dense_cover():
    # Sparse cards (28%) masked whole crowns away -> sticks.
    px = _rgba("tex/leaf_card.png")
    frac = sum(1 for p in px if p[3] > 51) / len(px)
    assert frac > 0.80, frac


def test_flame_bytes_bgr_swapped():
    # Authored orange (R>B); on-disk bytes must be pre-swapped (R<B)
    # for the UE import path that renders R/B swapped.
    px = _rgba("tex/flame.png")
    n = len(px)
    r = sum(p[0] for p in px) / n
    b = sum(p[2] for p in px) / n
    assert r < b, (r, b)


def test_pbr_mud_bytes_bgr_swapped():
    im = Image.open(GEN / "pbr/mud_diff.jpg").convert("RGB")
    px = list(im.getdata())
    n = len(px)
    r = sum(p[0] for p in px) / n
    b = sum(p[2] for p in px) / n
    assert r < b, (r, b)  # authored brown (100,83,51), swapped on disk


def test_flame_tongue_density():
    # Sparse tongues read as a translucent scrim, not fire (live v2.2).
    px = _rgba("tex/flame.png")
    frac = sum(1 for p in px if p[3] > 128) / len(px)
    assert frac > 0.35, frac


def test_smoke_column_density():
    px = _rgba("tex/smoke.png")
    frac = sum(1 for p in px if p[3] > 84) / len(px)
    assert frac > 0.50, frac


def test_clouds_broken_cover():
    px = _rgba("tex/clouds.png")
    frac = sum(1 for p in px if p[3] > 51) / len(px)
    assert 0.30 < frac < 0.80, frac


def test_paths_network_shape():
    pj = json.loads((GEN / "paths.json").read_text())
    assert pj["seed"] == 7
    assert len(pj["paths"]) == 3
    for path in pj["paths"]:
        assert len(path) == 36
        for x, y in path:
            assert 60 <= x <= 1940 and 60 <= y <= 1940, (x, y)
        length = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
        assert length > 500.0, length


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def test_path_corridor_clear_of_trunks():
    pj = json.loads((GEN / "paths.json").read_text())
    segs = [(a[0], a[1], b[0], b[1]) for path in pj["paths"]
            for a, b in zip(path, path[1:])]
    trees = json.loads((GEN / "placements.json").read_text())["trees"]
    assert len(trees) >= 10000, len(trees)  # lush pass: 16k cap
    worst = min(min(_seg_dist(t["x_m"], t["y_m"], *s) for s in segs) for t in trees)
    assert worst > 3.4, worst  # generator carves 3.5 m


def test_paths_obj_topology():
    lines = (GEN / "paths.obj").read_text().splitlines()
    nv = sum(1 for L in lines if L.startswith("v "))
    nf = sum(1 for L in lines if L.startswith("f "))
    assert nv == 3 * 36 * 2, nv
    assert nf == 3 * 35 * 2, nf


def test_variants_cover_all_trees():
    counts = json.loads((GEN / "variants.json").read_text())
    total = sum(counts[k] for k in ("emergent", "palm", "round", "bush", "charred"))
    n = json.loads((GEN / "placements.json").read_text())["count"]
    assert total == n, counts  # every placed tree gets a variant


def test_dirt_flat_tone():
    # Path swatch: opaque peat-dirt brown (authored RGB, pre-swap bytes
    # are BGR so on-disk R<B like every authored warm tone).
    im = Image.open(GEN / "tex/dirt_flat.png").convert("RGBA")
    px = list(im.getdata())
    n = len(px)
    assert all(p[3] == 255 for p in px)
    r = sum(p[0] for p in px) / n
    g = sum(p[1] for p in px) / n
    b = sum(p[2] for p in px) / n
    assert r < b and 40 < g < 110, (r, g, b)


def test_paths_obj_up_normals():
    # Ribbon needs explicit +Z normals: importer-computed ones from the
    # down-wound strip lit unpredictably bright (live v3).
    lines = (GEN / "paths.obj").read_text().splitlines()
    nv = sum(1 for L in lines if L.startswith("v "))
    nn = sum(1 for L in lines if L.startswith("vn "))
    assert nn == nv > 0, (nv, nn)
    assert all(L.split()[3] == "1.0000" for L in lines
               if L.startswith("vn "))


def test_grove_smooth_normals():
    # Missing vn shades each lat band flat -> striped crowns (live).
    for name in ("trunk", "canopy", "frond", "charred"):
        lines = (GEN / f"{name}.obj").read_text().splitlines()
        nv = sum(1 for L in lines if L.startswith("v "))
        nn = sum(1 for L in lines if L.startswith("vn "))
        assert nn == nv > 0, (name, nv, nn)
        faces = [L for L in lines if L.startswith("f ")]
        assert all(len(t.split("/")) == 3 for L in faces[:50] for t in L.split()[1:]), name
        vns = [L for L in lines if L.startswith("vn ")]
        for L in vns[:200:37]:
            x, y, z = (float(v) for v in L.split()[1:4])
            assert abs(math.sqrt(x * x + y * y + z * z) - 1.0) < 0.01, L
