from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from threading import Event
from typing import Callable

from agentboard.app.models import AgentState, AgentStatus, Subtask

from .opencode_runner import AgentRunner


AgentCallback = Callable[[AgentState], None]
LogCallback = Callable[[str, str], None]
CompletionCallback = Callable[[int, int], None]


class AgentDispatcher:
    def __init__(self, runner: AgentRunner) -> None:
        self.runner = runner

    def dispatch(
        self,
        *,
        repository: Path,
        optimized_prompt: str,
        subtasks: list[Subtask],
        agents: list[AgentState],
        cancel_event: Event,
        on_agent: AgentCallback,
        on_log: LogCallback,
        on_completion: CompletionCallback,
    ) -> bool:
        agents_by_role = {agent.role: agent for agent in agents}
        total = len(subtasks)

        for index, subtask in enumerate(subtasks):
            agent = agents_by_role[subtask.agent_role]
            if cancel_event.is_set():
                self._cancel_pending(agents, on_agent)
                return False

            agent.update(
                status=AgentStatus.RUNNING,
                progress=0,
                message=subtask.title,
            )
            on_agent(replace(agent))

            result = self.runner.run_agent(
                agent_name=agent.name,
                repo_path=repository,
                prompt=(
                    f"{optimized_prompt}\n\nAssigned subtask\n"
                    f"{subtask.title}\n{subtask.description}"
                ),
                cancel_event=cancel_event,
                on_log=lambda message, name=agent.name, current=agent: (
                    current.append_log(message),
                    on_log(name, message),
                    on_agent(replace(current)),
                ),
                on_progress=lambda progress, message, current=agent: (
                    current.update(progress=progress, message=message),
                    on_agent(replace(current)),
                ),
            )

            if result.cancelled:
                agent.update(
                    status=AgentStatus.CANCELLED,
                    message=result.summary,
                )
                on_agent(replace(agent))
                self._cancel_pending(agents, on_agent)
                return False
            if not result.success:
                agent.update(
                    status=AgentStatus.FAILED,
                    message=result.summary,
                )
                on_agent(replace(agent))
                return False

            agent.update(
                status=AgentStatus.DONE,
                progress=100,
                message=result.summary,
            )
            on_agent(replace(agent))
            on_completion(index + 1, total)

        return True

    @staticmethod
    def _cancel_pending(
        agents: list[AgentState], on_agent: AgentCallback
    ) -> None:
        for agent in agents:
            if agent.status == AgentStatus.WAITING:
                agent.update(
                    status=AgentStatus.CANCELLED,
                    message="Workflow cancelled before this agent started.",
                )
                on_agent(replace(agent))
