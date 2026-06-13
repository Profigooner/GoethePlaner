from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QDialog, QMainWindow, QMessageBox

from agentboard.app.core.task_manager import WorkflowWorker
from agentboard.app.core.git_manager import (
    GitBaseline,
    GitInspectWorker,
    RejectOutcome,
    RejectWorker,
    RepositoryState,
)
from agentboard.app.core.test_runner import TestRunResult, TestRunner, TestWorker
from agentboard.app.models import Project, Task, TaskStatus
from agentboard.app.utils.config import AppConfig

from .dialogs import NewProjectDialog, NewTaskDialog
from .task_dashboard import TaskDashboard
from .theme import application_stylesheet


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.config = config
        self.projects: list[Project] = []
        self.current_project: Project | None = None
        self.current_task: Task | None = None
        self.workflow_worker: WorkflowWorker | None = None
        self.workflow_thread: QThread | None = None
        self.current_baseline: GitBaseline | None = None
        self.git_worker: GitInspectWorker | None = None
        self.git_thread: QThread | None = None
        self.test_worker: TestWorker | None = None
        self.test_thread: QThread | None = None
        self.reject_worker: RejectWorker | None = None
        self.reject_thread: QThread | None = None
        self.dashboard = TaskDashboard()
        self.setCentralWidget(self.dashboard)
        self.setWindowTitle("GoethePlaner")
        self.setStyleSheet(application_stylesheet())
        self.resize(1500, 920)
        self.setMinimumSize(1280, 720)

        self.dashboard.new_project_requested.connect(self._new_project)
        self.dashboard.project_selected.connect(self._select_project)
        self.dashboard.new_task_requested.connect(self._new_task)
        self.dashboard.task_selected.connect(self._select_task)
        self.dashboard.create_requested.connect(self._validate_task_input)
        self.dashboard.cancel_requested.connect(self._cancel_task)
        self.dashboard.refresh_repository_requested.connect(
            self._refresh_repository
        )
        self.dashboard.run_tests_requested.connect(self._run_tests)
        self.dashboard.accept_requested.connect(self._accept_changes)
        self.dashboard.reject_requested.connect(self._confirm_reject)
        if config.test_command:
            self.dashboard.test_command_edit.setText(
                " ".join(config.test_command)
            )

        self.dashboard.set_projects([], None)
        self.dashboard.set_project(None)
        self.statusBar().showMessage("Create or select a project to begin.")

    def _new_project(self) -> None:
        if self.workflow_thread is not None:
            QMessageBox.information(
                self,
                "Workflow running",
                "Wait for the current workflow to finish or cancel it first.",
            )
            return
        dialog = NewProjectDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        project = Project(dialog.project_name, dialog.repository)
        self.projects.append(project)
        self.current_project = project
        self.current_task = None
        self._refresh_project_navigation()
        self.dashboard.set_project(project)
        self.statusBar().showMessage(f"Project {project.name} created.")

    def _select_project(self, project_id: str) -> None:
        project = next(
            (item for item in self.projects if item.id == project_id), None
        )
        if project is None:
            return
        self.current_project = project
        self.current_task = project.tasks[-1] if project.tasks else None
        self._refresh_project_navigation()
        self.dashboard.set_project(project)
        if self.current_task is not None:
            self.dashboard.show_task(self.current_task)
        else:
            self.dashboard.detail_stack.setCurrentWidget(
                self.dashboard.no_task_state
            )
        self.statusBar().showMessage(f"Project {project.name} selected.")

    def _new_task(self) -> None:
        if self.current_project is None:
            QMessageBox.information(
                self,
                "Select a project",
                "Create or select a project before creating a task.",
            )
            return
        if self.workflow_thread is not None:
            QMessageBox.information(
                self,
                "Workflow running",
                "Wait for the current workflow to finish or cancel it first.",
            )
            return
        dialog = NewTaskDialog(self.current_project.name, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.start_task(
            self.current_project.repo_path,
            dialog.prompt,
            dialog.mode,
            title=dialog.task_title,
        )

    def _select_task(self, task_id: str) -> None:
        if self.current_project is None:
            return
        task = next(
            (item for item in self.current_project.tasks if item.id == task_id),
            None,
        )
        if task is None:
            return
        if (
            self.workflow_thread is not None
            and self.current_task is not None
            and task.id != self.current_task.id
        ):
            self.statusBar().showMessage(
                "Finish or cancel the active workflow before switching tasks."
            )
            return
        self.current_task = task
        self.dashboard.show_task(task)
        self.dashboard.set_running(self.workflow_thread is not None)
        self.dashboard.set_tasks(self.current_project.tasks, task.id)
        self.statusBar().showMessage(f"Task {task.title} selected.")

    def _validate_task_input(
        self, repository: str, prompt: str, mode: str
    ) -> None:
        path = Path(repository).expanduser()
        if not repository or not path.is_dir():
            QMessageBox.warning(
                self, "Repository required", "Select a valid repository folder."
            )
            return
        if not prompt:
            QMessageBox.warning(
                self, "Task required", "Enter a programming task."
            )
            return
        self.start_task(path.resolve(), prompt, mode)

    def start_task(
        self,
        repository: Path,
        prompt: str,
        mode: str,
        *,
        title: str | None = None,
    ) -> None:
        name = title or next(
            (line.strip() for line in prompt.splitlines() if line.strip()),
            "Untitled task",
        )
        if len(name) > 64:
            name = f"{name[:61]}..."
        task = Task(repository, prompt, name)
        project = self._ensure_project(repository)
        project.add_task(task)
        self.current_project = project
        self.current_task = task
        self.current_baseline = None
        self._refresh_project_navigation()
        self.dashboard.set_project(project)
        self.dashboard.begin_task(task)
        self.statusBar().showMessage("Workflow running...")

        thread = QThread(self)
        worker = WorkflowWorker(task, self.config, mode)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.task_changed.connect(self._task_state_changed)
        worker.optimized_prompt_ready.connect(
            self.dashboard.set_optimized_prompt
        )
        worker.subtasks_ready.connect(self.dashboard.set_subtasks)
        worker.agent_changed.connect(self.dashboard.add_or_update_agent)
        worker.event_emitted.connect(self.dashboard.logs.append_event)
        worker.baseline_ready.connect(self._store_baseline)
        worker.repository_state_ready.connect(self._show_repository_state)
        worker.completed.connect(self._workflow_completed)
        worker.failed.connect(self._workflow_failed)
        worker.terminal.connect(thread.quit)
        worker.terminal.connect(worker.deleteLater)
        thread.finished.connect(self._workflow_thread_finished)

        self.workflow_thread = thread
        self.workflow_worker = worker
        thread.start()

    def _cancel_task(self) -> None:
        if self.workflow_worker is not None:
            self.workflow_worker.cancel()
            self.dashboard.cancel_button.setEnabled(False)
            self.statusBar().showMessage("Cancelling workflow...")

    def _workflow_completed(self, task: Task) -> None:
        self.current_task = task
        if self.current_project is not None:
            self.current_project.touch()
            self._refresh_project_navigation()
            self.dashboard.set_tasks(self.current_project.tasks, task.id)
        self.dashboard.set_decision_enabled(
            True, self.current_baseline is not None
        )
        if not self.dashboard.test_command_edit.text().strip():
            detected = TestRunner.detect_command(task.repository)
            if detected:
                self.dashboard.test_command_edit.setText(" ".join(detected))
        self.statusBar().showMessage(
            "Workflow complete. Review the generated result."
        )

    def _task_state_changed(self, status: str, progress: int) -> None:
        self.dashboard.set_task_status(status, progress)
        if self.current_project is not None and self.current_task is not None:
            self.current_project.touch()
            self.dashboard.set_tasks(
                self.current_project.tasks, self.current_task.id
            )
            self._refresh_project_navigation()

    def _store_baseline(self, baseline: GitBaseline) -> None:
        self.current_baseline = baseline

    def _show_repository_state(self, state: RepositoryState) -> None:
        files = [item.display for item in state.files]
        self.dashboard.show_repository_state(files, state.diff)
        if state.message:
            self.statusBar().showMessage(state.message)

    def _workflow_failed(self, message: str) -> None:
        self.statusBar().showMessage("Workflow failed.")
        QMessageBox.critical(self, "Workflow failed", message)

    def _workflow_thread_finished(self) -> None:
        self.dashboard.set_running(False)
        self.workflow_worker = None
        thread = self.workflow_thread
        self.workflow_thread = None
        if thread is not None:
            thread.deleteLater()
        if (
            self.current_task is not None
            and self.current_task.status.value == "Cancelled"
        ):
            self.statusBar().showMessage("Workflow cancelled.")
        if self.current_project is not None:
            self.dashboard.set_project(self.current_project)

    def _refresh_repository(self) -> None:
        if self.current_task is None or self.git_thread is not None:
            return
        thread = QThread(self)
        worker = GitInspectWorker(self.current_task.repository)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.state_ready.connect(self._show_repository_state)
        worker.failed.connect(
            lambda message: QMessageBox.warning(
                self, "Git inspection failed", message
            )
        )
        worker.terminal.connect(thread.quit)
        worker.terminal.connect(worker.deleteLater)
        thread.finished.connect(self._git_thread_finished)
        self.git_worker = worker
        self.git_thread = thread
        self.dashboard.refresh_button.setEnabled(False)
        thread.start()

    def _git_thread_finished(self) -> None:
        self.git_worker = None
        thread = self.git_thread
        self.git_thread = None
        if thread is not None:
            thread.deleteLater()
        self.dashboard.refresh_button.setEnabled(True)

    def _run_tests(self, command_text: str) -> None:
        if self.current_task is None or self.test_thread is not None:
            return
        if not command_text:
            QMessageBox.warning(
                self, "Test command required", "Enter a test command."
            )
            return

        self.dashboard.test_output.clear()
        self.dashboard.test_output.appendPlainText(f"$ {command_text}\n")
        thread = QThread(self)
        worker = TestWorker(self.current_task.repository, command_text)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.output.connect(self.dashboard.test_output.appendPlainText)
        worker.completed.connect(self._tests_completed)
        worker.failed.connect(self._tests_failed)
        worker.terminal.connect(thread.quit)
        worker.terminal.connect(worker.deleteLater)
        thread.finished.connect(self._test_thread_finished)
        self.test_worker = worker
        self.test_thread = thread
        self.dashboard.run_tests_button.setEnabled(False)
        thread.start()

    def _tests_completed(self, result: TestRunResult) -> None:
        label = "passed" if result.success else "failed"
        self.dashboard.test_output.appendPlainText(
            f"\nTests {label} with exit code {result.return_code}."
        )

    def _tests_failed(self, message: str) -> None:
        self.dashboard.test_output.appendPlainText(
            f"\nCould not run tests: {message}"
        )

    def _test_thread_finished(self) -> None:
        self.test_worker = None
        thread = self.test_thread
        self.test_thread = None
        if thread is not None:
            thread.deleteLater()
        self.dashboard.run_tests_button.setEnabled(True)

    def _accept_changes(self) -> None:
        if self.current_task is None:
            return
        self.current_task.finish(TaskStatus.ACCEPTED)
        self.dashboard.set_task_status(
            self.current_task.status.value,
            self.current_task.overall_progress,
        )
        self.dashboard.set_decision_enabled(False, False)
        self.dashboard.logs.append_line(
            "GoethePlaner",
            "Changes accepted locally. No commit or push was performed.",
        )
        if self.current_project is not None:
            self.current_project.touch()
            self._refresh_project_navigation()
            self.dashboard.set_tasks(
                self.current_project.tasks, self.current_task.id
            )
        self.statusBar().showMessage("Changes accepted locally.")

    def _confirm_reject(self) -> None:
        if (
            self.current_task is None
            or self.current_baseline is None
            or self.reject_thread is not None
        ):
            return
        answer = QMessageBox.question(
            self,
            "Reject generated changes?",
            "GoethePlaner will restore the Git working tree to the baseline "
            "captured before this task. Pre-existing changes are preserved. "
            "New files created during the task are moved to a temporary archive.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._start_reject()

    def _start_reject(self) -> None:
        if self.current_task is None or self.current_baseline is None:
            return
        thread = QThread(self)
        worker = RejectWorker(self.current_baseline, self.current_task.id)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._reject_completed)
        worker.failed.connect(self._reject_failed)
        worker.terminal.connect(thread.quit)
        worker.terminal.connect(worker.deleteLater)
        thread.finished.connect(self._reject_thread_finished)
        self.reject_worker = worker
        self.reject_thread = thread
        self.dashboard.set_decision_enabled(False, False)
        self.statusBar().showMessage("Restoring the pre-task baseline...")
        thread.start()

    def _reject_completed(self, outcome: RejectOutcome) -> None:
        if self.current_task is not None:
            self.current_task.finish(TaskStatus.REJECTED)
            self.dashboard.set_task_status(
                self.current_task.status.value,
                self.current_task.overall_progress,
            )
            if self.current_project is not None:
                self.current_project.touch()
                self._refresh_project_navigation()
                self.dashboard.set_tasks(
                    self.current_project.tasks, self.current_task.id
                )
        self._show_repository_state(outcome.state)
        message = (
            f"Rejected task changes. Restored "
            f"{len(outcome.result.restored_paths)} path(s)."
        )
        if outcome.result.archive_directory is not None:
            message += (
                " New files were archived at "
                f"{outcome.result.archive_directory}."
            )
        self.dashboard.logs.append_line("Git", message)
        self.statusBar().showMessage("Generated changes rejected.")

    def _reject_failed(self, message: str) -> None:
        self.dashboard.set_decision_enabled(True, True)
        QMessageBox.critical(self, "Reject failed", message)
        self.statusBar().showMessage("Could not reject all changes.")

    def _reject_thread_finished(self) -> None:
        self.reject_worker = None
        thread = self.reject_thread
        self.reject_thread = None
        if thread is not None:
            thread.deleteLater()

    def _ensure_project(self, repository: Path) -> Project:
        resolved = repository.resolve()
        project = next(
            (
                item
                for item in self.projects
                if item.repo_path.resolve() == resolved
            ),
            None,
        )
        if project is None:
            project = Project(resolved.name or "Local Project", resolved)
            self.projects.append(project)
        return project

    def _refresh_project_navigation(self) -> None:
        selected = self.current_project.id if self.current_project else None
        self.dashboard.set_projects(self.projects, selected)

    def closeEvent(self, event) -> None:
        if self.workflow_worker is not None:
            self.workflow_worker.cancel()
        if self.workflow_thread is not None:
            self.workflow_thread.quit()
            self.workflow_thread.wait(3_000)
        if self.test_worker is not None:
            self.test_worker.cancel()
        if self.test_thread is not None:
            self.test_thread.quit()
            self.test_thread.wait(3_000)
        if self.git_thread is not None:
            self.git_thread.quit()
            self.git_thread.wait(3_000)
        if self.reject_thread is not None:
            self.reject_thread.quit()
            if not self.reject_thread.wait(5_000):
                event.ignore()
                return
        super().closeEvent(event)
