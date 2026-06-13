from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class AgentRole(str, Enum):
    PROMPT_OPTIMIZER = "Prompt Optimizer"
    PLANNER = "Planner"
    BACKEND = "Backend"
    FRONTEND = "Frontend"
    TESTER = "Tester"
    REVIEWER = "Reviewer"


class AgentStatus(str, Enum):
    WAITING = "Waiting"
    RUNNING = "Running"
    DONE = "Done"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


@dataclass(slots=True)
class AgentState:
    role: AgentRole
    name: str
    status: AgentStatus = AgentStatus.WAITING
    progress: int = 0
    current_message: str = ""
    id: str = field(default_factory=lambda: uuid4().hex)
    task_id: str | None = None
    logs: list[str] = field(default_factory=list)
    result: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None

    def update(
        self,
        *,
        status: AgentStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
    ) -> None:
        if status is not None:
            self.status = status
            if status == AgentStatus.RUNNING and self.started_at is None:
                self.started_at = datetime.now(timezone.utc)
            if status in {
                AgentStatus.DONE,
                AgentStatus.FAILED,
                AgentStatus.CANCELLED,
            }:
                self.finished_at = datetime.now(timezone.utc)
        if progress is not None:
            self.progress = max(0, min(100, progress))
        if message is not None:
            self.current_message = message

    def append_log(self, message: str, limit: int = 50) -> None:
        self.logs.append(message)
        if len(self.logs) > limit:
            del self.logs[:-limit]

    @property
    def elapsed_seconds(self) -> int:
        if self.started_at is None:
            return 0
        end = self.finished_at or datetime.now(timezone.utc)
        return max(0, int((end - self.started_at).total_seconds()))
