from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .task import Task, TaskStatus


@dataclass(slots=True)
class Project:
    name: str
    repo_path: Path
    id: str = field(default_factory=lambda: uuid4().hex)
    goal: str = ""
    roadmap: str = ""
    init_plan: str = ""
    suggested_next_tasks: list[str] = field(default_factory=list)
    init_candidate_files: list[str] = field(default_factory=list)
    init_existing_files: list[str] = field(default_factory=list)
    init_warnings: list[str] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    tasks: list[Task] = field(default_factory=list)

    @property
    def active_task_count(self) -> int:
        terminal = {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
            TaskStatus.ACCEPTED,
            TaskStatus.REJECTED,
        }
        return sum(task.status not in terminal for task in self.tasks)

    def add_task(self, task: Task) -> None:
        task.project_id = self.id
        task.repository = self.repo_path
        self.tasks.append(task)
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def set_roadmap(
        self, roadmap: str, suggested_next_tasks: list[str]
    ) -> None:
        self.roadmap = roadmap
        self.suggested_next_tasks = list(suggested_next_tasks)
        self.touch()

    def set_init_plan(
        self,
        init_plan: str,
        candidate_files: list[str],
        existing_files: list[str],
        warnings: list[str],
    ) -> None:
        self.init_plan = init_plan
        self.init_candidate_files = list(candidate_files)
        self.init_existing_files = list(existing_files)
        self.init_warnings = list(warnings)
        self.touch()
