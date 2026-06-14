from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class DraftStatus(str, Enum):
    DRAFT = "draft"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ProposedFileStatus(str, Enum):
    NEW = "new"
    UPDATE = "update"
    CONFLICT = "conflict"


@dataclass(slots=True)
class ProposedFile:
    path: str
    content: str
    existing_content: str = ""
    status: ProposedFileStatus = ProposedFileStatus.NEW
    selected: bool = True
    diff_preview: str = ""


@dataclass(slots=True)
class RoadmapDraft:
    project_id: str
    user_goal: str
    draft_content: str
    id: str = field(default_factory=lambda: uuid4().hex)
    feedback_history: list[str] = field(default_factory=list)
    status: DraftStatus = DraftStatus.DRAFT
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    reasoning_summary: str = ""
    repository_observations: list[str] = field(default_factory=list)
    suggested_milestones: list[str] = field(default_factory=list)
    suggested_next_tasks: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    testing_strategy: list[str] = field(default_factory=list)
    command: tuple[str, ...] = ()
    stdout: str = ""
    stderr: str = ""

    def accept(self) -> None:
        self.status = DraftStatus.ACCEPTED
        self.touch()

    def reject(self) -> None:
        self.status = DraftStatus.REJECTED
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)


@dataclass(slots=True)
class InitDraft:
    project_id: str
    user_goal: str
    proposed_files: list[ProposedFile]
    id: str = field(default_factory=lambda: uuid4().hex)
    feedback_history: list[str] = field(default_factory=list)
    status: DraftStatus = DraftStatus.DRAFT
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    reasoning_summary: str = ""
    repository_observations: list[str] = field(default_factory=list)
    setup_notes: list[str] = field(default_factory=list)
    command: tuple[str, ...] = ()
    stdout: str = ""
    stderr: str = ""

    def accept(self) -> None:
        self.status = DraftStatus.ACCEPTED
        self.touch()

    def reject(self) -> None:
        self.status = DraftStatus.REJECTED
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
