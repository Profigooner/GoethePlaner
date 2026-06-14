from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agentboard.app.models import Project

from .agent_selector import AgentSelector


@dataclass(frozen=True, slots=True)
class RoadmapResult:
    markdown: str
    suggested_next_tasks: tuple[str, ...]
    detected_stack: tuple[str, ...]
    agent_recommendations: tuple[str, ...]


class RoadmapGenerator:
    MAX_ENTRIES = 120
    MAX_README_CHARS = 3_000

    def generate(self, project: Project) -> RoadmapResult:
        entries = self._entries(project.repo_path)
        stack = self._detect_stack(project.repo_path, entries)
        readme = self._readme_excerpt(project.repo_path)
        summary = (
            project.goal.strip()
            or self._summary_from_readme(readme)
            or f"Maintain and evolve the {project.name} codebase."
        )
        task_context = " ".join(
            task.original_prompt for task in project.tasks[-5:]
        )
        selection = AgentSelector().select(
            f"{summary}\n{task_context}", project.name
        )
        next_tasks = self._next_tasks(stack, bool(project.tasks))
        architecture = self._architecture_guess(entries, stack)
        risks = self._risk_areas(entries, stack)
        tests = self._testing_strategy(entries, stack)
        agent_names = tuple(
            selection.selected_agents
        )
        stack_lines = (
            [f"- {item}" for item in stack]
            if stack
            else ["- No framework markers detected."]
        )
        markdown = "\n".join(
            [
                f"# {project.name} Generated Roadmap",
                "",
                "## Project Summary",
                summary,
                "",
                "## Current Architecture Guess",
                architecture,
                "",
                "## Detected Stack",
                *stack_lines,
                "",
                "## Suggested Milestones",
                "1. Establish a reliable baseline and document current behavior.",
                "2. Complete the highest-value functional work in focused tasks.",
                "3. Expand regression coverage and operational safeguards.",
                "4. Review architecture, documentation, and release readiness.",
                "",
                "## Recommended Next Tasks",
                *[
                    f"{index}. {task}"
                    for index, task in enumerate(next_tasks, start=1)
                ],
                "",
                "## Risk Areas",
                *[f"- {item}" for item in risks],
                "",
                "## Testing Strategy",
                *[f"- {item}" for item in tests],
                "",
                "## Agent Recommendations",
                *[
                    f"- {agent_id}: {selection.reasons.get(agent_id, 'Recommended by planner.')}"
                    for agent_id in agent_names
                ],
                "",
                "> Generated read-only by GoethePlaner. Review before exporting.",
            ]
        )
        return RoadmapResult(
            markdown=markdown,
            suggested_next_tasks=tuple(next_tasks),
            detected_stack=tuple(stack),
            agent_recommendations=agent_names,
        )

    def _entries(self, repository: Path) -> list[str]:
        try:
            return sorted(
                item.name for item in repository.iterdir()
            )[: self.MAX_ENTRIES]
        except OSError:
            return []

    @staticmethod
    def _detect_stack(repository: Path, entries: list[str]) -> list[str]:
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
        stack = []
        for marker, label in markers.items():
            if marker in entries and label not in stack:
                stack.append(label)
        if (repository / "agentboard" / "app" / "ui").is_dir():
            stack.append("PySide6 desktop UI")
        return stack

    def _readme_excerpt(self, repository: Path) -> str:
        for name in ("README.md", "README.rst", "README.txt"):
            path = repository / name
            if path.is_file():
                try:
                    return path.read_text(
                        encoding="utf-8", errors="replace"
                    )[: self.MAX_README_CHARS]
                except OSError:
                    return ""
        return ""

    @staticmethod
    def _summary_from_readme(readme: str) -> str:
        lines = [
            line.strip()
            for line in readme.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        return lines[0][:400] if lines else ""

    @staticmethod
    def _architecture_guess(entries: list[str], stack: list[str]) -> str:
        folders = [
            item
            for item in entries
            if item
            in {
                "app",
                "src",
                "tests",
                "docs",
                "agentboard",
                "frontend",
                "backend",
            }
        ]
        folder_text = ", ".join(folders) if folders else "a flat repository root"
        stack_text = ", ".join(stack) if stack else "an undetected stack"
        return (
            f"The repository appears to use {stack_text}, organized around "
            f"{folder_text}. This is a heuristic based on top-level markers."
        )

    @staticmethod
    def _next_tasks(stack: list[str], has_history: bool) -> list[str]:
        tasks = [
            "Document the current architecture and supported local setup.",
            "Run the existing test suite and establish a clean regression baseline.",
            "Prioritize one focused product milestone with explicit acceptance criteria.",
        ]
        if "Python" in stack:
            tasks.append("Review Python packaging, typing, and test coverage.")
        if "Node.js / JavaScript" in stack:
            tasks.append("Review dependency scripts, linting, and runtime compatibility.")
        if has_history:
            tasks.append("Review recent task results and unresolved risks.")
        return tasks

    @staticmethod
    def _risk_areas(entries: list[str], stack: list[str]) -> list[str]:
        risks = [
            "Generated architecture assumptions require maintainer review.",
            "Concurrent edits outside GoethePlaner cannot be attributed safely.",
        ]
        if "tests" not in entries:
            risks.append("No top-level tests directory was detected.")
        if not stack:
            risks.append("Language and framework markers were not detected.")
        return risks

    @staticmethod
    def _testing_strategy(entries: list[str], stack: list[str]) -> list[str]:
        strategy = [
            "Run focused tests for every changed behavior.",
            "Run the repository's broader suite before accepting generated changes.",
            "Preserve a Git baseline before any code-modifying agent executes.",
        ]
        if "Python" in stack:
            strategy.append("Use the configured Python test runner and compile checks.")
        if "Node.js / JavaScript" in stack:
            strategy.append("Use package scripts for tests, linting, and type checks.")
        return strategy
