# Peatforest bulk data (lives on HuggingFace, not in git)

Tile-C GIS + staged inputs + generator outputs (~1.5 GB) are published as a
versioned HuggingFace dataset. This directory keeps only this entrypoint;
the bulk files stay untracked.

- **Dataset:** [sanggusti/peatforest-tilec-seed7](https://huggingface.co/datasets/sanggusti/peatforest-tilec-seed7) (tag: `3D maps`)
- **Pins:** `assets/manifest.yaml` (`gis:` + `pbr:` sections — URL + version + sha256 + license)
- **Report:** `docs/peatforest-report.md` (tile reasoning, seeds, counts, keyframes)
- **Build laws:** `.agents/skills/unreal-colosseum/SKILL.md`, `docs/track2-runbook.md` ss8.9-14

Fetch into this directory:

```bash
hf download sanggusti/peatforest-tilec-seed7 --repo-type dataset \
  --local-dir data/peatforest_dl
# then arrange the builder-expected layout under data/peatforest/:
#   *.tif + firms_tileC.json          <- gis/
#   ue_gen/ ue_inputs/ assets_raw/    <- same names
#   ../firms/                         <- firms_raw/ (raw FIRMS archive)
```

Verify after download:

```bash
cd data/peatforest_dl && sha256sum -c sha256sums.txt
```

Regenerate instead of downloading (seed 7, deterministic):

```bash
python unreal/peatforest/tools/gen_textures.py --seed 7 --out data/peatforest/ue_gen
python unreal/peatforest/tools/gen_terrain.py   --seed 7 --out data/peatforest/ue_gen
python unreal/peatforest/tools/gen_groves.py --gen data/peatforest/ue_gen \
  --out data/peatforest/ue_gen --seed 7
```
