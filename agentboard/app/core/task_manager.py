from __future__ import annotations

from dataclasses import replace
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from agentboard.app.models import (
    AgentRole,
    AgentState,
    AgentStatus,
    EventKind,
    Task,
    TaskStatus,
    WorkflowEvent,
)
from agentboard.app.utils.config import AppConfig

from .agent_dispatcher import AgentDispatcher
from .git_manager import GitBaseline, GitManager
from .opencode_runner import select_runner
from .prompt_optimizer import PromptOptimizer
from .task_planner import TaskPlanner


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
        self.planner = TaskPlanner()
        self.baseline: GitBaseline | None = None

    @Slot()
    def run(self) -> None:
        try:
            self._run_pipeline()
        except Exception as exc:
            self.task.finish(TaskStatus.FAILED)
            self.task_changed.emit(self.task.status.value, self.task.overall_progress)
            self._emit_event(
                EventKind.ERROR, f"Workflow failed: {exc}", "AgentBoard"
            )
            self.failed.emit(str(exc))
        finally:
            self.terminal.emit()

    def cancel(self) -> None:
        self.cancel_event.set()

    def _run_pipeline(self) -> None:
        self.task.agents = self._create_agents()
        for agent in self.task.agents:
            self.agent_changed.emit(replace(agent))

        optimizer_agent = self.task.agents[0]
        self._set_task(TaskStatus.OPTIMIZING, 3)
        if not self._run_local_stage(
            optimizer_agent,
            [
                "Reading the rough task prompt",
                "Adding implementation constraints",
                "Defining completion criteria",
            ],
            3,
            12,
        ):
            return

        self.task.optimized_prompt = self.optimizer.optimize(
            self.task.original_prompt, self.task.repository.name
        )
        self.optimized_prompt_ready.emit(self.task.optimized_prompt)

        planner_agent = self.task.agents[1]
        self._set_task(TaskStatus.PLANNING, 13)
        if not self._run_local_stage(
            planner_agent,
            [
                "Identifying implementation areas",
                "Assigning specialized agents",
                "Ordering verification and review",
            ],
            13,
            20,
        ):
            return

        self.task.subtasks = self.planner.plan(self.task.optimized_prompt)
        self.subtasks_ready.emit(list(self.task.subtasks))
        self._emit_event(
            EventKind.RESULT,
            f"Created {len(self.task.subtasks)} executable subtasks.",
            planner_agent.name,
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
        self._emit_event(
            EventKind.STATUS,
            f"Execution runner: {runner_label}",
            "AgentBoard",
        )
        dispatcher = AgentDispatcher(runner)
        success = dispatcher.dispatch(
            repository=self.task.repository,
            optimized_prompt=self.task.optimized_prompt,
            subtasks=self.task.subtasks,
            agents=self.task.agents[2:],
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
            "Collecting final workflow results.",
            "AgentBoard",
        )
        self.task.finish(TaskStatus.COMPLETED)
        self.task_changed.emit(self.task.status.value, 100)
        self._emit_event(
            EventKind.RESULT,
            "Workflow completed. Review repository changes before accepting.",
            "AgentBoard",
        )
        self.repository_state_ready.emit(git_manager.inspect())
        self.completed.emit(self.task)

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
            self.agent_changed.emit(replace(agent))
            self.task.set_progress(task_progress)
            self.task_changed.emit(self.task.status.value, task_progress)
            self._emit_event(EventKind.LOG, message, agent.name)

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
            EventKind.STATUS, "Workflow cancelled.", "AgentBoard"
        )

    def _set_task(self, status: TaskStatus, progress: int) -> None:
        self.task.status = status
        self.task.set_progress(progress)
        self.task_changed.emit(status.value, self.task.overall_progress)
        self._emit_event(EventKind.STATUS, status.value, "AgentBoard")

    def _emit_event(
        self, kind: EventKind, message: str, source: str
    ) -> None:
        self.event_emitted.emit(
            WorkflowEvent(kind=kind, message=message, source=source)
        )

    @staticmethod
    def _create_agents() -> list[AgentState]:
        return [
            AgentState(AgentRole.PROMPT_OPTIMIZER, "Prompt Optimizer Agent"),
            AgentState(AgentRole.PLANNER, "Planner Agent"),
            AgentState(AgentRole.BACKEND, "Backend Agent"),
            AgentState(AgentRole.FRONTEND, "Frontend Agent"),
            AgentState(AgentRole.TESTER, "Tester Agent"),
            AgentState(AgentRole.REVIEWER, "Reviewer Agent"),
        ]
