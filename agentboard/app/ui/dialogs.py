from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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
from agentboard.app.core.project_analysis import ProjectAnalyzer
from agentboard.app.core.prompt_optimizer import PromptOptimizer
from agentboard.app.models import ProjectAnalysis

from .plan_view import AgentSelectionPanel


class NewProjectDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setModal(True)
        self.resize(720, 620)
        self._analysis: ProjectAnalysis | None = None
        self._analysis_repository: Path | None = None

        title = QLabel("Create or import a project")
        title.setObjectName("taskTitle")
        description = QLabel(
            "Existing repositories are analyzed without changes. New projects "
            "use guided Roadmap and Init review before coding begins."
        )
        description.setObjectName("secondaryText")
        description.setWordWrap(True)

        self.project_type_combo = QComboBox()
        self.project_type_combo.addItem("Existing Project", "existing")
        self.project_type_combo.addItem("New Project", "new")
        self.project_type_combo.currentIndexChanged.connect(
            self._project_type_changed
        )
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Project name")
        self.repository_edit = QLineEdit()
        self.repository_edit.setPlaceholderText("Existing repository folder")
        self.repository_edit.textChanged.connect(self._repository_changed)
        self.goal_edit = QTextEdit()
        self.goal_edit.setPlaceholderText(
            "Project goal. Required for new projects and recommended for "
            "existing projects."
        )
        self.goal_edit.setMaximumHeight(86)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        self.analyze_button = QPushButton("Analyze Project")
        self.analyze_button.clicked.connect(self._analyze_existing)
        repository_row = QHBoxLayout()
        repository_row.addWidget(self.repository_edit, 1)
        repository_row.addWidget(browse)
        repository_row.addWidget(self.analyze_button)

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Project type", self.project_type_combo)
        form.addRow("Name", self.name_edit)
        self.repository_label = QLabel("Repository")
        form.addRow(self.repository_label, repository_row)
        form.addRow("Goal", self.goal_edit)

        self.analysis_view = QPlainTextEdit()
        self.analysis_view.setReadOnly(True)
        self.analysis_view.setPlaceholderText(
            "Select an existing repository and choose Analyze Project."
        )
        self.analysis_view.setMinimumHeight(150)

        self.import_docs_check = QCheckBox(
            "Import detected documentation into project context"
        )
        self.import_docs_check.setChecked(True)
        self.create_roadmap_check = QCheckBox(
            "Create a Roadmap if one is missing"
        )
        self.run_init_check = QCheckBox(
            "Run Init Agent if agent context is missing"
        )
        self.improve_readme_check = QCheckBox(
            "Review README improvements with Init Agent"
        )
        self.setup_mode_combo = QComboBox()
        self.setup_mode_combo.addItem("Auto · OpenCode when available", "auto")
        self.setup_mode_combo.addItem("Mock · Repository-aware simulation", "mock")
        self.setup_mode_combo.addItem("OpenCode · Require installed CLI", "opencode")

        choices = QVBoxLayout()
        choices.setSpacing(7)
        choices.addWidget(self.import_docs_check)
        choices.addWidget(self.create_roadmap_check)
        choices.addWidget(self.run_init_check)
        choices.addWidget(self.improve_readme_check)
        setup_row = QHBoxLayout()
        setup_row.addWidget(QLabel("Guided setup"))
        setup_row.addWidget(self.setup_mode_combo, 1)
        choices.addLayout(setup_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        self.accept_button = buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )
        self.accept_button.setText("Import Project")
        self.accept_button.setObjectName("primaryButton")
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(4)
        layout.addLayout(form)
        self.analysis_label = QLabel("Project analysis")
        self.analysis_label.setObjectName("sectionLabel")
        layout.addWidget(self.analysis_label)
        layout.addWidget(self.analysis_view)
        layout.addLayout(choices)
        layout.addWidget(buttons)
        self._project_type_changed()

    @property
    def project_type(self) -> str:
        return str(self.project_type_combo.currentData())

    @property
    def project_name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def repository(self) -> Path:
        selected = (
            Path(self.repository_edit.text().strip()).expanduser().resolve()
        )
        if self.project_type == "new":
            return selected / self.project_name
        return selected

    @property
    def goal(self) -> str:
        return self.goal_edit.toPlainText().strip()

    @property
    def analysis(self) -> ProjectAnalysis | None:
        return self._analysis

    @property
    def setup_mode(self) -> str:
        return str(self.setup_mode_combo.currentData())

    @property
    def import_documentation(self) -> bool:
        return self.import_docs_check.isChecked()

    @property
    def create_missing_roadmap(self) -> bool:
        return self.create_roadmap_check.isChecked()

    @property
    def run_missing_init(self) -> bool:
        return self.run_init_check.isChecked()

    @property
    def improve_readme(self) -> bool:
        return self.improve_readme_check.isChecked()

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            (
                "Select existing repository"
                if self.project_type == "existing"
                else "Select target parent folder"
            ),
            self.repository_edit.text() or str(Path.home()),
        )
        if selected:
            path = Path(selected).resolve()
            self.repository_edit.setText(str(path))
            if (
                self.project_type == "existing"
                and not self.name_edit.text().strip()
            ):
                self.name_edit.setText(path.name)

    def _project_type_changed(self) -> None:
        existing = self.project_type == "existing"
        self.repository_label.setText(
            "Repository" if existing else "Target folder"
        )
        self.repository_edit.setPlaceholderText(
            "Existing repository folder"
            if existing
            else "Parent folder for the new project"
        )
        self.analyze_button.setVisible(existing)
        self.analysis_label.setVisible(existing)
        self.analysis_view.setVisible(existing)
        self.import_docs_check.setVisible(existing)
        self.create_roadmap_check.setText(
            "Create a Roadmap if one is missing"
            if existing
            else "Run Roadmap Agent during guided onboarding"
        )
        self.run_init_check.setText(
            "Run Init Agent if agent context is missing"
            if existing
            else "Run Init Agent during guided onboarding"
        )
        self.create_roadmap_check.setChecked(not existing)
        self.run_init_check.setChecked(not existing)
        self.improve_readme_check.setVisible(existing)
        self.accept_button.setText(
            "Import Project" if existing else "Start Guided Setup"
        )
        self._analysis = None
        self._analysis_repository = None

    def _repository_changed(self) -> None:
        self._analysis = None
        self._analysis_repository = None
        if self.project_type == "existing":
            self.analysis_view.clear()

    def _analyze_existing(self) -> None:
        raw_path = self.repository_edit.text().strip()
        if not raw_path:
            QMessageBox.warning(
                self,
                "Repository required",
                "Select an existing local repository folder.",
            )
            return
        repository = Path(raw_path).expanduser().resolve()
        try:
            analysis = ProjectAnalyzer().analyze(repository)
        except ValueError as exc:
            QMessageBox.warning(self, "Analysis failed", str(exc))
            return
        self._analysis = analysis
        self._analysis_repository = repository
        if not self.name_edit.text().strip():
            self.name_edit.setText(repository.name)
        self.create_roadmap_check.setChecked(not analysis.has_roadmap)
        has_agent_file = any(
            name in analysis.documentation_files
            for name in ("AGENTS.md", "AGENT.md", "CLAUDE.md")
        )
        self.run_init_check.setChecked(not has_agent_file)
        self.improve_readme_check.setChecked(False)
        self.analysis_view.setPlainText(
            "\n".join(
                [
                    f"Detected project type: {analysis.detected_project_type}",
                    "Stack: "
                    + (
                        ", ".join(analysis.detected_stack)
                        if analysis.detected_stack
                        else "No language/framework markers detected"
                    ),
                    "Documentation: "
                    + (
                        ", ".join(analysis.documentation_files)
                        if analysis.documentation_files
                        else "None detected"
                    ),
                    "Missing important files: "
                    + (
                        ", ".join(analysis.missing_important_files)
                        if analysis.missing_important_files
                        else "None"
                    ),
                    "Roadmap: "
                    + (analysis.roadmap_path or "missing"),
                    "Init context: "
                    + (
                        ", ".join(analysis.init_paths)
                        if analysis.init_paths
                        else "missing"
                    ),
                    "",
                    "Suggested next actions:",
                    *[
                        f"- {action}"
                        for action in analysis.suggested_actions
                    ],
                ]
            )
        )

    def _validate(self) -> None:
        if not self.project_name:
            QMessageBox.warning(self, "Project name required", "Enter a name.")
            return
        if not self.repository_edit.text().strip():
            QMessageBox.warning(
                self,
                "Repository required",
                "Select a repository or target folder.",
            )
            return
        if self.project_type == "existing":
            repository = Path(
                self.repository_edit.text().strip()
            ).expanduser().resolve()
            if not repository.is_dir():
                QMessageBox.warning(
                    self,
                    "Repository required",
                    "Select an existing local repository folder.",
                )
                return
            if (
                self._analysis is None
                or self._analysis_repository != repository
            ):
                self._analyze_existing()
                if self._analysis is not None:
                    QMessageBox.information(
                        self,
                        "Review project analysis",
                        "Review the detected documentation and setup choices, "
                        "then choose Import Project again.",
                    )
                return
        else:
            parent = Path(
                self.repository_edit.text().strip()
            ).expanduser().resolve()
            if not parent.is_dir():
                QMessageBox.warning(
                    self,
                    "Target folder required",
                    "Select an existing parent folder for the new project.",
                )
                return
            if not self.goal:
                QMessageBox.warning(
                    self,
                    "Project goal required",
                    "Describe the project goal before guided setup.",
                )
                return
            target = self.repository
            if target.exists() and any(target.iterdir()):
                QMessageBox.warning(
                    self,
                    "Target is not empty",
                    "Choose a project name whose target folder does not exist "
                    "or is empty.",
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
