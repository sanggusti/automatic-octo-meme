"""inspect-ai tools: the LM-facing drone action surface.

Tools are factories bound to one episode's bridge + edge perception instance,
so every sample gets isolated simulator state. Docstrings and type
annotations are required by inspect-ai so the model knows how to call them.
"""

from __future__ import annotations

from inspect_ai.tool import ContentImage, ContentText, Tool, tool

from dmb.perception.edge import EdgePerception
from dmb.perception.frames import to_data_url
from dmb.sim.bridge import SimBridge


def edge_report_message(report, image: bytes | None) -> str | list:
    """Text-only or multimodal (text + frame) tool result."""
    detections = ", ".join(f"{d.label}@({d.x},{d.y})" for d in report.detections)
    text = f"{report.summary} Detections: [{detections}]"
    if image is None:
        return text + (" [frame unavailable]" if report.frame_ref else "")
    return [
        ContentText(text=text),
        ContentImage(image=to_data_url(image), detail="low"),
    ]


def _with_edge_report(obs_text: str, bridge: SimBridge, edge: EdgePerception) -> str:
    state = bridge.get_state()
    report = edge.on_step(int(state.get("steps", 0)))
    if report is not None:
        return f"{obs_text}\n[edge:{report.trigger}] {report.summary}"
    return obs_text


def make_drone_tools(bridge: SimBridge, edge: EdgePerception) -> list[Tool]:
    tools: list[Tool] = []

    @tool
    def arm():
        async def execute() -> str:
            """Arm the drone motors.

            Returns:
                Arm result message.
            """
            return bridge.act("arm", {}).text

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
            return _with_edge_report(obs.text, bridge, edge)

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
            return _with_edge_report(obs.text, bridge, edge)

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
            return _with_edge_report(obs.text, bridge, edge)

        return execute

    @tool
    def land():
        async def execute() -> str:
            """Land at the current position.

            Returns:
                Landing result message.
            """
            return bridge.act("land", {}).text

        return execute

    @tool
    def return_to_launch():
        async def execute() -> str:
            """Abort the mission: fly home and land.

            Returns:
                RTL result message.
            """
            return bridge.act("rtl", {}).text

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
            return (
                f"pos=({drone['x']},{drone['y']}) alt={drone['altitude_m']}m "
                f"airborne={drone['airborne']} battery={drone['battery_pct']}% "
                f"steps={state['steps']}/{state['step_budget']} "
                f"violations={state['safety_violations']}"
            )

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
