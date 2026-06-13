from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot


@dataclass(frozen=True, slots=True)
class ChangedFile:
    status: str
    path: str
    original_path: str | None = None

    @property
    def display(self) -> str:
        if self.original_path:
            return f"{self.status}  {self.original_path} -> {self.path}"
        return f"{self.status}  {self.path}"


@dataclass(frozen=True, slots=True)
class FileSnapshot:
    existed: bool
    content: bytes | None
    mode: int | None
    symlink_target: str | None
    index_mode: str | None
    index_object: str | None


@dataclass(frozen=True, slots=True)
class GitBaseline:
    repository: Path
    changed_files: tuple[ChangedFile, ...]
    snapshots: dict[str, FileSnapshot]
    tracked_files: frozenset[str]


@dataclass(frozen=True, slots=True)
class RepositoryState:
    is_git_repository: bool
    files: tuple[ChangedFile, ...] = ()
    diff: str = ""
    message: str = ""


@dataclass(frozen=True, slots=True)
class RejectResult:
    restored_paths: tuple[str, ...]
    archived_paths: tuple[str, ...]
    archive_directory: Path | None


@dataclass(frozen=True, slots=True)
class RejectOutcome:
    result: RejectResult
    state: RepositoryState


class GitManager:
    def __init__(self, repository: Path) -> None:
        self.repository = repository.resolve()

    def is_repository(self) -> bool:
        result = self._run(
            ["rev-parse", "--is-inside-work-tree"], check=False
        )
        return result.returncode == 0 and result.stdout.strip() == b"true"

    def inspect(self) -> RepositoryState:
        if not self.is_repository():
            return RepositoryState(
                is_git_repository=False,
                message="The selected folder is not a Git repository.",
            )

        files = tuple(self.changed_files())
        working = self._run(
            ["diff", "--no-ext-diff", "--binary", "--"], check=True
        ).stdout
        staged = self._run(
            ["diff", "--cached", "--no-ext-diff", "--binary", "--"],
            check=True,
        ).stdout
        sections: list[str] = []
        if staged:
            sections.append("# Staged changes\n" + staged.decode("utf-8", "replace"))
        if working:
            sections.append(
                "# Working tree changes\n"
                + working.decode("utf-8", "replace")
            )

        untracked = [item.path for item in files if item.status == "??"]
        if untracked:
            sections.append(
                "# Untracked files\n"
                + "\n".join(f"?? {path}" for path in untracked)
                + "\n"
            )

        return RepositoryState(
            is_git_repository=True,
            files=files,
            diff="\n".join(sections),
            message="Repository state loaded.",
        )

    def changed_files(self) -> list[ChangedFile]:
        output = self._run(
            ["status", "--porcelain=v1", "-z", "--untracked-files=all"],
            check=True,
        ).stdout
        records = output.decode("utf-8", "surrogateescape").split("\0")
        changed: list[ChangedFile] = []
        index = 0
        while index < len(records):
            record = records[index]
            index += 1
            if not record:
                continue
            status_code = record[:2]
            path = record[3:]
            original_path = None
            if status_code[0] in {"R", "C"}:
                if index < len(records):
                    original_path = records[index]
                    index += 1
            changed.append(
                ChangedFile(
                    status=status_code,
                    path=path,
                    original_path=original_path,
                )
            )
        return changed

    def capture_baseline(self) -> GitBaseline:
        if not self.is_repository():
            raise ValueError("The selected folder is not a Git repository.")

        changed = tuple(self.changed_files())
        tracked_output = self._run(["ls-files", "-z"], check=True).stdout
        tracked = frozenset(
            item
            for item in tracked_output.decode(
                "utf-8", "surrogateescape"
            ).split("\0")
            if item
        )
        paths = {
            path
            for item in changed
            for path in (item.path, item.original_path)
            if path
        }
        snapshots = {path: self._snapshot(path) for path in paths}
        return GitBaseline(
            repository=self.repository,
            changed_files=changed,
            snapshots=snapshots,
            tracked_files=tracked,
        )

    def reject_changes(
        self,
        baseline: GitBaseline,
        task_id: str,
        archive_root: Path | None = None,
    ) -> RejectResult:
        if baseline.repository.resolve() != self.repository:
            raise ValueError("The Git baseline belongs to another repository.")
        if not self.is_repository():
            raise ValueError("The selected folder is not a Git repository.")

        current = self.changed_files()
        current_paths = {
            path
            for item in current
            for path in (item.path, item.original_path)
            if path
        }
        paths = current_paths | set(baseline.snapshots)
        archive_directory = (
            archive_root
            if archive_root is not None
            else Path(tempfile.gettempdir()) / "agentboard-rejected" / task_id
        )
        restored: list[str] = []
        archived: list[str] = []

        for relative_path in sorted(paths):
            snapshot = baseline.snapshots.get(relative_path)
            if snapshot is not None:
                self._restore_snapshot(
                    relative_path,
                    snapshot,
                    archive_directory,
                    archived,
                )
                restored.append(relative_path)
            elif relative_path in baseline.tracked_files:
                self._run(
                    [
                        "restore",
                        "--source=HEAD",
                        "--staged",
                        "--worktree",
                        "--",
                        relative_path,
                    ],
                    check=True,
                )
                restored.append(relative_path)
            else:
                if self._archive_path(
                    relative_path, archive_directory
                ) is not None:
                    archived.append(relative_path)
                self._run(
                    ["update-index", "--force-remove", "--", relative_path],
                    check=True,
                )

        return RejectResult(
            restored_paths=tuple(restored),
            archived_paths=tuple(archived),
            archive_directory=archive_directory if archived else None,
        )

    def _snapshot(self, relative_path: str) -> FileSnapshot:
        path = self._path(relative_path)
        existed = path.exists() or path.is_symlink()
        content: bytes | None = None
        mode: int | None = None
        symlink_target: str | None = None
        if existed:
            file_stat = path.lstat()
            mode = stat.S_IMODE(file_stat.st_mode)
            if path.is_symlink():
                symlink_target = os.readlink(path)
            elif path.is_file():
                content = path.read_bytes()

        index_mode = None
        index_object = None
        entry = self._run(
            ["ls-files", "--stage", "--", relative_path], check=True
        ).stdout.decode("utf-8", "surrogateescape").strip()
        if entry:
            metadata = entry.split(maxsplit=3)
            if len(metadata) >= 2:
                index_mode, index_object = metadata[0], metadata[1]

        return FileSnapshot(
            existed=existed,
            content=content,
            mode=mode,
            symlink_target=symlink_target,
            index_mode=index_mode,
            index_object=index_object,
        )

    def _restore_snapshot(
        self,
        relative_path: str,
        snapshot: FileSnapshot,
        archive_directory: Path,
        archived: list[str],
    ) -> None:
        if snapshot.index_mode and snapshot.index_object:
            self._run(
                [
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    snapshot.index_mode,
                    snapshot.index_object,
                    relative_path,
                ],
                check=True,
            )
        else:
            self._run(
                ["update-index", "--force-remove", "--", relative_path],
                check=True,
            )

        path = self._path(relative_path)
        if not snapshot.existed:
            if self._archive_path(relative_path, archive_directory) is not None:
                archived.append(relative_path)
            return

        path.parent.mkdir(parents=True, exist_ok=True)
        if snapshot.symlink_target is not None:
            if path.exists() or path.is_symlink():
                if path.is_symlink():
                    path.unlink()
                else:
                    archived_path = self._archive_path(
                        relative_path, archive_directory
                    )
                    if archived_path is not None:
                        archived.append(relative_path)
            path.symlink_to(snapshot.symlink_target)
        elif snapshot.content is not None:
            if path.is_symlink() or path.is_dir():
                archived_path = self._archive_path(
                    relative_path, archive_directory
                )
                if archived_path is not None:
                    archived.append(relative_path)
            path.write_bytes(snapshot.content)

        if snapshot.mode is not None and not path.is_symlink():
            path.chmod(snapshot.mode)

    def _archive_path(
        self, relative_path: str, archive_directory: Path
    ) -> Path | None:
        source = self._path(relative_path)
        if not source.exists() and not source.is_symlink():
            return None

        destination = archive_directory / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() or destination.is_symlink():
            counter = 1
            while True:
                candidate = destination.with_name(
                    f"{destination.name}.{counter}"
                )
                if not candidate.exists() and not candidate.is_symlink():
                    destination = candidate
                    break
                counter += 1
        shutil.move(str(source), str(destination))
        return destination

    def _path(self, relative_path: str) -> Path:
        root = Path(os.path.abspath(self.repository))
        candidate = Path(os.path.abspath(root / relative_path))
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                f"Git returned a path outside the repository: {relative_path}"
            ) from exc
        return candidate

    def _run(
        self, args: list[str], *, check: bool
    ) -> subprocess.CompletedProcess[bytes]:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repository,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env={**os.environ, "GIT_PAGER": "cat"},
        )
        if check and result.returncode != 0:
            message = result.stderr.decode("utf-8", "replace").strip()
            raise RuntimeError(message or f"Git exited with {result.returncode}.")
        return result


class GitInspectWorker(QObject):
    state_ready = Signal(object)
    failed = Signal(str)
    terminal = Signal()

    def __init__(self, repository: Path) -> None:
        super().__init__()
        self.repository = repository

    @Slot()
    def run(self) -> None:
        try:
            self.state_ready.emit(GitManager(self.repository).inspect())
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.terminal.emit()


class RejectWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)
    terminal = Signal()

    def __init__(
        self, baseline: GitBaseline, task_id: str
    ) -> None:
        super().__init__()
        self.baseline = baseline
        self.task_id = task_id

    @Slot()
    def run(self) -> None:
        try:
            manager = GitManager(self.baseline.repository)
            result = manager.reject_changes(self.baseline, self.task_id)
            self.completed.emit(
                RejectOutcome(result=result, state=manager.inspect())
            )
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.terminal.emit()
