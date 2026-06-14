from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from agentboard.app.core.init_generator import InitGenerator, export_init_draft
from agentboard.app.core.project_generation import ProjectAgentWorker
from agentboard.app.core.roadmap_generator import export_accepted_roadmap
from agentboard.app.models import (
    DraftStatus,
    InitDraft,
    Project,
    ProposedFileStatus,
    RoadmapDraft,
)
from agentboard.app.utils.config import AppConfig

from .diff_viewer import DiffViewer
from .theme import THEME


class _ProjectAgentDialog(QDialog):
    def __init__(self, project: Project, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.project = project
        self.config = config
        self.worker: ProjectAgentWorker | None = None
        self.worker_thread: QThread | None = None
        self._close_when_finished = False
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_label = QLabel("Ready")
        self.progress_label.setObjectName("mutedText")
        self.logs = QPlainTextEdit()
        self.logs.setReadOnly(True)
        self.logs.setPlaceholderText(
            "The exact command, stdout, stderr, and diagnostics appear here."
        )

    def _run_worker(self, **kwargs) -> None:
        if self.worker_thread is not None:
            return
        thread = QThread(self)
        worker = ProjectAgentWorker(
            self.project,
            self.config,
            str(self.mode_combo.currentData()),
            **kwargs,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log.connect(self.logs.appendPlainText)
        worker.progress.connect(self._set_progress)
        worker.completed.connect(self._draft_ready)
        worker.failed.connect(self._agent_failed)
        worker.terminal.connect(thread.quit)
        worker.terminal.connect(worker.deleteLater)
        thread.finished.connect(self._thread_finished)
        self.worker = worker
        self.worker_thread = thread
        self.logs.clear()
        self.progress_bar.setValue(0)
        self._set_running(True)
        thread.start()

    def _set_progress(self, value: int, message: str) -> None:
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def _agent_failed(self, message: str) -> None:
        self.logs.appendPlainText(f"[error] {message}")
        if self._close_when_finished:
            self.progress_label.setText("Agent cancelled")
            return
        QMessageBox.critical(self, "Agent call failed", message)
        self.progress_label.setText("Agent call failed")

    def _thread_finished(self) -> None:
        self.worker = None
        thread = self.worker_thread
        self.worker_thread = None
        if thread is not None:
            thread.deleteLater()
        self._set_running(False)
        if self._close_when_finished:
            self._close_when_finished = False
            self.reject()

    def _cancel_dialog(self) -> None:
        if self.worker is None:
            self.reject()
            return
        self._close_when_finished = True
        self.worker.cancel()
        self.cancel_button.setEnabled(False)
        self.progress_label.setText("Cancelling agent...")

    def _set_running(self, running: bool) -> None:
        raise NotImplementedError

    def _draft_ready(self, draft: object) -> None:
        raise NotImplementedError

    def closeEvent(self, event) -> None:
        if self.worker is not None:
            self.worker.cancel()
        if self.worker_thread is not None:
            self.worker_thread.quit()
            if not self.worker_thread.wait(3_000):
                event.ignore()
                return
        super().closeEvent(event)


class RoadmapDialog(_ProjectAgentDialog):
    def __init__(self, project: Project, config: AppConfig, parent=None) -> None:
        super().__init__(project, config, parent)
        self.setWindowTitle("Create Roadmap")
        self.setModal(True)
        self.resize(1_040, 820)
        self.current_draft: RoadmapDraft | None = project.roadmap_draft

        title = QLabel(f"Roadmap Agent · {project.name}")
        title.setObjectName("taskTitle")
        safety = QLabel(
            "The agent inspects the repository in read-only planning mode. "
            "The roadmap remains a draft until you accept it."
        )
        safety.setObjectName("secondaryText")
        safety.setWordWrap(True)

        self.goal_edit = QTextEdit(project.goal)
        self.goal_edit.setPlaceholderText("Required project goal")
        self.goal_edit.setMaximumHeight(82)
        self.target_users_edit = QLineEdit()
        self.target_users_edit.setPlaceholderText("Who is the product for?")
        self.mvp_scope_edit = QTextEdit()
        self.mvp_scope_edit.setPlaceholderText("Desired MVP scope")
        self.mvp_scope_edit.setMaximumHeight(70)
        self.constraints_edit = QTextEdit()
        self.constraints_edit.setPlaceholderText(
            "Technical constraints, supported platforms, deadlines, or boundaries"
        )
        self.constraints_edit.setMaximumHeight(70)
        self.notes_edit = QLineEdit()
        self.notes_edit.setPlaceholderText("Optional notes")
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Auto · OpenCode when available", "auto")
        self.mode_combo.addItem("Mock · Repository-aware simulation", "mock")
        self.mode_combo.addItem("OpenCode · Require installed CLI", "opencode")

        form = QFormLayout()
        form.addRow("Project goal", self.goal_edit)
        form.addRow("Target users", self.target_users_edit)
        form.addRow("MVP scope", self.mvp_scope_edit)
        form.addRow("Constraints", self.constraints_edit)
        form.addRow("Notes", self.notes_edit)
        form.addRow("Execution", self.mode_combo)

        self.roadmap_preview = QPlainTextEdit()
        self.roadmap_preview.setReadOnly(True)
        self.roadmap_preview.setPlaceholderText(
            "Ask the Roadmap Agent to create a repository-aware draft."
        )
        self.reasoning_view = QPlainTextEdit()
        self.reasoning_view.setReadOnly(True)
        self.observations = QListWidget()
        self.recommendations = QPlainTextEdit()
        self.recommendations.setReadOnly(True)

        tabs = QTabWidget()
        tabs.addTab(self.roadmap_preview, "Roadmap Draft")
        tabs.addTab(self.reasoning_view, "Agent Summary")
        tabs.addTab(self.observations, "Repository Observations")
        tabs.addTab(self.recommendations, "Milestones, Tasks, Risks, Tests")
        tabs.addTab(self.logs, "Logs and Diagnostics")

        self.feedback_edit = QTextEdit()
        self.feedback_edit.setPlaceholderText(
            "Describe changes the agent should make to the current draft."
        )
        self.feedback_edit.setMaximumHeight(80)

        self.ask_button = QPushButton("Ask Agent")
        self.ask_button.setObjectName("primaryButton")
        self.accept_button = QPushButton("Accept Roadmap")
        self.request_changes_button = QPushButton("Request Changes")
        self.regenerate_button = QPushButton("Regenerate")
        self.export_button = QPushButton("Export")
        self.cancel_button = QPushButton("Cancel")
        self.ask_button.clicked.connect(self._generate)
        self.accept_button.clicked.connect(self._accept_draft)
        self.request_changes_button.clicked.connect(self._revise)
        self.regenerate_button.clicked.connect(self._generate)
        self.export_button.clicked.connect(self._export)
        self.cancel_button.clicked.connect(self._cancel_dialog)

        actions = QHBoxLayout()
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        actions.addWidget(self.regenerate_button)
        actions.addWidget(self.request_changes_button)
        actions.addWidget(self.export_button)
        actions.addWidget(self.accept_button)
        actions.addWidget(self.ask_button)

        progress = QHBoxLayout()
        progress.addWidget(self.progress_label)
        progress.addWidget(self.progress_bar, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(safety)
        layout.addLayout(form)
        layout.addLayout(progress)
        layout.addWidget(tabs, 1)
        layout.addWidget(QLabel("Revision feedback"))
        layout.addWidget(self.feedback_edit)
        layout.addLayout(actions)
        self._render_draft()
        self._set_running(False)

    @property
    def goal(self) -> str:
        return self.goal_edit.toPlainText().strip()

    def _generate(self) -> None:
        if not self.goal:
            QMessageBox.warning(
                self, "Project goal required", "Enter a project goal."
            )
            return
        self._run_worker(
            kind="roadmap",
            goal=self.goal,
            constraints=self.constraints_edit.toPlainText().strip(),
            target_users=self.target_users_edit.text().strip(),
            mvp_scope=self.mvp_scope_edit.toPlainText().strip(),
            notes=self.notes_edit.text().strip(),
        )

    def _revise(self) -> None:
        feedback = self.feedback_edit.toPlainText().strip()
        if self.current_draft is None:
            QMessageBox.information(
                self, "No draft", "Ask the agent for a draft first."
            )
            return
        if not feedback:
            QMessageBox.warning(
                self, "Feedback required", "Describe the requested changes."
            )
            return
        self._run_worker(
            kind="roadmap",
            goal=self.goal,
            previous_draft=self.current_draft,
            feedback=feedback,
            constraints=self.constraints_edit.toPlainText().strip(),
            target_users=self.target_users_edit.text().strip(),
            mvp_scope=self.mvp_scope_edit.toPlainText().strip(),
            notes=self.notes_edit.text().strip(),
        )

    def _draft_ready(self, draft: object) -> None:
        if not isinstance(draft, RoadmapDraft):
            self._agent_failed("Roadmap Agent returned an unexpected result.")
            return
        self.current_draft = draft
        self.project.set_roadmap_draft(draft)
        self.feedback_edit.clear()
        self._render_draft()
        self.progress_label.setText("Draft ready for review")

    def _render_draft(self) -> None:
        draft = self.current_draft
        if draft is None:
            self.roadmap_preview.clear()
            self.reasoning_view.clear()
            self.observations.clear()
            self.recommendations.clear()
            return
        self.goal_edit.setPlainText(draft.user_goal)
        self.roadmap_preview.setPlainText(draft.draft_content)
        self.reasoning_view.setPlainText(
            draft.reasoning_summary
            + (
                "\n\nFeedback history:\n- "
                + "\n- ".join(draft.feedback_history)
                if draft.feedback_history
                else ""
            )
        )
        self.observations.clear()
        self.observations.addItems(draft.repository_observations)
        self.recommendations.setPlainText(
            _section("Suggested Milestones", draft.suggested_milestones)
            + _section("Suggested Next Tasks", draft.suggested_next_tasks)
            + _section("Risks", draft.risks)
            + _section("Testing Strategy", draft.testing_strategy)
        )
        accepted = draft.status == DraftStatus.ACCEPTED
        self.export_button.setEnabled(accepted)

    def _accept_draft(self) -> None:
        if self.current_draft is None:
            return
        self.project.goal = self.goal
        self.project.accept_roadmap_draft(self.current_draft)
        self._render_draft()
        self.progress_label.setText(
            "Roadmap accepted. It can now be exported."
        )
        self._set_running(False)

    def _export(self) -> None:
        if (
            self.current_draft is None
            or self.current_draft.status != DraftStatus.ACCEPTED
        ):
            QMessageBox.information(
                self,
                "Accept roadmap first",
                "Accept the reviewed roadmap before exporting it.",
            )
            return
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Export Roadmap",
            str(self.project.repo_path / "ROADMAP.generated.md"),
            "Markdown (*.md);;All files (*)",
        )
        if not selected:
            return
        target = Path(selected)
        overwrite = _confirm_replace(self, target)
        if overwrite is None:
            return
        try:
            export_accepted_roadmap(
                self.current_draft, target, overwrite=overwrite
            )
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.progress_label.setText(f"Exported {target.name}")

    def _set_running(self, running: bool) -> None:
        has_draft = self.current_draft is not None
        accepted = (
            has_draft
            and self.current_draft.status == DraftStatus.ACCEPTED
        )
        self.ask_button.setText(
            "Create Revision" if accepted else "Ask Agent"
        )
        self.ask_button.setEnabled(not running)
        self.regenerate_button.setEnabled(not running and has_draft)
        self.request_changes_button.setEnabled(
            not running and has_draft
        )
        self.accept_button.setEnabled(not running and has_draft and not accepted)
        self.export_button.setEnabled(not running and bool(accepted))
        self.mode_combo.setEnabled(not running)
        self.cancel_button.setText("Cancel Agent" if running else "Cancel")
        if running:
            self.progress_label.setText("Agent is inspecting the repository")


class InitDialog(_ProjectAgentDialog):
    def __init__(self, project: Project, config: AppConfig, parent=None) -> None:
        super().__init__(project, config, parent)
        self.setWindowTitle("Run Init Agent")
        self.setModal(True)
        self.resize(1_080, 820)
        self.current_draft: InitDraft | None = project.init_draft

        title = QLabel(f"Init Agent · {project.name}")
        title.setObjectName("taskTitle")
        safety = QLabel(
            "Draft generation is read-only. No file is created or overwritten "
            "until you select proposals and confirm Apply Selected Files."
        )
        safety.setObjectName("secondaryText")
        safety.setWordWrap(True)
        self.goal_edit = QTextEdit(project.goal)
        self.goal_edit.setPlaceholderText(
            "Required init goal, setup expectations, and project conventions"
        )
        self.goal_edit.setMaximumHeight(90)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Auto · OpenCode when available", "auto")
        self.mode_combo.addItem("Mock · Repository-aware simulation", "mock")
        self.mode_combo.addItem("OpenCode · Require installed CLI", "opencode")
        form = QFormLayout()
        form.addRow("Init goal", self.goal_edit)
        form.addRow("Execution", self.mode_combo)

        self.file_tree = QTreeWidget()
        self.file_tree.setHeaderLabels(["Apply", "Proposed file", "Status"])
        self.file_tree.setRootIsDecorated(False)
        self.file_tree.setColumnWidth(0, 58)
        self.file_tree.setColumnWidth(1, 185)
        self.file_tree.setStyleSheet(
            "QTreeWidget {"
            f"background-color: {THEME.background_elevated};"
            f"color: {THEME.text_secondary};"
            f"border: 1px solid {THEME.border};"
            "border-radius: 8px;"
            "}"
            "QTreeWidget::item { padding: 5px; }"
            "QTreeWidget::item:selected {"
            f"background-color: {THEME.accent}; color: white;"
            "}"
            "QHeaderView::section {"
            f"background-color: {THEME.panel_alt};"
            f"color: {THEME.text_secondary};"
            f"border: 1px solid {THEME.border};"
            "padding: 6px;"
            "}"
        )
        self.file_tree.currentItemChanged.connect(self._show_selected_file)
        self.content_preview = QPlainTextEdit()
        self.content_preview.setReadOnly(True)
        self.diff_preview = DiffViewer()
        preview_tabs = QTabWidget()
        preview_tabs.addTab(self.content_preview, "Proposed Content")
        preview_tabs.addTab(self.diff_preview, "Diff Preview")
        file_splitter = QSplitter(Qt.Orientation.Horizontal)
        file_splitter.addWidget(self.file_tree)
        file_splitter.addWidget(preview_tabs)
        file_splitter.setSizes([330, 680])

        self.reasoning_view = QPlainTextEdit()
        self.reasoning_view.setReadOnly(True)
        self.reasoning_view.setMaximumHeight(100)
        detail_tabs = QTabWidget()
        proposal_page = QWidget()
        proposal_layout = QVBoxLayout(proposal_page)
        proposal_layout.setContentsMargins(0, 0, 0, 0)
        proposal_layout.addWidget(file_splitter)
        detail_tabs.addTab(proposal_page, "Proposed Files")
        detail_tabs.addTab(self.reasoning_view, "Agent Summary")
        detail_tabs.addTab(self.logs, "Logs and Diagnostics")

        self.feedback_edit = QTextEdit()
        self.feedback_edit.setPlaceholderText(
            "Describe changes to the proposed files."
        )
        self.feedback_edit.setMaximumHeight(75)
        self.run_button = QPushButton("Run Init Agent")
        self.run_button.setObjectName("primaryButton")
        self.apply_button = QPushButton("Apply Selected Files")
        self.request_changes_button = QPushButton("Request Changes")
        self.regenerate_button = QPushButton("Regenerate")
        self.export_button = QPushButton("Export Draft")
        self.cancel_button = QPushButton("Cancel")
        self.run_button.clicked.connect(self._generate)
        self.apply_button.clicked.connect(self._apply_selected)
        self.request_changes_button.clicked.connect(self._revise)
        self.regenerate_button.clicked.connect(self._generate)
        self.export_button.clicked.connect(self._export)
        self.cancel_button.clicked.connect(self._cancel_dialog)
        actions = QHBoxLayout()
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        actions.addWidget(self.regenerate_button)
        actions.addWidget(self.request_changes_button)
        actions.addWidget(self.export_button)
        actions.addWidget(self.apply_button)
        actions.addWidget(self.run_button)
        progress = QHBoxLayout()
        progress.addWidget(self.progress_label)
        progress.addWidget(self.progress_bar, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(safety)
        layout.addLayout(form)
        layout.addLayout(progress)
        layout.addWidget(detail_tabs, 1)
        layout.addWidget(QLabel("Revision feedback"))
        layout.addWidget(self.feedback_edit)
        layout.addLayout(actions)
        self._render_draft()
        self._set_running(False)

    @property
    def goal(self) -> str:
        return self.goal_edit.toPlainText().strip()

    def _generate(self) -> None:
        if not self.goal:
            QMessageBox.warning(
                self, "Init goal required", "Enter an init goal."
            )
            return
        self._run_worker(kind="init", goal=self.goal)

    def _revise(self) -> None:
        feedback = self.feedback_edit.toPlainText().strip()
        if self.current_draft is None:
            QMessageBox.information(
                self, "No draft", "Run the Init Agent first."
            )
            return
        if not feedback:
            QMessageBox.warning(
                self, "Feedback required", "Describe the requested changes."
            )
            return
        self._sync_selection()
        self._run_worker(
            kind="init",
            goal=self.goal,
            previous_draft=self.current_draft,
            feedback=feedback,
        )

    def _draft_ready(self, draft: object) -> None:
        if not isinstance(draft, InitDraft):
            self._agent_failed("Init Agent returned an unexpected result.")
            return
        self.current_draft = draft
        self.project.set_init_draft(draft)
        self.feedback_edit.clear()
        self._render_draft()
        self.progress_label.setText("File proposals ready for review")

    def _render_draft(self) -> None:
        self.file_tree.clear()
        draft = self.current_draft
        if draft is None:
            self.content_preview.clear()
            self.diff_preview.clear()
            self.reasoning_view.clear()
            return
        self.goal_edit.setPlainText(draft.user_goal)
        for index, proposal in enumerate(draft.proposed_files):
            item = QTreeWidgetItem(
                ["", proposal.path, proposal.status.value]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, index)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                0,
                Qt.CheckState.Checked
                if proposal.selected
                else Qt.CheckState.Unchecked,
            )
            if proposal.status == ProposedFileStatus.CONFLICT:
                item.setDisabled(True)
            self.file_tree.addTopLevelItem(item)
        if self.file_tree.topLevelItemCount():
            self.file_tree.setCurrentItem(self.file_tree.topLevelItem(0))
        self.reasoning_view.setPlainText(
            draft.reasoning_summary
            + _section(
                "Repository Observations", draft.repository_observations
            )
            + _section("Setup Notes", draft.setup_notes)
            + (
                "\nFeedback history:\n- "
                + "\n- ".join(draft.feedback_history)
                if draft.feedback_history
                else ""
            )
        )

    def _show_selected_file(
        self, current: QTreeWidgetItem | None, _previous
    ) -> None:
        if current is None or self.current_draft is None:
            self.content_preview.clear()
            self.diff_preview.clear()
            return
        index = current.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(index, int):
            return
        proposal = self.current_draft.proposed_files[index]
        self.content_preview.setPlainText(proposal.content)
        self.diff_preview.set_diff(proposal.diff_preview)

    def _sync_selection(self) -> None:
        if self.current_draft is None:
            return
        for index in range(self.file_tree.topLevelItemCount()):
            item = self.file_tree.topLevelItem(index)
            proposal_index = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(proposal_index, int):
                self.current_draft.proposed_files[
                    proposal_index
                ].selected = (
                    item.checkState(0) == Qt.CheckState.Checked
                )

    def _apply_selected(self) -> None:
        if self.current_draft is None:
            return
        self._sync_selection()
        selected = [
            item
            for item in self.current_draft.proposed_files
            if item.selected and item.status != ProposedFileStatus.CONFLICT
        ]
        if not selected:
            QMessageBox.information(
                self, "Select files", "Select at least one safe proposal."
            )
            return
        updates = {
            item.path
            for item in selected
            if item.status == ProposedFileStatus.UPDATE
        }
        detail = "\n".join(
            f"- {item.path} ({item.status.value})" for item in selected
        )
        warning = (
            "\n\nThe following existing files will be overwritten after this "
            "confirmation:\n" + "\n".join(f"- {path}" for path in sorted(updates))
            if updates
            else ""
        )
        answer = QMessageBox.question(
            self,
            "Apply selected Init files?",
            "Write only these selected proposals?\n\n"
            + detail
            + warning,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            written = InitGenerator().apply_selected(
                self.project,
                self.current_draft,
                confirmed=True,
                overwrite_paths=updates,
            )
        except (OSError, ValueError, PermissionError) as exc:
            QMessageBox.critical(self, "Init apply failed", str(exc))
            return
        self.project.goal = self.goal
        self.project.accept_init_draft(self.current_draft)
        self.progress_label.setText(
            f"Applied {len(written)} selected file(s)."
        )
        self._set_running(False)

    def _export(self) -> None:
        if self.current_draft is None:
            return
        self._sync_selection()
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Export Init Draft",
            str(self.project.repo_path / "INIT.generated.md"),
            "Markdown (*.md);;All files (*)",
        )
        if not selected:
            return
        target = Path(selected)
        overwrite = _confirm_replace(self, target)
        if overwrite is None:
            return
        try:
            export_init_draft(
                self.current_draft, target, overwrite=overwrite
            )
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return
        self.progress_label.setText(f"Exported {target.name}")

    def _set_running(self, running: bool) -> None:
        has_draft = self.current_draft is not None
        accepted = (
            has_draft and self.current_draft.status == DraftStatus.ACCEPTED
        )
        self.run_button.setText(
            "Refresh Init Draft" if accepted else "Run Init Agent"
        )
        self.run_button.setEnabled(not running)
        self.regenerate_button.setEnabled(not running and has_draft)
        self.request_changes_button.setEnabled(
            not running and has_draft
        )
        self.apply_button.setEnabled(not running and has_draft and not accepted)
        self.export_button.setEnabled(not running and has_draft)
        self.mode_combo.setEnabled(not running)
        self.cancel_button.setText("Cancel Agent" if running else "Cancel")
        if running:
            self.progress_label.setText("Agent is inspecting the repository")


def _section(title: str, items: list[str]) -> str:
    if not items:
        return ""
    return f"\n\n{title}\n" + "\n".join(f"- {item}" for item in items)


def _confirm_replace(parent: QWidget, target: Path) -> bool | None:
    if not target.exists():
        return False
    answer = QMessageBox.question(
        parent,
        "Replace existing file?",
        f"{target.name} already exists. Replace it?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return None
    return True
