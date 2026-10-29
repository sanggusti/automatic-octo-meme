"""Shared mission solver: every drone-navigation task uses this.

Builds an isolated episode (bridge + edge perception + tools) from sample
metadata, runs a ReAct agent with a hard message cap, and stores final sim
state for the deterministic mission scorer.
"""

from inspect_ai.agent import react, run
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import Tool
from inspect_ai.util import message_limit

from dmb.config import Settings
from dmb.perception.edge import FrameBudget, StubEdgePerception, TriggerConfig
from dmb.sim.assets import assert_mission_capable, load_drone_spec
from dmb.sim.bridge import GazeboSITLBridge, MockBridge
from dmb.tools.drone import make_drone_tools
from dmb.watch import watcher_from_env


def _bridge_for_backend(backend: str):
    if backend == "gazebo-sitl":
        return GazeboSITLBridge
    if backend == "mock":
        return MockBridge
    raise ValueError(f"Unknown DMB_SIM_BACKEND: {backend!r} (want mock|gazebo-sitl)")


@solver
def drone_mission() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        backend = Settings.from_env().sim_backend
        spec_name = str(dict(state.metadata).get("drone_spec", "quad_iris_class"))
        assert_mission_capable(load_drone_spec(spec_name))
        bridge = _bridge_for_backend(backend).from_metadata(dict(state.metadata))
        tod = dict(state.metadata).get("time_of_day_active") or "day"
        edge = StubEdgePerception(
            bridge,
            TriggerConfig(time_of_day=str(tod)),
            FrameBudget(max_snapshots=8),
        )
        watcher = watcher_from_env(str(state.sample_id))
        watcher.on_start({**dict(state.metadata), "backend": backend})
        tools: list[Tool] = make_drone_tools(bridge, edge, watcher)
        agent = react(
            prompt=(
                "You are a disaster-response drone navigator piloting a "
                "simulated drone through FUNCTION CALLS. Rules: act ONLY "
                "through function calls — plain text changes nothing in the "
                "simulator, so never narrate an action without emitting its "
                "matching function call in the same turn. Use the flight "
                "tools to search the area, rely on edge perception reports, "
                "minimise steps, stay out of hazard zones, then land and "
                "submit a summary of victim positions."
            ),
            tools=tools,
        )
        # Hard cap: a model that never submits must still terminate.
        agent_state, _limit_error = await run(
            agent, state.messages, [message_limit(50)]
        )
        state.messages = agent_state.messages
        state.output = agent_state.output
        final = bridge.get_state()
        state.store.set("sim_state", final)
        watcher.on_end({"state": final})
        bridge.close()
        return state

    return solve
