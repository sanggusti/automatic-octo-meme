"""Non-LM baseline agents: greedy coverage + random walk.

Pure policies over (bridge, edge) — no model calls — so they run fast,
deterministically, and provider-free. Used by the CI benchmark
(tests/test_baselines.py) and by thin inspect-ai solver wrappers for
task-level comparisons.
"""

from __future__ import annotations

import random

from inspect_ai.solver import Generate, Solver, TaskState, solver

from dmb.perception.edge import FrameBudget, StubEdgePerception, TriggerConfig
from dmb.sim.bridge import MockBridge


def _step(bridge: MockBridge, edge: StubEdgePerception, action: str, params: dict | None = None):
    obs = bridge.act(action, params or {})
    edge.on_step(bridge.get_state()["steps"])
    return obs


def greedy_policy(
    bridge: MockBridge, edge: StubEdgePerception, *, stride: int = 3, max_moves: int | None = None
) -> None:
    """Lawnmower sweep: arm, takeoff, visit every stride-th cell, land."""
    _step(bridge, edge, "arm")
    _step(bridge, edge, "takeoff", {"altitude_m": 10})
    moves = 0
    for y in range(0, bridge.height, stride):
        xs = range(0, bridge.width, stride)
        if (y // stride) % 2 == 1:
            xs = reversed(list(xs))
        for x in xs:
            if bridge.get_state()["steps"] >= bridge.step_budget - 2:
                break
            if max_moves is not None and moves >= max_moves:
                break
            _step(bridge, edge, "goto", {"x": x, "y": y})
            moves += 1
        else:
            continue
        break
    _step(bridge, edge, "land")


def random_policy(
    bridge: MockBridge, edge: StubEdgePerception, *, rng: random.Random, max_moves: int = 20
) -> None:
    """Random legal moves, then land."""
    _step(bridge, edge, "arm")
    _step(bridge, edge, "takeoff", {"altitude_m": 10})
    for _ in range(max_moves):
        if bridge.get_state()["steps"] >= bridge.step_budget - 2:
            break
        _step(
            bridge, edge, "goto",
            {"x": rng.randrange(bridge.width), "y": rng.randrange(bridge.height)},
        )
    _step(bridge, edge, "land")


def _episode(metadata: dict, policy: str, *, stride: int = 3, max_moves: int | None = None) -> dict:
    bridge = MockBridge.from_metadata(dict(metadata))
    edge = StubEdgePerception(bridge, TriggerConfig(), FrameBudget(max_snapshots=8))
    if policy == "greedy":
        greedy_policy(bridge, edge, stride=stride, max_moves=max_moves)
    elif policy == "random":
        random_policy(bridge, edge, rng=random.Random(int(metadata.get("seed", 0))))
    else:
        raise ValueError(f"unknown policy: {policy}")
    return bridge.get_state()


def run_baseline(metadata: dict, policy: str, **kwargs) -> dict:
    """Run one policy episode; return final sim state for scorers."""
    return _episode(metadata, policy, **kwargs)


@solver
def heuristic_mission() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state.store.set("sim_state", _episode(dict(state.metadata), "greedy"))
        return state

    return solve


@solver
def random_mission() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state.store.set("sim_state", _episode(dict(state.metadata), "random"))
        return state

    return solve
