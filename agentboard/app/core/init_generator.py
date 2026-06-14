from __future__ import annotations

from pathlib import Path, PurePosixPath
from threading import Event

from agentboard.app.models import (
    DraftStatus,
    InitDraft,
    Project,
    ProposedFileStatus,
)

from .opencode_runner import (
    LogCallback,
    MockOpenCodeRunner,
    ProgressCallback,
)


class InitGenerator:
    """Agent-backed init service retained under the existing module name."""

    def __init__(self, runner=None) -> None:
        self.runner = runner or MockOpenCodeRunner(step_delay=0)

    def generate(
        self,
        project: Project,
        goal: str,
        *,
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> InitDraft:
        return self.runner.run_init_agent(
            project,
            goal,
            cancel_event=cancel_event,
            on_log=on_log,
            on_progress=on_progress,
        )

    def revise(
        self,
        project: Project,
        previous_draft: InitDraft,
        feedback: str,
        *,
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> InitDraft:
        return self.runner.revise_init_agent(
            project,
            previous_draft,
            feedback,
            cancel_event=cancel_event,
            on_log=on_log,
            on_progress=on_progress,
        )

    def apply_selected(
        self,
        project: Project,
        draft: InitDraft,
        *,
        confirmed: bool = False,
        overwrite_paths: set[str] | None = None,
    ) -> tuple[str, ...]:
        if not confirmed:
            raise PermissionError("Explicit apply confirmation is required.")
        if draft.project_id != project.id:
            raise ValueError("Init draft belongs to another project.")
        overwrite = overwrite_paths or set()
        repository = project.repo_path.resolve()
        written: list[str] = []

        for proposal in draft.proposed_files:
            if not proposal.selected:
                continue
            if proposal.status == ProposedFileStatus.CONFLICT:
                raise ValueError(
                    f"Conflicted proposal cannot be applied: {proposal.path}"
                )
            relative = self._safe_relative(proposal.path)
            target = (repository / relative).resolve()
            if target != repository and repository not in target.parents:
                raise ValueError(f"Unsafe init proposal path: {proposal.path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if proposal.path not in overwrite:
                    raise PermissionError(
                        f"Explicit overwrite approval required: {proposal.path}"
                    )
                if target.is_symlink() or not target.is_file():
                    raise ValueError(
                        f"Unsafe existing target: {proposal.path}"
                    )
                current = target.read_text(
                    encoding="utf-8", errors="replace"
                )
                if current != proposal.existing_content:
                    raise FileExistsError(
                        f"{proposal.path} changed after the draft was generated."
                    )
                target.write_text(proposal.content, encoding="utf-8")
            else:
                with target.open("x", encoding="utf-8") as handle:
                    handle.write(proposal.content)
            written.append(proposal.path)

        return tuple(written)

    @staticmethod
    def _safe_relative(path: str) -> Path:
        relative = PurePosixPath(path.replace("\\", "/"))
        if (
            relative.is_absolute()
            or not relative.parts
            or ".." in relative.parts
            or relative.parts[0] in {"", "."}
        ):
            raise ValueError(f"Unsafe init proposal path: {path}")
        return Path(*relative.parts)


def export_init_draft(
    draft: InitDraft, target: Path, *, overwrite: bool = False
) -> Path:
    if target.exists() and not overwrite:
        raise FileExistsError(target)
    sections = [
        "# Init Agent Draft",
        "",
        f"Status: {draft.status.value}",
        "",
        f"Goal: {draft.user_goal}",
        "",
    ]
    for proposal in draft.proposed_files:
        sections.extend(
            [
                f"## {proposal.path}",
                "",
                f"Status: {proposal.status.value}",
                "",
                "```text",
                proposal.content.rstrip(),
                "```",
                "",
            ]
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "x"
    with target.open(mode, encoding="utf-8") as handle:
        handle.write("\n".join(sections).rstrip() + "\n")
    return target
