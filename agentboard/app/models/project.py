from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .drafts import InitDraft, ProposedFileStatus, RoadmapDraft
from .project_lifecycle import (
    ProjectAnalysis,
    ProjectDocument,
    ProjectResourceStatus,
    ProjectUpdateSuggestion,
    SuggestionStatus,
)
from .task import Task, TaskStatus


@dataclass(slots=True)
class Project:
    name: str
    repo_path: Path
    id: str = field(default_factory=lambda: uuid4().hex)
    project_type: str = "existing"
    goal: str = ""
    detected_project_type: str = ""
    roadmap_status: str = ProjectResourceStatus.MISSING.value
    init_status: str = ProjectResourceStatus.MISSING.value
    roadmap: str = ""
    init_plan: str = ""
    suggested_next_tasks: list[str] = field(default_factory=list)
    init_candidate_files: list[str] = field(default_factory=list)
    init_existing_files: list[str] = field(default_factory=list)
    init_warnings: list[str] = field(default_factory=list)
    roadmap_draft: RoadmapDraft | None = None
    init_draft: InitDraft | None = None
    roadmap_draft_history: list[RoadmapDraft] = field(default_factory=list)
    init_draft_history: list[InitDraft] = field(default_factory=list)
    documents: list[ProjectDocument] = field(default_factory=list)
    update_suggestions: list[ProjectUpdateSuggestion] = field(
        default_factory=list
    )
    analysis: ProjectAnalysis | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    tasks: list[Task] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.repo_path = Path(self.repo_path)

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
        self.roadmap_status = ProjectResourceStatus.ACCEPTED.value
        self.suggested_next_tasks = list(suggested_next_tasks)
        self.touch()

    def set_roadmap_draft(self, draft: RoadmapDraft) -> None:
        if draft.project_id != self.id:
            raise ValueError("Roadmap draft belongs to another project.")
        self.roadmap_draft = draft
        self.roadmap_draft_history.append(draft)
        self.roadmap_status = ProjectResourceStatus.DRAFT.value
        self.touch()

    def accept_roadmap_draft(self, draft: RoadmapDraft) -> None:
        if draft.project_id != self.id:
            raise ValueError("Roadmap draft belongs to another project.")
        draft.accept()
        self.roadmap_draft = draft
        self.roadmap = draft.draft_content
        self.roadmap_status = ProjectResourceStatus.ACCEPTED.value
        self.suggested_next_tasks = list(draft.suggested_next_tasks)
        self.touch()

    def set_init_plan(
        self,
        init_plan: str,
        candidate_files: list[str],
        existing_files: list[str],
        warnings: list[str],
    ) -> None:
        self.init_plan = init_plan
        self.init_status = ProjectResourceStatus.ACCEPTED.value
        self.init_candidate_files = list(candidate_files)
        self.init_existing_files = list(existing_files)
        self.init_warnings = list(warnings)
        self.touch()

    def set_init_draft(self, draft: InitDraft) -> None:
        if draft.project_id != self.id:
            raise ValueError("Init draft belongs to another project.")
        self.init_draft = draft
        self.init_draft_history.append(draft)
        self.init_status = ProjectResourceStatus.DRAFT.value
        self.touch()

    def accept_init_draft(self, draft: InitDraft) -> None:
        if draft.project_id != self.id:
            raise ValueError("Init draft belongs to another project.")
        draft.accept()
        self.init_draft = draft
        self.init_status = ProjectResourceStatus.ACCEPTED.value
        self.init_plan = "\n\n".join(
            f"## {proposal.path}\n\n```text\n{proposal.content.rstrip()}\n```"
            for proposal in draft.proposed_files
            if (
                proposal.selected
                and proposal.status != ProposedFileStatus.CONFLICT
            )
        )
        self.init_candidate_files = [
            proposal.path
            for proposal in draft.proposed_files
            if (
                proposal.selected
                and proposal.status != ProposedFileStatus.CONFLICT
            )
        ]
        self.init_existing_files = [
            proposal.path
            for proposal in draft.proposed_files
            if proposal.existing_content
        ]
        self.init_warnings = [
            "Only explicitly selected files were approved.",
            "Existing files require explicit overwrite confirmation.",
        ]
        self.touch()

    @property
    def roadmap_content(self) -> str:
        return self.roadmap

    @roadmap_content.setter
    def roadmap_content(self, value: str) -> None:
        self.update_roadmap(value)

    @property
    def init_content(self) -> str:
        return self.init_plan

    @init_content.setter
    def init_content(self, value: str) -> None:
        self.update_init(value)

    @property
    def pending_suggestions(self) -> list[ProjectUpdateSuggestion]:
        return [
            suggestion
            for suggestion in self.update_suggestions
            if suggestion.status == SuggestionStatus.PENDING.value
        ]

    def set_analysis(self, analysis: ProjectAnalysis) -> None:
        if analysis.repo_path.resolve() != self.repo_path.resolve():
            raise ValueError("Project analysis belongs to another repository.")
        self.analysis = analysis
        self.detected_project_type = analysis.detected_project_type
        self.touch()

    def add_document(self, document: ProjectDocument) -> None:
        if document.project_id != self.id:
            raise ValueError("Project document belongs to another project.")
        self.documents = [
            item
            for item in self.documents
            if not (
                item.kind == document.kind
                and item.path == document.path
            )
        ]
        self.documents.append(document)
        self.touch()

    def update_roadmap(
        self,
        content: str,
        status: str = ProjectResourceStatus.USER_MODIFIED.value,
    ) -> None:
        self.roadmap = content
        self.roadmap_status = (
            status
            if content.strip()
            else ProjectResourceStatus.MISSING.value
        )
        self.touch()

    def update_init(
        self,
        content: str,
        status: str = ProjectResourceStatus.USER_MODIFIED.value,
    ) -> None:
        self.init_plan = content
        self.init_status = (
            status
            if content.strip()
            else ProjectResourceStatus.MISSING.value
        )
        self.touch()

    def add_roadmap_requirement(self, requirement: str) -> None:
        text = requirement.strip()
        if not text:
            raise ValueError("Roadmap requirement cannot be empty.")
        separator = "\n" if self.roadmap and not self.roadmap.endswith("\n") else ""
        self.update_roadmap(
            f"{self.roadmap}{separator}- [ ] {text}\n",
            ProjectResourceStatus.USER_MODIFIED.value,
        )

    def add_update_suggestion(
        self, suggestion: ProjectUpdateSuggestion
    ) -> None:
        if suggestion.project_id != self.id:
            raise ValueError("Update suggestion belongs to another project.")
        self.update_suggestions.append(suggestion)
        if suggestion.target == "roadmap":
            self.roadmap_status = ProjectResourceStatus.NEEDS_UPDATE.value
        elif suggestion.target == "init":
            self.init_status = ProjectResourceStatus.NEEDS_UPDATE.value
        self.touch()

    def apply_update_suggestion(self, suggestion_id: str) -> None:
        suggestion = self._suggestion(suggestion_id)
        suggestion.accept()
        if suggestion.target == "roadmap":
            base = self.roadmap.rstrip()
            self.roadmap = (
                f"{base}\n\n{suggestion.suggested_change.strip()}\n"
                if base
                else f"{suggestion.suggested_change.strip()}\n"
            )
            self.roadmap_status = (
                ProjectResourceStatus.UPDATED_AFTER_TASK.value
            )
        elif suggestion.target == "init":
            base = self.init_plan.rstrip()
            self.init_plan = (
                f"{base}\n\n{suggestion.suggested_change.strip()}\n"
                if base
                else f"{suggestion.suggested_change.strip()}\n"
            )
            self.init_status = ProjectResourceStatus.UPDATED_AFTER_TASK.value
        else:
            raise ValueError(f"Unknown suggestion target: {suggestion.target}")
        self.touch()

    def reject_update_suggestion(self, suggestion_id: str) -> None:
        suggestion = self._suggestion(suggestion_id)
        suggestion.reject()
        pending_targets = {
            item.target for item in self.pending_suggestions
        }
        if (
            suggestion.target == "roadmap"
            and "roadmap" not in pending_targets
            and self.roadmap_status == ProjectResourceStatus.NEEDS_UPDATE.value
        ):
            self.roadmap_status = (
                ProjectResourceStatus.ACCEPTED.value
                if self.roadmap
                else ProjectResourceStatus.MISSING.value
            )
        if (
            suggestion.target == "init"
            and "init" not in pending_targets
            and self.init_status == ProjectResourceStatus.NEEDS_UPDATE.value
        ):
            self.init_status = (
                ProjectResourceStatus.ACCEPTED.value
                if self.init_plan
                else ProjectResourceStatus.MISSING.value
            )
        self.touch()

    def _suggestion(self, suggestion_id: str) -> ProjectUpdateSuggestion:
        suggestion = next(
            (
                item
                for item in self.update_suggestions
                if item.id == suggestion_id
            ),
            None,
        )
        if suggestion is None:
            raise ValueError("Unknown project update suggestion.")
        return suggestion
