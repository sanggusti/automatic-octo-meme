"""Aggregation: registry rows -> markdown + CSV."""

import json

from dmb.aggregate import _load_rows, render_csv, render_markdown


def _write_run(root, run_id, model, samples):
    path = root / run_id
    path.mkdir(parents=True, exist_ok=True)
    (path / "config.json").write_text(
        json.dumps({"run_id": run_id, "task": "t", "model": model, "scenario": "pack"})
    )
    (path / "scores.json").write_text(json.dumps({"samples": samples}))


def _sample(sid, scenario, composite):
    return {
        "sample_id": sid,
        "scenario": scenario,
        "seed": 1,
        "scores": {
            "rescue_recall": composite,
            "containment": composite,
            "efficiency": composite,
            "safety": 1.0,
            "composite": composite,
        },
        "error": None,
    }


def test_table_groups_and_averages(tmp_path):
    _write_run(
        tmp_path, "r1", "mA",
        [_sample("a-1", "forest_fire", 0.5), _sample("a-2", "forest_fire", 0.7)],
    )
    _write_run(tmp_path, "r2", "mA", [_sample("b-1", "tsunami", 1.0)])
    (tmp_path / "empty-dir").mkdir()  # no config/scores: skipped
    rows = _load_rows(tmp_path)
    assert len(rows) == 3
    md = render_markdown(rows)
    assert "| mA | forest_fire | 2 | 0.600±0.141 |" in md
    assert "| mA | tsunami | 1 | 1.000 |" in md


def test_csv_has_full_vectors(tmp_path):
    _write_run(tmp_path, "r1", "mA", [_sample("a-1", "forest_fire", 0.5)])
    csv_text = render_csv(_load_rows(tmp_path))
    header, body = csv_text.strip().splitlines()
    assert header.startswith("run_id,task,model,scenario,seed,sample_id,")
    assert body.startswith("r1,t,mA,forest_fire,1,a-1,")
    assert body.count("0.5") >= 4


def test_empty_registry_renders_header(tmp_path):
    assert render_markdown(_load_rows(tmp_path)).startswith("| model |")
