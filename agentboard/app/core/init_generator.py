from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from agentboard.app.models import Project


@dataclass(frozen=True, slots=True)
class InitPlanResult:
    markdown: str
    candidate_files: tuple[str, ...]
    existing_files: tuple[str, ...]
    warnings: tuple[str, ...]


class InitGenerator:
    COMMON_FILES = (
        "README.md",
        ".gitignore",
        "tests/",
    )

    def generate(self, project: Project) -> InitPlanResult:
        repository = project.repo_path
        existing = self._existing(repository)
        candidates = self._candidates(repository, existing)
        warnings = [
            "Generation is read-only; no files were created or overwritten.",
            "Review every candidate before using Apply Selected Files.",
        ]
        if any(repository.iterdir()):
            warnings.append(
                "Existing project detected. Preserve current structure and conventions."
            )
        markdown = "\n".join(
            [
                f"# {project.name} Safe Init Plan",
                "",
                "## Project Goal",
                project.goal.strip()
                or "No project goal has been recorded yet.",
                "",
                "## Suggested Structure",
                "```text",
                f"{repository.name}/",
                "  README.md",
                "  src/ or application package/",
                "  tests/",
                "  project dependency manifest",
                "  .gitignore",
                "```",
                "",
                "## Files That Could Be Created",
                *([f"- {item}" for item in candidates] or ["- None detected."]),
                "",
                "## Files Already Present",
                *([f"- {item}" for item in existing] or ["- None detected."]),
                "",
                "## Setup Recommendations",
                "- Keep one documented local launch command.",
                "- Add a focused automated test entry point.",
                "- Keep generated output and local environments out of Git.",
                "- Document required runtimes and dependency installation.",
                "",
                "## Warnings",
                *[f"- {warning}" for warning in warnings],
            ]
        )
        return InitPlanResult(
            markdown=markdown,
            candidate_files=tuple(candidates),
            existing_files=tuple(existing),
            warnings=tuple(warnings),
        )

    def apply_selected(
        self, project: Project, selected_files: list[str]
    ) -> tuple[str, ...]:
        created: list[str] = []
        for relative in selected_files:
            if relative not in {
                "README.md",
                ".gitignore",
                "tests/",
                "pyproject.toml",
                "package.json",
            }:
                continue
            target = project.repo_path / relative.rstrip("/")
            if target.exists():
                continue
            if relative.endswith("/"):
                target.mkdir(parents=True, exist_ok=False)
                created.append(relative)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as handle:
                handle.write(self._template(relative, project))
            created.append(relative)
        return tuple(created)

    def _existing(self, repository: Path) -> list[str]:
        candidates = [
            *self.COMMON_FILES,
            "pyproject.toml",
            "requirements.txt",
            "package.json",
            "src/",
            "app/",
        ]
        return [
            name
            for name in candidates
            if (repository / name.rstrip("/")).exists()
        ]

    @staticmethod
    def _candidates(repository: Path, existing: list[str]) -> list[str]:
        candidates = ["README.md", ".gitignore", "tests/"]
        if not (repository / "pyproject.toml").exists() and not (
            repository / "requirements.txt"
        ).exists() and not (repository / "package.json").exists():
            has_javascript = any(
                path.suffix in {".js", ".jsx", ".ts", ".tsx"}
                for path in repository.rglob("*")
                if path.is_file()
            )
            candidates.append(
                "package.json" if has_javascript else "pyproject.toml"
            )
        return [item for item in candidates if item not in existing]

    @staticmethod
    def _template(relative: str, project: Project) -> str:
        package_name = re.sub(
            r"[^a-z0-9]+", "-", project.name.casefold()
        ).strip("-") or "local-project"
        templates = {
            "README.md": (
                f"# {project.name}\n\n"
                f"{project.goal or 'Describe the project goal here.'}\n\n"
                "## Setup\n\nDocument local setup and launch commands.\n"
            ),
            ".gitignore": (
                ".venv/\nnode_modules/\n__pycache__/\n*.py[cod]\n"
                ".pytest_cache/\n.DS_Store\n"
            ),
            "pyproject.toml": (
                "[project]\n"
                f'name = "{package_name}"\n'
                'version = "0.1.0"\n'
                'requires-python = ">=3.10"\n'
            ),
            "package.json": (
                "{\n"
                f'  "name": "{package_name}",\n'
                '  "version": "0.1.0",\n'
                '  "private": true\n'
                "}\n"
            ),
        }
        return templates.get(relative, "")
