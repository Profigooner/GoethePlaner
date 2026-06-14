from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal, Slot

from agentboard.app.models import Project

from .init_generator import InitGenerator, InitPlanResult
from .roadmap_generator import RoadmapGenerator, RoadmapResult


@dataclass(frozen=True, slots=True)
class ProjectGenerationResult:
    project_id: str
    kind: str
    result: RoadmapResult | InitPlanResult


class ProjectGenerationWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    terminal = Signal()

    def __init__(self, project: Project, kind: str) -> None:
        super().__init__()
        self.project = project
        self.kind = kind

    @Slot()
    def run(self) -> None:
        try:
            if self.kind == "roadmap":
                result = RoadmapGenerator().generate(self.project)
            elif self.kind == "init":
                result = InitGenerator().generate(self.project)
            else:
                raise ValueError(f"Unknown project generation kind: {self.kind}")
            self.completed.emit(
                ProjectGenerationResult(
                    project_id=self.project.id,
                    kind=self.kind,
                    result=result,
                )
            )
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.terminal.emit()
