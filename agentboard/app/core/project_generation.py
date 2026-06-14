from __future__ import annotations

from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from agentboard.app.models import InitDraft, Project, RoadmapDraft
from agentboard.app.utils.config import AppConfig

from .init_generator import InitGenerator
from .opencode_runner import select_runner
from .roadmap_generator import RoadmapGenerator


class ProjectAgentWorker(QObject):
    log = Signal(str)
    progress = Signal(int, str)
    completed = Signal(object)
    failed = Signal(str)
    terminal = Signal()

    def __init__(
        self,
        project: Project,
        config: AppConfig,
        mode: str,
        kind: str,
        goal: str,
        *,
        previous_draft: RoadmapDraft | InitDraft | None = None,
        feedback: str = "",
        constraints: str = "",
        target_users: str = "",
        mvp_scope: str = "",
        notes: str = "",
    ) -> None:
        super().__init__()
        self.project = project
        self.config = config
        self.mode = mode
        self.kind = kind
        self.goal = goal
        self.previous_draft = previous_draft
        self.feedback = feedback
        self.constraints = constraints
        self.target_users = target_users
        self.mvp_scope = mvp_scope
        self.notes = notes
        self.cancel_event = Event()

    @Slot()
    def run(self) -> None:
        try:
            runner, label = select_runner(self.config, self.mode)
            self.log.emit(f"Project agent runner: {label}")
            if self.kind == "roadmap":
                service = RoadmapGenerator(runner)
                if isinstance(self.previous_draft, RoadmapDraft):
                    draft = service.revise(
                        self.project,
                        self.previous_draft,
                        self.feedback,
                        constraints=self.constraints,
                        target_users=self.target_users,
                        mvp_scope=self.mvp_scope,
                        notes=self.notes,
                        cancel_event=self.cancel_event,
                        on_log=self.log.emit,
                        on_progress=self.progress.emit,
                    )
                else:
                    draft = service.generate(
                        self.project,
                        self.goal,
                        self.constraints,
                        target_users=self.target_users,
                        mvp_scope=self.mvp_scope,
                        notes=self.notes,
                        cancel_event=self.cancel_event,
                        on_log=self.log.emit,
                        on_progress=self.progress.emit,
                    )
            elif self.kind == "init":
                service = InitGenerator(runner)
                if isinstance(self.previous_draft, InitDraft):
                    draft = service.revise(
                        self.project,
                        self.previous_draft,
                        self.feedback,
                        cancel_event=self.cancel_event,
                        on_log=self.log.emit,
                        on_progress=self.progress.emit,
                    )
                else:
                    draft = service.generate(
                        self.project,
                        self.goal,
                        cancel_event=self.cancel_event,
                        on_log=self.log.emit,
                        on_progress=self.progress.emit,
                    )
            else:
                raise ValueError(f"Unknown project agent kind: {self.kind}")
            self.completed.emit(draft)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.terminal.emit()

    def cancel(self) -> None:
        self.cancel_event.set()


ProjectGenerationWorker = ProjectAgentWorker
