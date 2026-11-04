"""Fetch pinned Fuel models into assets/models/ (sha256-verified).

Reads URLs + hashes from assets/manifest.yaml (single source of truth),
skips downloads whose on-disk zip already matches, extracts each zip into
assets/models/<entry>/ (model:// resolution root for world builders).

Usage: python assets/vegetation/fetch_models.py [--models-dir DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

MANIFEST_SECTIONS = ("vegetation", "emitters", "actors")


def manifest_entries(manifest_path: Path) -> dict[str, dict]:
    import yaml  # noqa: PLC0415

    manifest = yaml.safe_load(manifest_path.read_text())
    entries = {}
    for section in MANIFEST_SECTIONS:
        for key, value in (manifest.get(section, {}) or {}).items():
            if isinstance(value, dict) and "url" in value:
                entries[key] = value
    return entries


def verify_sha(path: Path, sha256: str) -> bool:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest() == sha256


def fetch_all(models_dir: Path, manifest_path: Path) -> list[str]:
    models_dir.mkdir(parents=True, exist_ok=True)
    fetched = []
    for key, entry in sorted(manifest_entries(manifest_path).items()):
        dest = models_dir / f"{key}.zip"
        if dest.exists() and verify_sha(dest, entry["sha256"]):
            print(f"cached {key}")
        else:
            print(f"GET {key} ({entry['url']})", flush=True)
            urllib.request.urlretrieve(entry["url"], dest)
            if not verify_sha(dest, entry["sha256"]):
                dest.unlink(missing_ok=True)
                raise RuntimeError(f"sha256 mismatch for {key}")
        target = models_dir / key
        if not (target / "model.config").exists():
            with zipfile.ZipFile(dest) as zf:
                zf.extractall(target)
        fetched.append(key)
    return fetched


def create_aliases(models_dir: Path) -> list[str]:
    """Symlink each model under its config <name> spellings.

    Fuel model SDFs self-reference ``model://<config-name>`` (e.g.
    grass-plane's SDF wants ``model://grass_plane/...``), so the
    resolution root must carry those spellings too. Both the raw
    <name> and its spaces-to-underscores variant are linked, plus
    every model:// spellings the SDFs actually reference (some
    models self-ref under a different legacy name, e.g.
    standing-person's SDF wants model://person_standing/...).
    """
    import re  # noqa: PLC0415
    import xml.etree.ElementTree as ET  # noqa: PLC0415

    aliases = []
    for target in sorted(models_dir.iterdir()):
        if target.is_symlink() or not target.is_dir():
            continue
        config = target / "model.config"
        if not config.exists():
            continue
        name = ET.fromstring(config.read_text()).findtext("name") or ""
        spellings = {name, name.replace(" ", "_")}
        for sdf in target.glob("*.sdf"):
            for ref in re.findall(r"model://([^/<\"]+)", sdf.read_text()):
                spellings.add(ref.strip())
        for spelling in spellings - {"", target.name}:
            link = models_dir / spelling
            if link.is_symlink() or link.exists():
                link.unlink() if link.is_symlink() else None
                if link.exists() and not link.is_symlink():
                    continue
            link.symlink_to(target.name)
            aliases.append(spelling)
    return aliases


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch pinned Fuel models.")
    parser.add_argument(
        "--models-dir",
        default=str(Path(__file__).resolve().parent.parent / "models"),
    )
    args = parser.parse_args()
    manifest = Path(__file__).resolve().parent.parent / "manifest.yaml"
    fetched = fetch_all(Path(args.models_dir), manifest)
    aliases = create_aliases(Path(args.models_dir))
    print(f"{len(fetched)} models ready: {', '.join(fetched)}")
    print(f"{len(aliases)} aliases: {', '.join(aliases)}")


if __name__ == "__main__":
    sys.exit(main())
