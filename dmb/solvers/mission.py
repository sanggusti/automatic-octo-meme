"""Shared mission solver: every drone-navigation task uses this.

Builds an isolated episode (bridge + edge perception + tools) from sample
metadata, runs a ReAct agent with a hard message cap, and stores final sim
state for the deterministic mission scorer.
"""

from inspect_ai.agent import react, run
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import Tool
from inspect_ai.util import message_limit

from dmb.perception.edge import FrameBudget, StubEdgePerception, TriggerConfig
from dmb.sim.bridge import MockBridge
from dmb.tools.drone import make_drone_tools


@solver
def drone_mission() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        bridge = MockBridge.from_metadata(dict(state.metadata))
        edge = StubEdgePerception(
            bridge,
            TriggerConfig(),
            FrameBudget(max_snapshots=8),
        )
        tools: list[Tool] = make_drone_tools(bridge, edge)
        agent = react(
            prompt=(
                "You are a disaster-response drone navigator. Use the flight "
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
        state.store.set("sim_state", bridge.get_state())
        bridge.close()
        return state

    return solve
