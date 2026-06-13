from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from agentboard.app.models import AgentState, Subtask, Task

from .agent_card import AgentCard
from .diff_viewer import DiffViewer
from .log_viewer import LogViewer


class TaskDashboard(QWidget):
    create_requested = Signal(str, str, str)
    cancel_requested = Signal()
    run_tests_requested = Signal(str)
    refresh_repository_requested = Signal()
    accept_requested = Signal()
    reject_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.agent_cards: dict[str, AgentCard] = {}

        self.repository_edit = QLineEdit()
        self.repository_edit.setReadOnly(True)
        self.repository_edit.setPlaceholderText("Select a local Git repository")
        self.browse_button = QPushButton("Browse...")

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Auto (OpenCode when available)", "auto")
        self.mode_combo.addItem("Mock", "mock")
        self.mode_combo.addItem("OpenCode", "opencode")

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(
            "Describe the programming task. AgentBoard will clarify and split it."
        )
        self.prompt_edit.setMinimumHeight(120)
        self.create_button = QPushButton("Create Task")
        self.create_button.setDefault(True)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)

        self.task_list = QListWidget()
        self.task_list.setMinimumWidth(210)
        self.task_list.setAlternatingRowColors(True)

        self.task_name_label = QLabel("No task selected")
        self.task_name_label.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.task_status_label = QLabel("Ready")
        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)

        self.agent_container = QWidget()
        self.agent_layout = QVBoxLayout(self.agent_container)
        self.agent_layout.setContentsMargins(0, 0, 0, 0)
        self.agent_layout.addStretch()
        agent_scroll = QScrollArea()
        agent_scroll.setWidgetResizable(True)
        agent_scroll.setWidget(self.agent_container)

        self.optimized_prompt = QPlainTextEdit()
        self.optimized_prompt.setReadOnly(True)
        self.optimized_prompt.setPlaceholderText(
            "The clarified prompt will appear here."
        )
        self.subtask_list = QListWidget()
        self.logs = LogViewer()
        self.changed_files = QListWidget()
        self.diff_viewer = DiffViewer()

        self.test_command_edit = QLineEdit()
        self.test_command_edit.setPlaceholderText(
            "Test command, for example: python -m pytest"
        )
        self.run_tests_button = QPushButton("Run Tests")
        self.run_tests_button.setEnabled(False)
        self.test_output = QPlainTextEdit()
        self.test_output.setReadOnly(True)
        self.test_output.setPlaceholderText("Test output will appear here.")

        self.refresh_button = QPushButton("Refresh Changes")
        self.refresh_button.setEnabled(False)
        self.accept_button = QPushButton("Accept Changes")
        self.accept_button.setEnabled(False)
        self.reject_button = QPushButton("Reject Changes")
        self.reject_button.setEnabled(False)

        self._build_layout(agent_scroll)
        self._connect_controls()

    def _build_layout(self, agent_scroll: QScrollArea) -> None:
        repo_row = QHBoxLayout()
        repo_row.addWidget(self.repository_edit)
        repo_row.addWidget(self.browse_button)

        form = QFormLayout()
        form.addRow("Repository", repo_row)
        form.addRow("Execution mode", self.mode_combo)
        form.addRow("Task", self.prompt_edit)

        task_buttons = QHBoxLayout()
        task_buttons.addStretch()
        task_buttons.addWidget(self.cancel_button)
        task_buttons.addWidget(self.create_button)

        input_panel = QFrame()
        input_panel.setFrameShape(QFrame.Shape.StyledPanel)
        input_layout = QVBoxLayout(input_panel)
        input_layout.addLayout(form)
        input_layout.addLayout(task_buttons)

        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        overview_layout.addWidget(self.task_name_label)
        overview_layout.addWidget(self.task_status_label)
        overview_layout.addWidget(self.overall_progress)
        overview_layout.addWidget(QLabel("Agents"))
        overview_layout.addWidget(agent_scroll, 1)

        changes = QWidget()
        changes_layout = QVBoxLayout(changes)
        changes_layout.setContentsMargins(0, 0, 0, 0)
        changes_layout.addWidget(self.refresh_button)
        changes_layout.addWidget(self.changed_files)

        tests = QWidget()
        tests_layout = QVBoxLayout(tests)
        tests_layout.setContentsMargins(0, 0, 0, 0)
        test_row = QHBoxLayout()
        test_row.addWidget(self.test_command_edit)
        test_row.addWidget(self.run_tests_button)
        tests_layout.addLayout(test_row)
        tests_layout.addWidget(self.test_output)

        tabs = QTabWidget()
        tabs.addTab(self.optimized_prompt, "Optimized Prompt")
        tabs.addTab(self.subtask_list, "Subtasks")
        tabs.addTab(self.logs, "Logs")
        tabs.addTab(changes, "Changed Files")
        tabs.addTab(self.diff_viewer, "Diff")
        tabs.addTab(tests, "Tests")

        main_splitter = QSplitter()
        main_splitter.addWidget(self.task_list)
        main_splitter.addWidget(overview)
        main_splitter.addWidget(tabs)
        main_splitter.setStretchFactor(0, 0)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setStretchFactor(2, 2)
        main_splitter.setSizes([220, 360, 620])

        decision_row = QHBoxLayout()
        decision_row.addStretch()
        decision_row.addWidget(self.reject_button)
        decision_row.addWidget(self.accept_button)

        layout = QVBoxLayout(self)
        layout.addWidget(input_panel)
        layout.addWidget(main_splitter, 1)
        layout.addLayout(decision_row)

    def _connect_controls(self) -> None:
        self.create_button.clicked.connect(self._emit_create)
        self.cancel_button.clicked.connect(self.cancel_requested)
        self.run_tests_button.clicked.connect(
            lambda: self.run_tests_requested.emit(
                self.test_command_edit.text().strip()
            )
        )
        self.refresh_button.clicked.connect(self.refresh_repository_requested)
        self.accept_button.clicked.connect(self.accept_requested)
        self.reject_button.clicked.connect(self.reject_requested)

    def _emit_create(self) -> None:
        self.create_requested.emit(
            self.repository_edit.text().strip(),
            self.prompt_edit.toPlainText().strip(),
            str(self.mode_combo.currentData()),
        )

    def set_repository(self, path: Path) -> None:
        self.repository_edit.setText(str(path))

    def begin_task(self, task: Task) -> None:
        self.task_list.addItem(task.name)
        self.task_list.setCurrentRow(self.task_list.count() - 1)
        self.task_name_label.setText(task.name)
        self.task_status_label.setText(task.status.value)
        self.overall_progress.setValue(task.overall_progress)
        self.optimized_prompt.clear()
        self.subtask_list.clear()
        self.logs.clear()
        self.changed_files.clear()
        self.diff_viewer.clear()
        self.test_output.clear()
        self.clear_agents()
        self.set_running(True)

    def set_running(self, running: bool) -> None:
        self.create_button.setEnabled(not running)
        self.browse_button.setEnabled(not running)
        self.prompt_edit.setEnabled(not running)
        self.mode_combo.setEnabled(not running)
        self.cancel_button.setEnabled(running)

    def set_task_status(self, status: str, progress: int) -> None:
        self.task_status_label.setText(status)
        self.overall_progress.setValue(progress)

    def set_optimized_prompt(self, prompt: str) -> None:
        self.optimized_prompt.setPlainText(prompt)

    def set_subtasks(self, subtasks: list[Subtask]) -> None:
        self.subtask_list.clear()
        for subtask in subtasks:
            self.subtask_list.addItem(
                f"{subtask.agent_role.value}: {subtask.title}\n"
                f"{subtask.description}"
            )

    def clear_agents(self) -> None:
        for card in self.agent_cards.values():
            card.deleteLater()
        self.agent_cards.clear()

    def add_or_update_agent(self, agent: AgentState) -> None:
        card = self.agent_cards.get(agent.id)
        if card is None:
            card = AgentCard(agent)
            self.agent_cards[agent.id] = card
            self.agent_layout.insertWidget(
                max(0, self.agent_layout.count() - 1), card
            )
        else:
            card.update_agent(agent)

    def show_repository_state(
        self, files: list[str], diff_text: str
    ) -> None:
        self.changed_files.clear()
        self.changed_files.addItems(files)
        self.diff_viewer.set_diff(diff_text or "No working-tree changes.")

    def set_decision_enabled(
        self, accept_enabled: bool, reject_enabled: bool
    ) -> None:
        self.accept_button.setEnabled(accept_enabled)
        self.reject_button.setEnabled(reject_enabled)
        enabled = accept_enabled or reject_enabled
        self.refresh_button.setEnabled(enabled)
        self.run_tests_button.setEnabled(enabled)
