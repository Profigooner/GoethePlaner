from __future__ import annotations

import difflib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from agentboard.app.models import (
    InitDraft,
    Project,
    ProposedFile,
    ProposedFileStatus,
    RoadmapDraft,
)


@dataclass(frozen=True, slots=True)
class RepositoryContext:
    readme: str
    detected_stack: tuple[str, ...]
    structure: tuple[str, ...]


def inspect_repository(project: Project) -> RepositoryContext:
    repository = project.repo_path
    readme = ""
    for name in ("README.md", "README.rst", "README.txt"):
        path = repository / name
        if not path.is_file():
            continue
        try:
            readme = path.read_text(
                encoding="utf-8", errors="replace"
            )[:8_000]
        except OSError:
            readme = ""
        break

    structure: list[str] = []
    try:
        paths = sorted(repository.rglob("*"), key=lambda item: item.as_posix())
    except OSError:
        paths = []
    for path in paths:
        relative = path.relative_to(repository)
        if any(
            part in {".git", ".venv", "node_modules", "__pycache__"}
            for part in relative.parts
        ):
            continue
        suffix = "/" if path.is_dir() else ""
        structure.append(f"{relative.as_posix()}{suffix}")
        if len(structure) >= 160:
            break

    names = {item.split("/", 1)[0] for item in structure}
    markers = {
        "pyproject.toml": "Python",
        "requirements.txt": "Python",
        "package.json": "Node.js / JavaScript",
        "tsconfig.json": "TypeScript",
        "Cargo.toml": "Rust",
        "go.mod": "Go",
        "Dockerfile": "Docker",
        "docker-compose.yml": "Docker Compose",
        "CMakeLists.txt": "C / C++",
    }
    stack: list[str] = []
    for marker, label in markers.items():
        if marker in names and label not in stack:
            stack.append(label)
    if (repository / "agentboard" / "app" / "ui").is_dir():
        stack.append("PySide6 desktop UI")
    return RepositoryContext(readme, tuple(stack), tuple(structure))


def build_roadmap_prompt(
    project: Project,
    goal: str,
    constraints: str,
    *,
    target_users: str = "",
    mvp_scope: str = "",
    notes: str = "",
    previous_draft: RoadmapDraft | None = None,
    feedback: str = "",
) -> str:
    context = inspect_repository(project)
    revision = ""
    if previous_draft is not None:
        revision = (
            "\nPrevious roadmap draft:\n"
            f"{previous_draft.draft_content[:30_000]}\n"
            "\nUser feedback to apply:\n"
            f"{feedback.strip()}\n"
            "Revise the previous draft rather than starting from generic advice.\n"
        )
    return f"""You are the Roadmap Agent for GoethePlaner.

Work in planning/read-only mode. Inspect and reason about the repository.
Do not modify files or run destructive commands.

Repository path:
{project.repo_path}

Project name:
{project.name}

Project goal:
{goal.strip()}

Target users:
{target_users.strip() or "Not specified"}

Desired MVP scope:
{mvp_scope.strip() or "Not specified"}

Technical constraints:
{constraints.strip() or "None supplied"}

Optional notes:
{notes.strip() or "None supplied"}

Detected languages and frameworks:
{", ".join(context.detected_stack) or "No reliable markers detected"}

Repository structure summary:
{chr(10).join(context.structure) or "(empty repository)"}

Existing README content:
{context.readme or "(no README found)"}
{revision}
Generate a practical development roadmap grounded in this repository. Include
clear milestones, concrete next tasks, risks, and a testing strategy. Do not
claim that files were changed.

Return strict JSON only with this shape:
{{
  "draft_content": "# Markdown roadmap...",
  "reasoning_summary": "Short user-facing explanation, not hidden chain of thought.",
  "repository_observations": ["observation"],
  "suggested_milestones": ["milestone"],
  "suggested_next_tasks": ["task"],
  "risks": ["risk"],
  "testing_strategy": ["test strategy item"]
}}
"""


