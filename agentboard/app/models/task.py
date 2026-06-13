from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4

from .agent import AgentRole, AgentState


class TaskStatus(str, Enum):
    DRAFT = "Draft"
    OPTIMIZING = "Optimizing"
    PLANNING = "Planning"
    RUNNING = "Running"
    REVIEWING = "Reviewing"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"


@dataclass(slots=True)
class Subtask:
    title: str
    description: str
    agent_role: AgentRole
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(slots=True)
class Task:
    repository: Path
    original_prompt: str
    name: str
    id: str = field(default_factory=lambda: uuid4().hex)
    project_id: str | None = None
    optimized_prompt: str = ""
    subtasks: list[Subtask] = field(default_factory=list)
    agents: list[AgentState] = field(default_factory=list)
    status: TaskStatus = TaskStatus.DRAFT
    overall_progress: int = 0
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: datetime | None = None

    @property
    def title(self) -> str:
        return self.name

    @title.setter
    def title(self, value: str) -> None:
        self.name = value
        self.touch()

    def set_progress(self, value: int) -> None:
        self.overall_progress = max(0, min(100, value))
        self.touch()

    def finish(self, status: TaskStatus) -> None:
        self.status = status
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = self.completed_at
        if status in {TaskStatus.COMPLETED, TaskStatus.ACCEPTED}:
            self.overall_progress = 100

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
