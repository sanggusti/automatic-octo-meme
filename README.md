# Disaster Mitigation Bench

Benchmarking language models as **drone navigators** and **reconnaissance
advisors** in simulated 3D disaster environments (forest fire, flash flood,
flood, earthquake, landslide). Eval harness: [inspect-ai](https://inspect.aisi.org.uk/).
Inference: Baseten (paid) + Modal (custom models). All runs tracked.

## Quickstart

```bash
uv venv .venv
VIRTUAL_ENV=$PWD/.venv uv pip install -e ".[dev]"
.venv/bin/python -m pytest -q
XDG_DATA_HOME=$PWD/.inspect-data INSPECT_LOG_DIR=./logs \
INSPECT_TRACE_FILE=./logs/trace.log \
  .venv/bin/inspect eval evals/forest_fire.py --model mockllm/model --limit 1
```

## Docs

Start at [docs/](docs/README.md): architecture, compute split, action
surface, edge perception, scenarios, metrics, inference, tracking, human
evals, assets, runbooks, roadmap.

## Contributing

Issues first, then PR, then merge, then close — no direct pushes to `main`.
See [runbooks](docs/runbooks.md#publishing-flow-required).