def build_init_prompt(
    project: Project,
    goal: str,
    *,
    previous_draft: InitDraft | None = None,
    feedback: str = "",
) -> str:
    context = inspect_repository(project)
    revision = ""
    if previous_draft is not None:
        previous = [
            {"path": item.path, "content": item.content[:20_000]}
            for item in previous_draft.proposed_files
        ]
        revision = (
            "\nPrevious proposed files:\n"
            f"{json.dumps(previous, indent=2)}\n"
            "\nUser feedback to apply:\n"
            f"{feedback.strip()}\n"
            "Revise the proposals while preserving repository conventions.\n"
        )
    return f"""You are the Init Agent for GoethePlaner.
Inspect this repository and generate initialization documentation similar to an
OpenCode /init workflow.

Repository path:
{project.repo_path}

Project name:
{project.name}

Project init goal:
{goal.strip()}

Detected languages and frameworks:
{", ".join(context.detected_stack) or "No reliable markers detected"}

Repository structure summary:
{chr(10).join(context.structure) or "(empty repository)"}

Existing README content:
{context.readme or "(no README found)"}
{revision}
Generate proposed contents for README.md, AGENTS.md, project setup instructions,
development workflow notes, test commands, architecture overview, and coding
rules. You may place setup, workflow, tests, and architecture in README.md or
AGENTS.md when that best fits the repository. Propose optional configuration
files only when repository evidence supports them.

Do not modify files directly. Do not execute setup or migration commands. Return
proposed file contents for user review.

Return strict JSON only with this shape:
{{
  "reasoning_summary": "Short user-facing explanation, not hidden chain of thought.",
  "repository_observations": ["observation"],
  "setup_notes": ["note"],
  "proposed_files": [
    {{"path": "README.md", "content": "# Complete proposed content"}},
    {{"path": "AGENTS.md", "content": "# Complete proposed content"}}
  ]
}}
"""


def parse_roadmap_output(
    project: Project,
    goal: str,
    output: str,
    *,
    previous_draft: RoadmapDraft | None = None,
    feedback: str = "",
) -> RoadmapDraft:
    data = _parse_json_object(output)
    content = str(data.get("draft_content", "")).strip()
    if not content:
        raise ValueError("Roadmap Agent returned no draft_content.")
    return RoadmapDraft(
        project_id=project.id,
        user_goal=goal.strip(),
        draft_content=content,
        id=previous_draft.id if previous_draft else _new_id(),
        feedback_history=[
            *(previous_draft.feedback_history if previous_draft else []),
            *([feedback.strip()] if feedback.strip() else []),
        ],
        created_at=(
            previous_draft.created_at
            if previous_draft is not None
            else _now()
        ),
        reasoning_summary=str(data.get("reasoning_summary", "")).strip(),
        repository_observations=_string_list(
            data.get("repository_observations")
        ),
        suggested_milestones=_string_list(data.get("suggested_milestones")),
        suggested_next_tasks=_string_list(data.get("suggested_next_tasks")),
        risks=_string_list(data.get("risks")),
        testing_strategy=_string_list(data.get("testing_strategy")),
    )


def parse_init_output(
    project: Project,
    goal: str,
    output: str,
    *,
    previous_draft: InitDraft | None = None,
    feedback: str = "",
) -> InitDraft:
    data = _parse_json_object(output)
    raw_files = data.get("proposed_files")
    if not isinstance(raw_files, list):
        raise ValueError("Init Agent returned no proposed_files list.")
    proposals = hydrate_proposed_files(project.repo_path, raw_files)
    if not proposals:
        raise ValueError("Init Agent returned no safe file proposals.")
    return InitDraft(
        project_id=project.id,
        user_goal=goal.strip(),
        proposed_files=proposals,
        id=previous_draft.id if previous_draft else _new_id(),
        feedback_history=[
            *(previous_draft.feedback_history if previous_draft else []),
            *([feedback.strip()] if feedback.strip() else []),
        ],
        created_at=(
            previous_draft.created_at
            if previous_draft is not None
            else _now()
        ),
        reasoning_summary=str(data.get("reasoning_summary", "")).strip(),
        repository_observations=_string_list(
            data.get("repository_observations")
        ),
        setup_notes=_string_list(data.get("setup_notes")),
    )


