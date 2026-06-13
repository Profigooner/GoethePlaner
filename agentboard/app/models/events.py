from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class EventKind(str, Enum):
    STATUS = "status"
    PROGRESS = "progress"
    LOG = "log"
    ERROR = "error"
    RESULT = "result"


@dataclass(frozen=True, slots=True)
class WorkflowEvent:
    kind: EventKind
    message: str
    source: str = "AgentBoard"
    progress: int | None = None
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

