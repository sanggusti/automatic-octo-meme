"""inspect-ai tools: the LM-facing drone action surface.

Tools are factories bound to one episode's bridge + edge perception instance,
so every sample gets isolated simulator state. Docstrings and type
annotations are required by inspect-ai so the model knows how to call them.
"""

from __future__ import annotations

import os

from inspect_ai.tool import ContentImage, ContentText, Tool, tool

from dmb.perception.edge import EdgePerception
from dmb.perception.frames import to_data_url
from dmb.sim.bridge import SimBridge
from dmb.watch.recorder import NullWatcher, Watcher


def edge_report_message(report, image: bytes | None) -> str | list:
    """Text-only or multimodal (text + frame) tool result.

    ``DMB_VISION=text`` forces text-only results so text models (e.g. the
    flywheel teacher) can run the bench; the LM then navigates purely on
    edge reports, which is the intended edge-first architecture.
    """
    detections = ", ".join(f"{d.label}@({d.x},{d.y})" for d in report.detections)
    text = f"{report.summary} Detections: [{detections}]"
    if image is None:
        return text + (" [frame unavailable]" if report.frame_ref else "")
    if os.environ.get("DMB_VISION", "").lower() == "text":
        return text + " [frame withheld: text-only run]"
    return [
        ContentText(text=text),
        ContentImage(image=to_data_url(image), detail="low"),
    ]


def make_drone_tools(
    bridge: SimBridge, edge: EdgePerception, watcher: Watcher | None = None
) -> list[Tool]:
    tools: list[Tool] = []
    watch: Watcher = watcher or NullWatcher()

    def _clock() -> tuple[float, int, int, int]:
        state = bridge.get_state()
        step = int(state.get("steps", 0))
        drone = state.get("drone", {})
        return (
            float(state.get("sim_time", step * 5.0)),
            step,
            int(drone.get("x", 0)),
            int(drone.get("y", 0)),
        )

    def _edge_event(report) -> None:
        t, step, _x, _y = _clock()
        watch.on_event(
            "edge",
            t,
            step,
            trigger=report.trigger,
            summary=report.summary,
            frame_ref=report.frame_ref,
            detections=[
                {"label": d.label, "x": d.x, "y": d.y} for d in report.detections
            ],
        )

    def _with_edge_report(obs_text: str) -> str:
        state = bridge.get_state()
        report = edge.on_step(int(state.get("steps", 0)))
        if report is not None:
            _edge_event(report)
            return f"{obs_text}\n[edge:{report.trigger}] {report.summary}"
        return obs_text

    def _action(tool: str, args: dict, obs_text: str) -> None:
        t, step, x, y = _clock()
        watch.on_event(
            "action", t, step, tool=tool, args=args, obs=obs_text[:500],
            pos=[x, y],
        )

    @tool
    def arm():
        async def execute() -> str:
            """Arm the drone motors.

            Returns:
                Arm result message.
            """
            obs = bridge.act("arm", {}).text
            _action("arm", {}, obs)
            return obs

        return execute

    @tool
    def takeoff():
        async def execute(altitude_m: float) -> str:
            """Take off to an altitude and hover.

            Args:
                altitude_m: Target altitude in metres (must be positive).

            Returns:
                Takeoff result plus any edge perception report.
            """
            obs = bridge.act("takeoff", {"altitude_m": altitude_m})
            _action("takeoff", {"altitude_m": altitude_m}, obs.text)
            return _with_edge_report(obs.text)

        return execute

    @tool
    def goto_location():
        async def execute(x: int, y: int) -> str:
            """Fly to grid coordinates (x, y).

            Args:
                x: Target x coordinate (0-based).
                y: Target y coordinate (0-based).

            Returns:
                Movement result plus any edge perception report.
            """
            obs = bridge.act("goto", {"x": x, "y": y})
            _action("goto_location", {"x": x, "y": y}, obs.text)
            return _with_edge_report(obs.text)

        return execute

    @tool
    def loiter():
        async def execute(seconds: int) -> str:
            """Hold position to let edge perception scan the area.

            Args:
                seconds: How long to loiter.

            Returns:
                Loiter result plus any edge perception report.
            """
            obs = bridge.act("loiter", {"seconds": seconds})
            _action("loiter", {"seconds": seconds}, obs.text)
            return _with_edge_report(obs.text)

        return execute

    @tool
    def land():
        async def execute() -> str:
            """Land at the current position.

            Returns:
                Landing result message.
            """
            obs = bridge.act("land", {}).text
            _action("land", {}, obs)
            return obs

        return execute

    @tool
    def return_to_launch():
        async def execute() -> str:
            """Abort the mission: fly home and land.

            Returns:
                RTL result message.
            """
            obs = bridge.act("rtl", {}).text
            _action("return_to_launch", {}, obs)
            return obs

        return execute

    @tool
    def get_telemetry():
        async def execute() -> str:
            """Read position, altitude, battery, steps, and violations.

            Returns:
                Telemetry summary string.
            """
            state = bridge.get_state()
            drone = state["drone"]
            text = (
                f"pos=({drone['x']},{drone['y']}) alt={drone['altitude_m']}m "
                f"airborne={drone['airborne']} battery={drone['battery_pct']}% "
                f"steps={state['steps']}/{state['step_budget']} "
                f"violations={state['safety_violations']}"
            )
            _action("get_telemetry", {}, text)
            return text

        return execute

    @tool
    def request_edge_report():
        async def execute():
            """Request an on-demand edge perception scan (uses snapshot budget).

            Returns:
                Edge report with detections, snapshot status, and — while
                budget remains — the observation frame image.
            """
            report = edge.on_demand(int(bridge.get_state().get("steps", 0)))
            image = bridge.capture_frame(report.frame_ref) if report.frame_ref else None
            _edge_event(report)
            _action("request_edge_report", {}, report.summary)
            return edge_report_message(report, image)

        return execute

    for factory in (
        arm,
        takeoff,
        goto_location,
        loiter,
        land,
        return_to_launch,
        get_telemetry,
        request_edge_report,
    ):
        tools.append(factory())
    return tools