def hydrate_proposed_files(
    repository: Path, raw_files: list[Any]
) -> list[ProposedFile]:
    proposals: list[ProposedFile] = []
    seen: set[str] = set()
    for raw in raw_files:
        if not isinstance(raw, dict):
            continue
        relative = str(raw.get("path", "")).strip().replace("\\", "/")
        content = str(raw.get("content", ""))
        if not relative or relative in seen or not _is_safe_relative(relative):
            continue
        seen.add(relative)
        target = repository / PurePosixPath(relative)
        existing = ""
        status = ProposedFileStatus.NEW
        if target.exists():
            if target.is_symlink() or not target.is_file():
                status = ProposedFileStatus.CONFLICT
            else:
                try:
                    existing = target.read_text(
                        encoding="utf-8", errors="replace"
                    )
                    status = ProposedFileStatus.UPDATE
                except OSError:
                    status = ProposedFileStatus.CONFLICT
        diff = "".join(
            difflib.unified_diff(
                existing.splitlines(keepends=True),
                content.splitlines(keepends=True),
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
            )
        )
        proposals.append(
            ProposedFile(
                path=relative,
                content=content,
                existing_content=existing,
                status=status,
                selected=status != ProposedFileStatus.CONFLICT,
                diff_preview=diff,
            )
        )
    return proposals


def mock_roadmap_draft(
    project: Project,
    goal: str,
    constraints: str,
    *,
    target_users: str = "",
    mvp_scope: str = "",
    notes: str = "",
    previous_draft: RoadmapDraft | None = None,
    feedback: str = "",
) -> RoadmapDraft:
    context = inspect_repository(project)
    stack = ", ".join(context.detected_stack) or "the detected project stack"
    feedback_line = (
        f"\n\n## Revision Notes\nThis revision addresses: {feedback.strip()}"
        if feedback.strip()
        else ""
    )
    content = "\n".join(
        [
            f"# {project.name} Roadmap Draft",
            "",
            "## Product Goal",
            goal.strip(),
            "",
            "## Target Users",
            target_users.strip() or "Confirm the primary user group.",
            "",
            "## MVP Scope",
            mvp_scope.strip()
            or "Deliver one end-to-end workflow with explicit acceptance criteria.",
            "",
            "## Technical Direction",
            f"Build on {stack}. Preserve current repository conventions.",
            constraints.strip() or "No additional technical constraints supplied.",
            "",
            "## Milestones",
            "1. Validate the current behavior and establish a regression baseline.",
            "2. Implement the highest-value user workflow end to end.",
            "3. Add failure handling, safety checks, and focused tests.",
            "4. Complete documentation and release verification.",
            "",
            "## Suggested Next Tasks",
            "1. Document current architecture and supported setup commands.",
            "2. Define measurable MVP acceptance criteria.",
            "3. Implement the first vertical feature slice with tests.",
            "4. Review operational risks and release readiness.",
            "",
            "## Risks",
            "- Repository assumptions require maintainer review.",
            "- Existing user files and local changes must be preserved.",
            "- Untested integration paths can hide release regressions.",
            "",
            "## Testing Strategy",
            "- Run focused tests for every changed behavior.",
            "- Run the full project suite before acceptance.",
            "- Add UI or integration coverage for the primary user workflow.",
            feedback_line,
        ]
    ).strip()
    draft = RoadmapDraft(
        project_id=project.id,
        user_goal=goal.strip(),
        draft_content=content,
        id=previous_draft.id if previous_draft else _new_id(),
        feedback_history=[
            *(previous_draft.feedback_history if previous_draft else []),
            *([feedback.strip()] if feedback.strip() else []),
        ],
        created_at=previous_draft.created_at if previous_draft else _now(),
        reasoning_summary=(
            "Mock Roadmap Agent inspected repository markers and converted the "
            "goal into phased, reviewable delivery work."
        ),
        repository_observations=[
            f"Detected stack: {stack}.",
            f"Reviewed {len(context.structure)} bounded structure entries.",
            "An existing README was found."
            if context.readme
            else "No existing README was found.",
        ],
        suggested_milestones=[
            "Baseline and architecture",
            "MVP implementation",
            "Safety and regression coverage",
            "Release readiness",
        ],
        suggested_next_tasks=[
            "Document current architecture and setup.",
            "Define MVP acceptance criteria.",
            "Implement the first vertical feature slice.",
            "Review release risks.",
        ],
        risks=[
            "Repository assumptions require maintainer review.",
            "Existing user files must be preserved.",
        ],
        testing_strategy=[
            "Run focused behavioral tests.",
            "Run the full suite before acceptance.",
            "Cover the primary workflow with integration tests.",
        ],
    )
    return draft


