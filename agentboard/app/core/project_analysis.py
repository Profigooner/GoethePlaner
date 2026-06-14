from __future__ import annotations

import json
from pathlib import Path

from agentboard.app.models import (
    Project,
    ProjectAnalysis,
    ProjectDocument,
    ProjectResourceStatus,
)


DOCUMENT_NAMES = (
    "README.md",
    "ROADMAP.md",
    "ROADMAP.generated.md",
    "AGENTS.md",
    "AGENT.md",
    "CLAUDE.md",
    "TODO.md",
    "pyproject.toml",
    "package.json",
    "requirements.txt",
)
INIT_DOCUMENT_NAMES = (
    "AGENTS.md",
    "AGENT.md",
    "CLAUDE.md",
    "README.md",
    "TODO.md",
)
MAX_IMPORTED_CHARS = 100_000


class ProjectAnalyzer:
    def analyze(self, repository: Path) -> ProjectAnalysis:
        repo = Path(repository).expanduser().resolve()
        if not repo.is_dir():
            raise ValueError("Project repository must be an existing directory.")
        documents = tuple(
            name for name in DOCUMENT_NAMES if (repo / name).is_file()
        )
        stack = self._detect_stack(repo, documents)
        detected_type = self._detected_type(stack)
        roadmap_path = next(
            (
                name
                for name in ("ROADMAP.md", "ROADMAP.generated.md")
                if name in documents
            ),
            None,
        )
        init_paths = tuple(
            name for name in INIT_DOCUMENT_NAMES if name in documents
        )
        missing: list[str] = []
        if "README.md" not in documents:
            missing.append("README.md")
        if roadmap_path is None:
            missing.append("ROADMAP.md")
        if not any(
            name in documents
            for name in ("AGENTS.md", "AGENT.md", "CLAUDE.md")
        ):
            missing.append("AGENTS.md")
        actions: list[str] = []
        if documents:
            actions.append("Review and import existing project documentation.")
        if roadmap_path is None:
            actions.append("Create a Roadmap draft with the Roadmap Agent.")
        if not any(
            name in documents
            for name in ("AGENTS.md", "AGENT.md", "CLAUDE.md")
        ):
            actions.append("Run the Init Agent to propose agent instructions.")
        if "README.md" in documents:
            actions.append("Review whether README should be improved.")
        else:
            actions.append("Create README through the Init review flow.")
        return ProjectAnalysis(
            repo_path=repo,
            detected_project_type=detected_type,
            detected_stack=tuple(stack),
            documentation_files=documents,
            missing_important_files=tuple(missing),
            roadmap_path=roadmap_path,
            init_paths=init_paths,
            suggested_actions=tuple(actions),
            is_git_repository=(repo / ".git").exists(),
        )

    def import_existing_documents(
        self, project: Project, analysis: ProjectAnalysis
    ) -> tuple[ProjectDocument, ...]:
        if analysis.repo_path.resolve() != project.repo_path.resolve():
            raise ValueError("Analysis belongs to another repository.")
        imported: list[ProjectDocument] = []
        for name in analysis.documentation_files:
            path = project.repo_path / name
            try:
                content = path.read_text(
                    encoding="utf-8", errors="replace"
                )[:MAX_IMPORTED_CHARS]
            except OSError:
                continue
            kind = self._document_kind(name)
            document = ProjectDocument(
                project_id=project.id,
                kind=kind,
                path=name,
                content=content,
            )
            project.add_document(document)
            imported.append(document)

        roadmap_document = next(
            (
                item
                for item in imported
                if item.path == analysis.roadmap_path
            ),
            None,
        )
        if roadmap_document is not None:
            project.update_roadmap(
                roadmap_document.content,
                ProjectResourceStatus.IMPORTED.value,
            )

        init_documents = [
            item
            for item in imported
            if item.path in analysis.init_paths
        ]
        if init_documents:
            project.update_init(
                "\n\n".join(
                    f"## {item.path}\n\n{item.content.rstrip()}"
                    for item in init_documents
                ),
                ProjectResourceStatus.IMPORTED.value,
            )
        return tuple(imported)

    def _detect_stack(
        self, repository: Path, documents: tuple[str, ...]
    ) -> list[str]:
        stack: list[str] = []
        markers = {
            "pyproject.toml": "Python",
            "requirements.txt": "Python",
            "package.json": "Node.js / JavaScript",
        }
        for marker, label in markers.items():
            if marker in documents and label not in stack:
                stack.append(label)
        additional = {
            "tsconfig.json": "TypeScript",
            "Cargo.toml": "Rust",
            "go.mod": "Go",
            "Dockerfile": "Docker",
            "docker-compose.yml": "Docker Compose",
            "CMakeLists.txt": "C / C++",
        }
        for marker, label in additional.items():
            if (repository / marker).is_file():
                stack.append(label)
        self._detect_python_frameworks(repository, stack)
        self._detect_node_frameworks(repository, stack)
        return stack

    @staticmethod
    def _detect_python_frameworks(
        repository: Path, stack: list[str]
    ) -> None:
        texts: list[str] = []
        for name in ("pyproject.toml", "requirements.txt"):
            path = repository / name
            if path.is_file():
                try:
                    texts.append(
                        path.read_text(
                            encoding="utf-8", errors="replace"
                        )[:30_000].casefold()
                    )
                except OSError:
                    pass
        combined = "\n".join(texts)
        for token, label in (
            ("pyside6", "PySide6"),
            ("django", "Django"),
            ("fastapi", "FastAPI"),
            ("flask", "Flask"),
        ):
            if token in combined and label not in stack:
                stack.append(label)

    @staticmethod
    def _detect_node_frameworks(
        repository: Path, stack: list[str]
    ) -> None:
        package_path = repository / "package.json"
        if not package_path.is_file():
            return
        try:
            payload = json.loads(
                package_path.read_text(encoding="utf-8")[:100_000]
            )
        except (OSError, ValueError):
            return
        dependencies = {
            **payload.get("dependencies", {}),
            **payload.get("devDependencies", {}),
        }
        for token, label in (
            ("react", "React"),
            ("next", "Next.js"),
            ("vue", "Vue"),
            ("@angular/core", "Angular"),
            ("express", "Express"),
            ("@nestjs/core", "NestJS"),
        ):
            if token in dependencies and label not in stack:
                stack.append(label)

    @staticmethod
    def _detected_type(stack: list[str]) -> str:
        if not stack:
            return "Unknown local project"
        return " / ".join(stack[:3])

    @staticmethod
    def _document_kind(name: str) -> str:
        if name.startswith("ROADMAP"):
            return "roadmap"
        if name == "README.md":
            return "readme"
        if name in {"AGENTS.md", "AGENT.md", "CLAUDE.md"}:
            return "agents"
        if name == "TODO.md":
            return "todo"
        return "setup"
