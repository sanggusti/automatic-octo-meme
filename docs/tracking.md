# Tracking — Reproducibility Contract

## Sources of truth

1. **inspect-ai eval logs** (`.eval`): full transcripts, tool calls, scores.
   View with `inspect view`. Local dirs are redirected into the repo during
   sandboxed runs (`INSPECT_LOG_DIR`, `INSPECT_TRACE_FILE`, `XDG_DATA_HOME`;
   see [runbooks](runbooks.md)).
2. **`RunRegistry`** (`dmb/registry.py`): `runs/<run_id>/` holds
   `config.json` (task, model, scenario, seeds, limits, git sha),
   `scores.json`, `events.jsonl`, and eval-log pointers.
3. **Git**: code + scenario + asset versions. The registry records the HEAD
   sha of every run.

## Rules

- No result is real until a registry entry + eval log exist for it.
- Seeds are explicit and checked in with the task; `world_hash` proves the
  world a score came from.
- `runs/` and `logs/` are git-ignored working outputs; promote only
  curated summaries (tables in issues/PRs, golden scores in tests).
- Provider runs additionally record model slug + endpoint + price tier in
  the run notes so cost is auditable.

## Reading results

- Single run: `inspect view` on the `.eval` log.
- Across runs: aggregate `runs/*/scores.json` (aggregation script is a
  roadmap item; until then, small ad-hoc scripts, kept with the analysis).
