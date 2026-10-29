"""Manifest pins (#17/#18/#19): every entry has license + (url+sha256 | generator)."""

from pathlib import Path

import yaml

MANIFEST = Path(__file__).resolve().parent.parent / "assets" / "manifest.yaml"


def _entries(node, path=""):
    if isinstance(node, dict) and ("url" in node or "generator" in node or "params" in node):
        yield path, node
        return
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _entries(value, f"{path}/{key}" if path else key)


def test_manifest_entries_pinned():
    manifest = yaml.safe_load(MANIFEST.read_text())
    entries = list(_entries(manifest))
    assert len(entries) >= 6
    for path, entry in entries:
        assert entry.get("license"), f"{path} missing license"
        if "generator" in entry:
            continue
        if "params" in entry:  # drone specs: source URLs, hashes N/A (git tags)
            assert entry["params"].startswith("https://"), path
            assert entry["model"].startswith("https://"), path
            continue
        assert entry["url"].startswith("https://fuel.gazebosim.org/"), path
        assert "tip" not in entry["url"] and "latest" not in entry["url"], path
        sha = entry.get("sha256", "")
        assert len(sha) == 64 and all(c in "0123456789abcdef" for c in sha), path


def test_tree_placement_runs(tmp_path):
    import json
    import subprocess
    import sys

    script = Path(__file__).resolve().parent.parent / "assets" / "vegetation" / "place_trees.py"
    subprocess.run(
        [sys.executable, str(script), "forest_fire", "--seed", "1", "--out", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    sdf = (tmp_path / "vegetation.sdf").read_text()
    assert sdf.count("<include>") == 100  # 10x10 grid, fuel 0.7 everywhere
    tags = json.loads((tmp_path / "fuel_tags.json").read_text())
    assert len(tags) == 100
    assert all(v == 0.7 for v in tags.values())
    assert 'model://Pine Tree' in sdf and 'model://Oak tree' in sdf
