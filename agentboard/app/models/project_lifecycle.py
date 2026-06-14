from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from uuid import uuid4


class ProjectResourceStatus(str, Enum):
    MISSING = "missing"
    IMPORTED = "imported"
    DRAFT = "draft"
    ACCEPTED = "accepted"
    STALE = "stale"
    NEEDS_UPDATE = "needs_update"
    UPDATED_AFTER_TASK = "updated_after_task"
    USER_MODIFIED = "user_modified"


class SuggestionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(slots=True)
class ProjectDocument:
    project_id: str
    kind: str
    content: str
    path: str | None = None
    status: str = ProjectResourceStatus.IMPORTED.value
    id: str = field(default_factory=lambda: uuid4().hex)
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass(slots=True)
class ProjectUpdateSuggestion:
    project_id: str
    target: str
    suggested_change: str
    source_task_id: str | None = None
    status: str = SuggestionStatus.PENDING.value
    id: str = field(default_factory=lambda: uuid4().hex)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def accept(self) -> None:
        if self.status != SuggestionStatus.PENDING.value:
            raise ValueError("Only pending suggestions can be accepted.")
        self.status = SuggestionStatus.ACCEPTED.value

    def reject(self) -> None:
        if self.status != SuggestionStatus.PENDING.value:
            raise ValueError("Only pending suggestions can be rejected.")
        self.status = SuggestionStatus.REJECTED.value


@dataclass(frozen=True, slots=True)
class ProjectAnalysis:
    repo_path: Path
    detected_project_type: str
    detected_stack: tuple[str, ...]
    documentation_files: tuple[str, ...]
    missing_important_files: tuple[str, ...]
    roadmap_path: str | None
    init_paths: tuple[str, ...]
    suggested_actions: tuple[str, ...]
    is_git_repository: bool

    @property
    def has_roadmap(self) -> bool:
        return self.roadmap_path is not None

    @property
    def has_init_context(self) -> bool:
        return bool(self.init_paths)
