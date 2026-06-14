from __future__ import annotations

from pathlib import Path
from threading import Event

from agentboard.app.models import DraftStatus, Project, RoadmapDraft

from .opencode_runner import (
    LogCallback,
    MockOpenCodeRunner,
    ProgressCallback,
)


class RoadmapGenerator:
    """Agent-backed roadmap service retained under the existing module name."""

    def __init__(self, runner=None) -> None:
        self.runner = runner or MockOpenCodeRunner(step_delay=0)

    def generate(
        self,
        project: Project,
        goal: str,
        constraints: str = "",
        *,
        target_users: str = "",
        mvp_scope: str = "",
        notes: str = "",
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> RoadmapDraft:
        return self.runner.run_roadmap_agent(
            project,
            goal,
            constraints,
            target_users=target_users,
            mvp_scope=mvp_scope,
            notes=notes,
            cancel_event=cancel_event,
            on_log=on_log,
            on_progress=on_progress,
        )

    def revise(
        self,
        project: Project,
        previous_draft: RoadmapDraft,
        feedback: str,
        *,
        constraints: str = "",
        target_users: str = "",
        mvp_scope: str = "",
        notes: str = "",
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> RoadmapDraft:
        return self.runner.revise_roadmap_agent(
            project,
            previous_draft,
            feedback,
            constraints=constraints,
            target_users=target_users,
            mvp_scope=mvp_scope,
            notes=notes,
            cancel_event=cancel_event,
            on_log=on_log,
            on_progress=on_progress,
        )


def export_accepted_roadmap(
    draft: RoadmapDraft, target: Path, *, overwrite: bool = False
) -> Path:
    if draft.status != DraftStatus.ACCEPTED:
        raise ValueError("Roadmap must be accepted before export.")
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "x"
    with target.open(mode, encoding="utf-8") as handle:
        handle.write(draft.draft_content)
        if not draft.draft_content.endswith("\n"):
            handle.write("\n")
    return target
