"""Recon-advisor task stub: LM directs humans in a disaster zone.

v0 runs the guidance-generation half only (prompt -> instructions). Grading
follows docs/human-evals.md: rubric-graded by a human (the operator can be a
grader or a baseline participant), plus a simulated human-actor check in the
recon workstream.
"""

from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.solver import generate, system_message


@task
def recon_advisor():
    return Task(
        dataset=[
            Sample(
                input=(
                    "Flash flood, sector B. Two adults and one child are on a "
                    "rooftop at grid (7, 8); water is rising from the south. "
                    "A rescue boat is staged at (2, 1). Direct the civilians: "
                    "where to go, what to do, and what to avoid."
                ),
                id="recon-flash-flood-1",
            )
        ],
        solver=[
            system_message(
                "You are a reconnaissance advisor. Give short, ordered, "
                "actionable instructions a stressed civilian can follow."
            ),
            generate(),
        ],
    )
