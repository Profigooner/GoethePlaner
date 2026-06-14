from __future__ import annotations

from dataclasses import replace
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from agentboard.app.models import (
    AgentState,
    AgentStatus,
    EventKind,
    Subtask,
    Task,
    TaskStatus,
    WorkflowEvent,
)
from agentboard.app.utils.config import AppConfig

from .agent_dispatcher import StagedAgentDispatcher
from .agent_registry import (
    AgentDefinition,
    DEFAULT_AGENT_REGISTRY,
)
from .git_manager import GitBaseline, GitManager
from .opencode_runner import MockOpenCodeRunner, select_runner
from .prompt_optimizer import PromptOptimizer


DEFAULT_SELECTED_AGENTS = (
    "prompt_optimizer",
    "planner",
    "backend_engineer",
    "frontend_engineer",
    "test_engineer",
    "code_reviewer",
)


class WorkflowWorker(QObject):
    task_changed = Signal(str, int)
    optimized_prompt_ready = Signal(str)
    subtasks_ready = Signal(object)
    agent_changed = Signal(object)
    event_emitted = Signal(object)
    baseline_ready = Signal(object)
    repository_state_ready = Signal(object)
    completed = Signal(object)
    failed = Signal(str)
    terminal = Signal()

    def __init__(self, task: Task, config: AppConfig, mode: str) -> None:
        super().__init__()
        self.task = task
        self.config = config
        self.mode = mode
        self.cancel_event = Event()
        self.optimizer = PromptOptimizer()
        self.baseline: GitBaseline | None = None

    @Slot()
    def run(self) -> None:
        try:
            self._run_pipeline()
        except Exception as exc:
            self.task.finish(TaskStatus.FAILED)
            self.task_changed.emit(
                self.task.status.value, self.task.overall_progress
            )
            self._emit_event(
                EventKind.ERROR, f"Workflow failed: {exc}", "GoethePlaner"
            )
            self.failed.emit(str(exc))
        finally:
            self.terminal.emit()

    def cancel(self) -> None:
        self.cancel_event.set()

    def _run_pipeline(self) -> None:
        definitions = self._selected_definitions()
        self.task.selected_agents = [item.id for item in definitions]
        self.task.execution_graph = self._execution_graph(definitions)
        self.task.agents = self._create_agents(definitions)
        for agent in self.task.agents:
            self.agent_changed.emit(replace(agent))

        agents_by_id = {
            agent.agent_id: agent for agent in self.task.agents
        }
        optimizer = agents_by_id.get("prompt_optimizer")
        if optimizer is not None:
            self._set_task(TaskStatus.OPTIMIZING, 3)
            if not self._run_local_stage(
                optimizer,
                [
                    "Reading the rough task prompt",
                    "Adding implementation constraints",
                    "Defining completion criteria",
                ],
                3,
                12,
            ):
                return

        if not self.task.optimized_prompt:
            self.task.optimized_prompt = self.optimizer.optimize(
                self.task.original_prompt, self.task.repository.name
            )
        self.optimized_prompt_ready.emit(self.task.optimized_prompt)

        planner = agents_by_id["planner"]
        self._set_task(TaskStatus.PLANNING, 13)
        if not self._run_local_stage(
            planner,
            [
                "Confirming selected specialists",
                "Ordering implementation and verification",
                "Recording execution constraints",
            ],
            13,
            20,
        ):
            return

        self.task.subtasks = self._build_subtasks(definitions)
        self.subtasks_ready.emit(list(self.task.subtasks))
        self._emit_event(
            EventKind.RESULT,
            f"Created {len(self.task.subtasks)} staged agent assignments.",
            planner.name,
        )

        self._set_task(TaskStatus.RUNNING, 20)
        git_manager = GitManager(self.task.repository)
        if git_manager.is_repository():
            self.baseline = git_manager.capture_baseline()
            self.baseline_ready.emit(self.baseline)
            self._emit_event(
                EventKind.STATUS,
                "Captured the pre-task Git working-tree baseline.",
                "Git",
            )
        else:
            self._emit_event(
                EventKind.STATUS,
                "Selected folder is not a Git repository; diff and reject are unavailable.",
                "Git",
            )

        runner, runner_label = select_runner(self.config, self.mode)
        parallel = isinstance(runner, MockOpenCodeRunner)
        mode_note = (
            "parallel implementation stages"
            if parallel
            else "safe sequential stages"
        )
        self._emit_event(
            EventKind.STATUS,
            f"Execution runner: {runner_label}; {mode_note}.",
            "GoethePlaner",
        )
        dispatcher = StagedAgentDispatcher(
            runner,
            custom_agents=self.config.custom_agent_map,
            parallel_implementation=parallel,
        )
        success = dispatcher.dispatch(
            repository=self.task.repository,
            optimized_prompt=self.task.optimized_prompt,
            planner_notes=self.task.planner_notes,
            definitions=definitions,
            agents=self.task.agents,
            cancel_event=self.cancel_event,
            on_agent=self.agent_changed.emit,
            on_log=lambda source, message: self._emit_event(
                EventKind.LOG, message, source
            ),
            on_completion=self._agent_completed,
        )
        if not success:
            if self.cancel_event.is_set():
                self._finish_cancelled()
            else:
                self.task.finish(TaskStatus.FAILED)
                self.task_changed.emit(
                    self.task.status.value, self.task.overall_progress
                )
                self.failed.emit("An agent failed. Review the Logs tab.")
            return

        self._set_task(TaskStatus.REVIEWING, 96)
        self._emit_event(
            EventKind.STATUS,
            "Collecting final agent results and repository state.",
            "GoethePlaner",
        )
        completed_agents = [
            agent.name
            for agent in self.task.agents
            if agent.status == AgentStatus.DONE
        ]
        self.task.completion_summary = (
            f"Completed {len(completed_agents)} agent stage(s)"
            + (
                f": {', '.join(completed_agents)}."
                if completed_agents
                else "."
            )
        )
        self.task.finish(TaskStatus.COMPLETED)
        self.task_changed.emit(self.task.status.value, 100)
        self._emit_event(
            EventKind.RESULT,
            "Workflow completed. Review repository changes before accepting.",
            "GoethePlaner",
        )
        self.repository_state_ready.emit(git_manager.inspect())
        self.completed.emit(self.task)

    def _selected_definitions(self) -> list[AgentDefinition]:
        selected = list(self.task.selected_agents or DEFAULT_SELECTED_AGENTS)
        if "planner" not in selected:
            selected.insert(0, "planner")
        known = {
            agent_id
            for agent_id in selected
            if DEFAULT_AGENT_REGISTRY.contains(agent_id)
        }
        graph_order = [
            agent_id
            for stage in self.task.execution_graph
            for agent_id in stage
            if agent_id in known
        ]
        preferred = [
            "prompt_optimizer",
            "planner",
            *graph_order,
            *selected,
        ]
        ordered: list[AgentDefinition] = []
        seen: set[str] = set()
        for agent_id in preferred:
            if agent_id in seen or agent_id not in known:
                continue
            ordered.append(DEFAULT_AGENT_REGISTRY.get(agent_id))
            seen.add(agent_id)
        return ordered

    def _create_agents(
        self, definitions: list[AgentDefinition]
    ) -> list[AgentState]:
        agents: list[AgentState] = []
        for definition in definitions:
            agents.append(
                AgentState(
                    definition.role,
                    definition.display_name,
                    task_id=self.task.id,
                    agent_id=definition.id,
                    selection_reason=self.task.agent_selection_reasons.get(
                        definition.id, definition.description
                    ),
                    can_modify_code=definition.can_modify_code,
                    can_run_commands=definition.can_run_commands,
                    risk_level=definition.risk_level,
                )
            )
        return agents

    @staticmethod
    def _execution_graph(
        definitions: list[AgentDefinition],
    ) -> list[list[str]]:
        selected = {item.id for item in definitions}
        implementation = [
            item.id
            for item in definitions
            if item.id
            not in {
                "prompt_optimizer",
                "planner",
                "test_engineer",
                "code_reviewer",
                "documentation_writer",
            }
        ]
        stages = [
            ["prompt_optimizer"] if "prompt_optimizer" in selected else [],
            ["planner"],
            implementation,
            ["test_engineer"] if "test_engineer" in selected else [],
            ["code_reviewer"] if "code_reviewer" in selected else [],
            ["documentation_writer"]
            if "documentation_writer" in selected
            else [],
        ]
        return [stage for stage in stages if stage]

    @staticmethod
    def _build_subtasks(
        definitions: list[AgentDefinition],
    ) -> list[Subtask]:
        return [
            Subtask(
                title=f"Run {definition.display_name} stage",
                description=definition.description,
                agent_role=definition.role,
            )
            for definition in definitions
            if definition.id not in {"prompt_optimizer", "planner"}
        ]

    def _run_local_stage(
        self,
        agent: AgentState,
        messages: list[str],
        start_progress: int,
        end_progress: int,
    ) -> bool:
        agent.update(
            status=AgentStatus.RUNNING,
            progress=0,
            message=messages[0],
        )
        self.agent_changed.emit(replace(agent))
        self._emit_event(EventKind.STATUS, messages[0], agent.name)

        for index, message in enumerate(messages, start=1):
            if self.cancel_event.wait(self.config.mock_step_delay):
                agent.update(
                    status=AgentStatus.CANCELLED,
                    message="Workflow cancelled.",
                )
                self.agent_changed.emit(replace(agent))
                self._finish_cancelled()
                return False
            stage_progress = int(index / len(messages) * 100)
            task_progress = start_progress + int(
                (end_progress - start_progress) * index / len(messages)
            )
            agent.update(progress=stage_progress, message=message)
            agent.append_log(message)
            self.agent_changed.emit(replace(agent))
            self.task.set_progress(task_progress)
            self.task_changed.emit(self.task.status.value, task_progress)
            self._emit_event(EventKind.LOG, message, agent.name)

        agent.result = "Local planning stage completed."
        agent.update(
            status=AgentStatus.DONE,
            progress=100,
            message="Complete",
        )
        self.agent_changed.emit(replace(agent))
        return True

    def _agent_completed(self, completed: int, total: int) -> None:
        progress = 20 + int(75 * completed / max(1, total))
        self.task.set_progress(progress)
        self.task_changed.emit(self.task.status.value, progress)

    def _finish_cancelled(self) -> None:
        for agent in self.task.agents:
            if agent.status == AgentStatus.WAITING:
                agent.update(
                    status=AgentStatus.CANCELLED,
                    message="Workflow cancelled before start.",
                )
                self.agent_changed.emit(replace(agent))
        self.task.finish(TaskStatus.CANCELLED)
        self.task_changed.emit(
            self.task.status.value, self.task.overall_progress
        )
        self._emit_event(
            EventKind.STATUS, "Workflow cancelled.", "GoethePlaner"
        )

    def _set_task(self, status: TaskStatus, progress: int) -> None:
        self.task.status = status
        self.task.set_progress(progress)
        self.task_changed.emit(status.value, self.task.overall_progress)
        self._emit_event(EventKind.STATUS, status.value, "GoethePlaner")

    def _emit_event(
        self, kind: EventKind, message: str, source: str
    ) -> None:
        self.event_emitted.emit(
            WorkflowEvent(kind=kind, message=message, source=source)
        )
