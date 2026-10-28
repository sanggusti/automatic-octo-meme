"""Scenario definitions and seeded sample generation.

A scenario YAML describes a disaster type; a benchmark sample is
``(scenario, seed)`` expanded deterministically by :func:`build_samples`.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from inspect_ai.dataset import Sample

from dmb.difficulty import difficulty_score

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"

REQUIRED_KEYS = (
    "name",
    "kind",
    "description",
    "grid",
    "victims",
    "hazards",
    "weather",
    "difficulty",
)


@dataclass(frozen=True)
class ScenarioConfig:
    name: str
    kind: str
    description: str
    raw: dict = field(compare=False)

    @property
    def grid(self) -> dict:
        return dict(self.raw.get("grid", {}))

    @property
    def victim_spec(self) -> dict:
        return dict(self.raw.get("victims", {}))

    @property
    def hazards(self) -> list:
        return list(self.raw.get("hazards", []))

    @property
    def weather(self) -> list:
        return list(self.raw.get("weather", []))

    @property
    def difficulty(self) -> dict:
        return dict(self.raw.get("difficulty", {}))


def load_scenario(name: str, scenarios_dir: str | Path = SCENARIOS_DIR) -> ScenarioConfig:
    path = Path(scenarios_dir) / f"{name}.yaml"
    raw = yaml.safe_load(path.read_text())
    missing = [k for k in REQUIRED_KEYS if k not in raw]
    if missing:
        raise ValueError(f"Scenario {name} missing keys: {missing}")
    return ScenarioConfig(name=raw["name"], kind=raw["kind"], description=raw["description"], raw=raw)


def list_scenarios(scenarios_dir: str | Path = SCENARIOS_DIR) -> list[str]:
    return sorted(p.stem for p in Path(scenarios_dir).glob("*.yaml"))


def world_hash(scenario: str, seed: int, victim_placements: list[dict]) -> str:
    """Deterministic fingerprint: same (scenario, seed) must hash equal."""
    payload = json.dumps(
        {"scenario": scenario, "seed": seed, "placements": victim_placements},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _place_victims(rng: random.Random, config: ScenarioConfig) -> list[dict]:
    grid = config.grid
    width, height = int(grid.get("width", 10)), int(grid.get("height", 10))
    placements: list[dict] = []
    for category, spec in config.victim_spec.get("categories", {}).items():
        count = rng.randint(int(spec.get("min", 0)), int(spec.get("max", 0)))
        for _ in range(count):
            placements.append(
                {
                    "category": category,
                    "x": rng.randrange(width),
                    "y": rng.randrange(height),
                    "mobility": spec.get("mobility", "static"),
                }
            )
    return placements


def build_samples(
    scenario: str,
    seeds: list[int],
    *,
    scenarios_dir: str | Path = SCENARIOS_DIR,
    mission_brief: str | None = None,
) -> list[Sample]:
    """Expand (scenario, seeds) into inspect-ai samples with fixed metadata."""
    config = load_scenario(scenario, scenarios_dir)
    samples: list[Sample] = []
    for seed in seeds:
        rng = random.Random(seed)
        placements = _place_victims(rng, config)
        brief = mission_brief or (
            f"You are the drone navigator for a {config.kind} disaster response "
            f"mission ({config.name}). {config.description} Locate victims and "
            "report their positions. Minimise flight time and avoid hazard zones."
        )
        samples.append(
            Sample(
                input=brief,
                id=f"{scenario}-seed-{seed}",
                metadata={
                    "scenario": scenario,
                    "seed": seed,
                    "grid": config.grid,
                    "victim_placements": placements,
                    "hazards": config.hazards,
                    "weather": config.weather,
                    "difficulty": config.difficulty,
                    "dynamics": config.raw.get("dynamics", {}),
                    "difficulty_score": difficulty_score(
                        {
                            "grid": config.grid,
                            "victim_placements": placements,
                            "hazards": config.hazards,
                            "difficulty": config.difficulty,
                        }
                    ),
                    "world_hash": world_hash(scenario, seed, placements),
                },
            )
        )
    return samples