def mock_init_draft(
    project: Project,
    goal: str,
    *,
    previous_draft: InitDraft | None = None,
    feedback: str = "",
) -> InitDraft:
    context = inspect_repository(project)
    stack = ", ".join(context.detected_stack) or "Undetected"
    test_command = (
        "QT_QPA_PLATFORM=offscreen python -m unittest discover -v"
        if "Python" in context.detected_stack
        else "Use the repository's documented test command."
    )
    revision_note = (
        f"\n\n## Requested Revision\n{feedback.strip()}"
        if feedback.strip()
        else ""
    )
    readme = (
        f"# {project.name}\n\n"
        f"{goal.strip()}\n\n"
        "## Stack\n\n"
        f"{stack}\n\n"
        "## Setup\n\n"
        "Install the repository dependencies in an isolated local environment.\n\n"
        "## Development\n\n"
        "Keep changes focused, preserve existing user work, and review generated "
        "diffs before acceptance.\n\n"
        "## Tests\n\n"
        f"```bash\n{test_command}\n```\n"
        f"{revision_note}\n"
    )
    agents = (
        f"# AGENTS.md\n\n"
        f"## Project Goal\n\n{goal.strip()}\n\n"
        "## Architecture\n\n"
        f"The repository currently exposes {len(context.structure)} bounded "
        f"structure entries and uses: {stack}.\n\n"
        "## Working Rules\n\n"
        "- Inspect existing code and conventions before editing.\n"
        "- Do not overwrite user files or discard local changes silently.\n"
        "- Use argument-list subprocess calls with `shell=False`.\n"
        "- Add focused tests for changed behavior.\n"
        "- Report verification results and remaining risks.\n\n"
        "## Test Command\n\n"
        f"`{test_command}`\n"
        f"{revision_note}\n"
    )
    raw_files: list[dict[str, str]] = [
        {"path": "README.md", "content": readme},
        {"path": "AGENTS.md", "content": agents},
    ]
    if not (project.repo_path / ".gitignore").exists():
        raw_files.append(
            {
                "path": ".gitignore",
                "content": ".venv/\n__pycache__/\n*.py[cod]\n.DS_Store\n",
            }
        )
    draft = InitDraft(
        project_id=project.id,
        user_goal=goal.strip(),
        proposed_files=hydrate_proposed_files(project.repo_path, raw_files),
        id=previous_draft.id if previous_draft else _new_id(),
        feedback_history=[
            *(previous_draft.feedback_history if previous_draft else []),
            *([feedback.strip()] if feedback.strip() else []),
        ],
        created_at=previous_draft.created_at if previous_draft else _now(),
        reasoning_summary=(
            "Mock Init Agent inspected repository markers and proposed complete "
            "reviewable documentation files."
        ),
        repository_observations=[
            f"Detected stack: {stack}.",
            "README.md exists and is proposed as an update."
            if (project.repo_path / "README.md").exists()
            else "README.md is missing and is proposed as a new file.",
            "AGENTS.md exists and is proposed as an update."
            if (project.repo_path / "AGENTS.md").exists()
            else "AGENTS.md is missing and is proposed as a new file.",
        ],
        setup_notes=[
            "Review every proposed file and diff.",
            f"Suggested test command: {test_command}",
        ],
    )
    return draft


def _parse_json_object(output: str) -> dict[str, Any]:
    text = output.strip()
    if text.startswith("```"):
        first_newline = text.find("\n")
        last_fence = text.rfind("```")
        if first_newline != -1 and last_fence > first_newline:
            text = text[first_newline + 1 : last_fence].strip()
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(
                "Agent output did not contain a structured JSON object."
            )
        try:
            decoded = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Agent output was not valid structured JSON: {exc}"
            ) from exc
    if not isinstance(decoded, dict):
        raise ValueError("Agent output JSON must be an object.")
    return decoded


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _is_safe_relative(path: str) -> bool:
    relative = PurePosixPath(path)
    return (
        not relative.is_absolute()
        and bool(relative.parts)
        and ".." not in relative.parts
        and relative.parts[0] not in {"", "."}
    )


def _new_id() -> str:
    from uuid import uuid4

    return uuid4().hex


def _now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
