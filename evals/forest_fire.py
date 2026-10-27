"""Sample mission eval: forest-fire drone navigation on the mock backend.

Each sample builds an isolated MockBridge + edge perception pair, runs a
ReAct agent over the drone tools, then stores final sim state for the
deterministic mission scorer.
"""

from inspect_ai import Task, task
from inspect_ai.agent import react, run
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import Tool
from inspect_ai.util import message_limit

from dmb.perception.edge import FrameBudget, StubEdgePerception, TriggerConfig
from dmb.scenarios import build_samples
from dmb.scorers.mission import mission_score
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


@task
def forest_fire():
    return Task(
        dataset=build_samples("forest_fire", seeds=[1, 2, 3]),
        solver=[drone_mission()],
        scorer=mission_score(),
    )
