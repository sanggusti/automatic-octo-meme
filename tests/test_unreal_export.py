"""UE export path (#50): foliage CSV + fire-schedule JSON run green."""

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOREST = ROOT / "unreal" / "forest_fire"


def test_export_foliage_runs(tmp_path):
    subprocess.run(
        [sys.executable, str(FOREST / "export_foliage.py"),
         "forest_fire_peat", "--seed", "1", "--out", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    with (tmp_path / "foliage.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 100  # 10x10 grid, fuel 0.5 everywhere
    peat_rows = [r for r in rows if float(r["peat_depth"]) > 0]
    assert len(peat_rows) == 50  # eastern block x >= 5
    assert {r["species"] for r in rows} <= {
        "peat_swamp_tree", "canopy_tree", "underbrush"
    }
    assert all(float(r["flammability"]) == 0.5 for r in rows)
    assert all(float(r["x_m"]) == int(r["x_cell"]) * 5.0 for r in rows)


def test_export_fire_schedule_runs(tmp_path):
    subprocess.run(
        [sys.executable, str(FOREST / "export_fire_schedule.py"),
         "forest_fire_peat", "--weather", "drought-extreme",
         "--steps", "60", "--out", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    schedule = json.loads((tmp_path / "fire_schedule.json").read_text())
    assert schedule["scenario"] == "forest_fire_peat"
    assert schedule["weather"] == "drought-extreme"
    assert schedule["summary"] == {
        "first_breakout": 19,
        "total_ignited": 57,
        "total_smolder": 50,
    }
    assert len(schedule["steps"]) == 61
    first, last = schedule["steps"][0], schedule["steps"][60]
    assert first["burning"] == [] and first["haze"] == 0.08
    assert last["haze"] == 1.0
    assert all(
        later["haze"] >= step["haze"] - 1e-9
        for step, later in zip(schedule["steps"][:20], schedule["steps"][1:21])
    )
