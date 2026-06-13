from __future__ import annotations

from agentboard.app.models import AgentRole, Subtask


class TaskPlanner:
    def plan(self, optimized_prompt: str) -> list[Subtask]:
        summary = optimized_prompt.splitlines()[1].strip()
        return [
            Subtask(
                title="Implement core and backend changes",
                description=(
                    f"Inspect the repository and implement the non-visual parts "
                    f"of the objective: {summary}"
                ),
                agent_role=AgentRole.BACKEND,
            ),
            Subtask(
                title="Implement user-facing changes",
                description=(
                    "Update the relevant interface or presentation layer while "
                    "following existing project conventions."
                ),
                agent_role=AgentRole.FRONTEND,
            ),
            Subtask(
                title="Add and run focused tests",
                description=(
                    "Cover the changed behavior, run the relevant test commands, "
                    "and report failures without hiding them."
                ),
                agent_role=AgentRole.TESTER,
            ),
            Subtask(
                title="Review the completed change",
                description=(
                    "Inspect the resulting diff for correctness, regressions, "
                    "unsafe behavior, and missing verification."
                ),
                agent_role=AgentRole.REVIEWER,
            ),
        ]

