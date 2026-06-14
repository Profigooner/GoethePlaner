from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from threading import Event, Lock
from typing import Callable

from agentboard.app.models import AgentState, AgentStatus, Subtask

from .agent_registry import AgentDefinition, safe_opencode_agent
from .opencode_runner import AgentRunner


AgentCallback = Callable[[AgentState], None]
LogCallback = Callable[[str, str], None]
CompletionCallback = Callable[[int, int], None]


class AgentDispatcher:
    """Legacy role-based dispatcher retained for compatibility."""

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


class StagedAgentDispatcher:
    FINAL_STAGE_IDS = (
        "test_engineer",
        "code_reviewer",
        "documentation_writer",
    )
    LOCAL_STAGE_IDS = ("prompt_optimizer", "planner")

    def __init__(
        self,
        runner: AgentRunner,
        *,
        custom_agents: dict[str, str] | None = None,
        parallel_implementation: bool = False,
    ) -> None:
        self.runner = runner
        self.custom_agents = custom_agents or {}
        self.parallel_implementation = parallel_implementation
        self._callback_lock = Lock()

    def dispatch(
        self,
        *,
        repository: Path,
        optimized_prompt: str,
        planner_notes: str,
        definitions: list[AgentDefinition],
        agents: list[AgentState],
        cancel_event: Event,
        on_agent: AgentCallback,
        on_log: LogCallback,
        on_completion: CompletionCallback,
    ) -> bool:
        definitions_by_id = {item.id: item for item in definitions}
        agents_by_id = {item.agent_id: item for item in agents}
        implementation_ids = [
            item.id
            for item in definitions
            if item.id not in self.LOCAL_STAGE_IDS
            and item.id not in self.FINAL_STAGE_IDS
        ]
        execution_ids = [
            *implementation_ids,
            *[
                item
                for item in self.FINAL_STAGE_IDS
                if item in definitions_by_id
            ],
        ]
        total = len(execution_ids)
        completed = 0

        if self.parallel_implementation and len(implementation_ids) > 1:
            successful, completed = self._run_parallel(
                implementation_ids,
                definitions_by_id,
                agents_by_id,
                repository,
                optimized_prompt,
                planner_notes,
                cancel_event,
                on_agent,
                on_log,
                on_completion,
                total,
            )
            if not successful:
                self._cancel_pending(agents, on_agent)
                return False
        else:
            for agent_id in implementation_ids:
                if not self._run_one(
                    definitions_by_id[agent_id],
                    agents_by_id[agent_id],
                    repository,
                    optimized_prompt,
                    planner_notes,
                    cancel_event,
                    on_agent,
                    on_log,
                ):
                    self._cancel_pending(agents, on_agent)
                    return False
                completed += 1
                on_completion(completed, total)

        for agent_id in self.FINAL_STAGE_IDS:
            if agent_id not in definitions_by_id:
                continue
            if not self._run_one(
                definitions_by_id[agent_id],
                agents_by_id[agent_id],
                repository,
                optimized_prompt,
                planner_notes,
                cancel_event,
                on_agent,
                on_log,
            ):
                self._cancel_pending(agents, on_agent)
                return False
            completed += 1
            on_completion(completed, total)
        return True

    def _run_parallel(
        self,
        agent_ids: list[str],
        definitions: dict[str, AgentDefinition],
        agents: dict[str, AgentState],
        repository: Path,
        optimized_prompt: str,
        planner_notes: str,
        cancel_event: Event,
        on_agent: AgentCallback,
        on_log: LogCallback,
        on_completion: CompletionCallback,
        total: int,
    ) -> tuple[bool, int]:
        successful = True
        completed = 0
        with ThreadPoolExecutor(
            max_workers=min(4, len(agent_ids)),
            thread_name_prefix="goethe-agent",
        ) as executor:
            futures = {
                executor.submit(
                    self._run_one,
                    definitions[agent_id],
                    agents[agent_id],
                    repository,
                    optimized_prompt,
                    planner_notes,
                    cancel_event,
                    on_agent,
                    on_log,
                ): agent_id
                for agent_id in agent_ids
            }
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as exc:
                    agent = agents[futures[future]]
                    agent.update(
                        status=AgentStatus.FAILED,
                        message=f"Agent execution failed: {exc}",
                    )
                    self._emit_agent(on_agent, agent)
                    result = False
                successful = successful and result
                completed += 1
                on_completion(completed, total)
        return successful, completed

    def _run_one(
        self,
        definition: AgentDefinition,
        agent: AgentState,
        repository: Path,
        optimized_prompt: str,
        planner_notes: str,
        cancel_event: Event,
        on_agent: AgentCallback,
        on_log: LogCallback,
    ) -> bool:
        if cancel_event.is_set():
            agent.update(
                status=AgentStatus.CANCELLED,
                message="Workflow cancelled before this agent started.",
            )
            self._emit_agent(on_agent, agent)
            return False

        agent.update(
            status=AgentStatus.RUNNING,
            progress=0,
            message=f"Starting {definition.display_name} stage",
        )
        self._emit_agent(on_agent, agent)
        result = self.runner.run_agent(
            agent_name=safe_opencode_agent(
                definition, self.custom_agents
            ),
            repo_path=repository,
            prompt=definition.build_prompt(
                task=optimized_prompt,
                repository=str(repository),
                planner_notes=planner_notes,
            ),
            cancel_event=cancel_event,
            on_log=lambda message: self._handle_log(
                agent, message, on_agent, on_log
            ),
            on_progress=lambda progress, message: self._handle_progress(
                agent, progress, message, on_agent
            ),
        )
        agent.result = result.summary
        if result.cancelled:
            agent.update(
                status=AgentStatus.CANCELLED,
                message=result.summary,
            )
            self._emit_agent(on_agent, agent)
            return False
        if not result.success:
            agent.update(
                status=AgentStatus.FAILED,
                message=result.summary,
            )
            self._emit_agent(on_agent, agent)
            return False

        agent.update(
            status=AgentStatus.DONE,
            progress=100,
            message=result.summary,
        )
        self._emit_agent(on_agent, agent)
        return True

    def _handle_log(
        self,
        agent: AgentState,
        message: str,
        on_agent: AgentCallback,
        on_log: LogCallback,
    ) -> None:
        with self._callback_lock:
            agent.append_log(message)
            on_log(agent.name, message)
            on_agent(replace(agent))

    def _handle_progress(
        self,
        agent: AgentState,
        progress: int,
        message: str,
        on_agent: AgentCallback,
    ) -> None:
        with self._callback_lock:
            agent.update(progress=progress, message=message)
            on_agent(replace(agent))

    def _emit_agent(
        self, on_agent: AgentCallback, agent: AgentState
    ) -> None:
        with self._callback_lock:
            on_agent(replace(agent))

    @staticmethod
    def _cancel_pending(
        agents: list[AgentState], on_agent: AgentCallback
    ) -> None:
        for agent in agents:
            if agent.status == AgentStatus.WAITING:
                agent.update(
                    status=AgentStatus.CANCELLED,
                    message="Workflow stopped before this agent started.",
                )
                on_agent(replace(agent))
