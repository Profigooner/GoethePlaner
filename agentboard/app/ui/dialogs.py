from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from agentboard.app.core.agent_selector import (
    AgentSelectionResult,
    AgentSelector,
)
from agentboard.app.core.prompt_optimizer import PromptOptimizer

from .plan_view import AgentSelectionPanel


class NewProjectDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setModal(True)
        self.resize(560, 300)

        title = QLabel("Connect a local project")
        title.setObjectName("taskTitle")
        description = QLabel(
            "Projects group a repository, roadmap, init plan, tasks, agents, "
            "and review output."
        )
        description.setObjectName("secondaryText")
        description.setWordWrap(True)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Project name")
        self.repository_edit = QLineEdit()
        self.repository_edit.setPlaceholderText("Local repository folder")
        self.goal_edit = QTextEdit()
        self.goal_edit.setPlaceholderText(
            "Optional project goal, for example: Build a reliable local "
            "analytics dashboard."
        )
        self.goal_edit.setMaximumHeight(80)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        repository_row = QHBoxLayout()
        repository_row.addWidget(self.repository_edit, 1)
        repository_row.addWidget(browse)

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Name", self.name_edit)
        form.addRow("Repository", repository_row)
        form.addRow("Goal", self.goal_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Create Project"
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName(
            "primaryButton"
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(4)
        layout.addLayout(form)
        layout.addStretch()
        layout.addWidget(buttons)

    @property
    def project_name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def repository(self) -> Path:
        return Path(self.repository_edit.text().strip()).expanduser().resolve()

    @property
    def goal(self) -> str:
        return self.goal_edit.toPlainText().strip()

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select repository",
            self.repository_edit.text() or str(Path.home()),
        )
        if selected:
            path = Path(selected).resolve()
            self.repository_edit.setText(str(path))
            if not self.name_edit.text().strip():
                self.name_edit.setText(path.name)

    def _validate(self) -> None:
        if not self.project_name:
            QMessageBox.warning(self, "Project name required", "Enter a name.")
            return
        if not self.repository_edit.text().strip() or not self.repository.is_dir():
            QMessageBox.warning(
                self,
                "Repository required",
                "Select an existing local repository folder.",
            )
            return
        self.accept()


class NewTaskDialog(QDialog):
    def __init__(
        self,
        project_name: str,
        repository_name: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Plan Task")
        self.setModal(True)
        self.resize(760, 720)
        self.selector = AgentSelector()
        self.selection_result: AgentSelectionResult | None = None
        self._optimized_prompt = ""

        self.stack = QStackedWidget()
        self.input_page = self._build_input_page(project_name)
        self.plan_page = self._build_plan_page()
        self.stack.addWidget(self.input_page)
        self.stack.addWidget(self.plan_page)

        self.cancel_button = QPushButton("Cancel")
        self.back_button = QPushButton("Back")
        self.back_button.setVisible(False)
        self.plan_button = QPushButton("Plan Task")
        self.plan_button.setObjectName("primaryButton")
        self.run_button = QPushButton("Run Selected Agents")
        self.run_button.setObjectName("primaryButton")
        self.run_button.setVisible(False)
        self.cancel_button.clicked.connect(self.reject)
        self.back_button.clicked.connect(self._show_input)
        self.plan_button.clicked.connect(
            lambda: self._plan(repository_name or project_name)
        )
        self.run_button.clicked.connect(self._accept_plan)

        actions = QHBoxLayout()
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        actions.addWidget(self.back_button)
        actions.addWidget(self.plan_button)
        actions.addWidget(self.run_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addWidget(self.stack, 1)
        layout.addLayout(actions)

    def _build_input_page(self, project_name: str) -> QWidget:
        page = QWidget()
        title = QLabel(f"New task for {project_name}")
        title.setObjectName("taskTitle")
        description = QLabel(
            "Describe the outcome, then review the Planner's recommended "
            "specialized agents before execution."
        )
        description.setObjectName("secondaryText")
        description.setWordWrap(True)
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Short task title")
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(
            "Describe the programming task, constraints, and expected result."
        )
        self.prompt_edit.setMinimumHeight(220)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Auto · OpenCode when available", "auto")
        self.mode_combo.addItem("Mock · Parallel simulated workflow", "mock")
        self.mode_combo.addItem("OpenCode · Safe sequential execution", "opencode")
        safety = QLabel(
            "Real OpenCode code-modifying agents run sequentially in the shared "
            "repository. Mock implementation agents may run in parallel."
        )
        safety.setObjectName("mutedText")
        safety.setWordWrap(True)
        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Title", self.title_edit)
        form.addRow("Prompt", self.prompt_edit)
        form.addRow("Execution", self.mode_combo)
        form.addRow("Safety", safety)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(6)
        layout.addLayout(form, 1)
        return page

    def _build_plan_page(self) -> QWidget:
        page = QWidget()
        title = QLabel("Planner recommendation")
        title.setObjectName("taskTitle")
        self.original_preview = QLabel()
        self.original_preview.setObjectName("secondaryText")
        self.original_preview.setWordWrap(True)
        self.plan_reason = QLabel()
        self.plan_reason.setObjectName("secondaryText")
        self.plan_reason.setWordWrap(True)
        self.optimized_preview = QPlainTextEdit()
        self.optimized_preview.setReadOnly(True)
        self.optimized_preview.setMaximumHeight(115)
        self.planner_notes_view = QPlainTextEdit()
        self.planner_notes_view.setReadOnly(True)
        self.planner_notes_view.setMaximumHeight(130)
        self.agent_selection = AgentSelectionPanel()
        self.execution_graph_label = QLabel()
        self.execution_graph_label.setObjectName("secondaryText")
        self.execution_graph_label.setWordWrap(True)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(self.plan_reason)
        layout.addWidget(QLabel("Original prompt"))
        layout.addWidget(self.original_preview)
        layout.addWidget(QLabel("Optimized prompt"))
        layout.addWidget(self.optimized_preview)
        layout.addWidget(QLabel("Planner notes"))
        layout.addWidget(self.planner_notes_view)
        layout.addWidget(self.agent_selection, 1)
        layout.addWidget(QLabel("Execution graph"))
        layout.addWidget(self.execution_graph_label)
        return page

    @property
    def task_title(self) -> str:
        return self.title_edit.text().strip()

    @property
    def prompt(self) -> str:
        return self.prompt_edit.toPlainText().strip()

    @property
    def mode(self) -> str:
        return str(self.mode_combo.currentData())

    @property
    def selected_agents(self) -> list[str]:
        return self.agent_selection.selected_agents()

    @property
    def planner_notes(self) -> str:
        return (
            self.selection_result.planner_notes
            if self.selection_result is not None
            else ""
        )

    @property
    def selection_reasons(self) -> dict[str, str]:
        if self.selection_result is None:
            return {}
        selected = set(self.selected_agents)
        return {
            agent_id: reason
            for agent_id, reason in self.selection_result.reasons.items()
            if agent_id in selected
        }

    @property
    def optimized_prompt(self) -> str:
        return self._optimized_prompt

    @property
    def execution_graph(self) -> list[list[str]]:
        selected = set(self.selected_agents)
        stages = [
            ["prompt_optimizer"] if "prompt_optimizer" in selected else [],
            ["planner"],
            [
                item
                for item in self.selected_agents
                if item
                not in {
                    "prompt_optimizer",
                    "planner",
                    "test_engineer",
                    "code_reviewer",
                    "documentation_writer",
                }
            ],
            ["test_engineer"] if "test_engineer" in selected else [],
            ["code_reviewer"] if "code_reviewer" in selected else [],
            ["documentation_writer"]
            if "documentation_writer" in selected
            else [],
        ]
        return [stage for stage in stages if stage]

    def _plan(self, repository_name: str) -> None:
        if not self.task_title:
            QMessageBox.warning(self, "Title required", "Enter a task title.")
            return
        if not self.prompt:
            QMessageBox.warning(self, "Prompt required", "Enter a task prompt.")
            return
        self._optimized_prompt = PromptOptimizer().optimize(
            self.prompt, repository_name
        )
        self.selection_result = self.selector.select(
            self._optimized_prompt, self.task_title
        )
        self.plan_reason.setText(self.selection_result.reason)
        self.original_preview.setText(self.prompt)
        self.optimized_preview.setPlainText(self._optimized_prompt)
        self.planner_notes_view.setPlainText(
            self.selection_result.planner_notes
        )
        self.agent_selection.set_selection(self.selection_result)
        self.execution_graph_label.setText(
            "  →  ".join(
                " + ".join(
                    self.selector.registry.get(item).display_name
                    for item in stage
                )
                for stage in self.execution_graph
            )
        )
        self.stack.setCurrentWidget(self.plan_page)
        self.back_button.setVisible(True)
        self.plan_button.setVisible(False)
        self.run_button.setVisible(True)

    def _show_input(self) -> None:
        self.stack.setCurrentWidget(self.input_page)
        self.back_button.setVisible(False)
        self.plan_button.setVisible(True)
        self.run_button.setVisible(False)

    def _accept_plan(self) -> None:
        selected = self.selected_agents
        if "planner" not in selected:
            QMessageBox.warning(
                self, "Planner required", "Planner must remain selected."
            )
            return
        if len(selected) < 2:
            QMessageBox.warning(
                self,
                "Select agents",
                "Select at least one agent in addition to Planner.",
            )
            return
        self.accept()

    def _validate(self) -> None:
        self._plan("repository")
