"""Peatland heightfield generator (#50): deterministic terrain + swatches."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "unreal" / "forest_fire" / "tools" / "terrain_gen.py"


def _run(outdir: Path):
    subprocess.run(
        [sys.executable, str(TOOL), "--seed", "7", "--out", str(outdir)],
        check=True,
        capture_output=True,
    )


def _hashes(outdir: Path):
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(outdir.iterdir())
        if p.is_file()
    }


def test_terrain_gen_deterministic(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    _run(first)
    _run(second)
    assert _hashes(first) == _hashes(second)
    assert _hashes(first / "swatches") == _hashes(second / "swatches")


def test_terrain_gen_layout(tmp_path):
    _run(tmp_path)
    lines = (tmp_path / "terrain.obj").read_text().splitlines()
    verts = [ln for ln in lines if ln.startswith("v ")]
    faces = [ln for ln in lines if ln.startswith("f ")]
    assert len(verts) == 51 * 51
    assert len(faces) == 2 * 50 * 50
    heights = json.loads((tmp_path / "heights.json").read_text())
    assert heights["step_m"] == 1.0 and heights["n"] == 51
    assert len(heights["heights_cm"]) == 51
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["seed"] == 7
    assert meta["spawn_cm"]["x"] == 0.0 and meta["spawn_cm"]["y"] == 0.0


def test_terrain_gen_swatches_bgr(tmp_path):
    """Swatch PNGs are readable and deliberately B-over-R ordered.

    UE 5.6's texture import renders these PNGs R/B-swapped (live-verified:
    flames vivid blue instead of orange), so the writer pre-swaps bytes.
    PIL therefore reads flame as (26, 122, 255), which renders as the
    documented (255, 122, 26) in-engine. Do not "fix" the order without a
    packaged capture proving flames still orange.
    """
    from PIL import Image

    _run(tmp_path)
    swatches = tmp_path / "swatches"
    assert len(list(swatches.glob("*.png"))) == 11
    flame = Image.open(swatches / "flame.png").convert("RGB")
    assert flame.size == (4, 4)
    assert flame.getpixel((0, 0)) == (26, 122, 255)
    ground = Image.open(swatches / "ground.png").convert("RGB")
    assert ground.getpixel((0, 0)) == (18, 29, 43)
