from __future__ import annotations

from dataclasses import dataclass, field
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

    def update(
        self,
        *,
        status: AgentStatus | None = None,
        progress: int | None = None,
        message: str | None = None,
    ) -> None:
        if status is not None:
            self.status = status
        if progress is not None:
            self.progress = max(0, min(100, progress))
        if message is not None:
            self.current_message = message

