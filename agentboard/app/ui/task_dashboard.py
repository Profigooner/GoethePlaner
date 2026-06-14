from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from agentboard.app.core.agent_registry import DEFAULT_AGENT_REGISTRY
from agentboard.app.models import (
    AgentState,
    Project,
    Subtask,
    Task,
    WorkflowEvent,
)

from .components import EmptyState, GlassPanel, StatusBadge
from .sidebar import ProjectSidebar
from .tool_windows import BottomToolBar, BottomToolWindow
from .workspace_views import (
    InitView,
    ProjectOverviewView,
    RoadmapView,
    TaskDetailView,
)


class TaskDashboard(QWidget):
    create_requested = Signal(str, str, str)
    cancel_requested = Signal()
    run_tests_requested = Signal(str)
    refresh_repository_requested = Signal()
    accept_requested = Signal()
    reject_requested = Signal()
    new_project_requested = Signal()
    project_selected = Signal(str)
    navigation_selected = Signal(str, str, str)
    new_task_requested = Signal()
    new_task_for_project = Signal(str)
    task_selected = Signal(str)
    generate_roadmap_requested = Signal()
    generate_init_requested = Signal()
    open_roadmap_requested = Signal()
    settings_requested = Signal()
    export_roadmap_requested = Signal()
    export_init_requested = Signal()
    apply_init_requested = Signal(object)
    roadmap_content_saved = Signal(str)
    roadmap_requirement_requested = Signal()
    roadmap_import_requested = Signal()
    init_import_requested = Signal()
    roadmap_task_requested = Signal(str)
    suggestion_accept_requested = Signal(str)
    suggestion_reject_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("appRoot")
        self.current_project: Project | None = None
        self.current_task: Task | None = None
        self.task_cards: dict[str, Task] = {}
        self._create_compatibility_controls()

        self.sidebar = ProjectSidebar()
        self.sidebar.new_project_requested.connect(self.new_project_requested)
        self.sidebar.project_selected.connect(self.project_selected)
        self.sidebar.task_selected.connect(self.task_selected)
        self.sidebar.navigation_selected.connect(self.navigation_selected)
        self.sidebar.new_task_requested.connect(self.new_task_for_project)
        self.sidebar.settings_requested.connect(self.settings_requested)
        self.sidebar.setFixedWidth(280)

        self.project_name_label = QLabel("Select a project")
        self.project_name_label.setObjectName("projectTitle")
        self.project_path_label = QLabel(
            "Create or import a project to begin."
        )
        self.project_path_label.setObjectName("secondaryText")
        self.project_status = StatusBadge("Idle")
        self.roadmap_header_status = StatusBadge("missing")
        self.init_header_status = StatusBadge("missing")
        self.new_task_button = QPushButton("+ New Task")
        self.new_task_button.setObjectName("primaryButton")
        self.new_task_button.setEnabled(False)
        self.new_task_button.clicked.connect(self.new_task_requested)
        self.generate_roadmap_button = QPushButton("Create Roadmap")
        self.generate_roadmap_button.setEnabled(False)
        self.generate_roadmap_button.clicked.connect(
            self.open_roadmap_requested
        )
        self.generate_init_button = QPushButton("Run Init Agent")
        self.generate_init_button.setEnabled(False)
        self.generate_init_button.clicked.connect(
            lambda: self.show_project_overview("init")
        )
        self.open_roadmap_button = self.generate_roadmap_button
        self.settings_button = QPushButton("Settings")
        self.settings_button.hide()
        self.settings_button.clicked.connect(self.settings_requested)

        header = GlassPanel("headerPanel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 11, 14, 11)
        identity = QVBoxLayout()
        identity.setSpacing(2)
        title_row = QHBoxLayout()
        title_row.addWidget(self.project_name_label)
        title_row.addWidget(self.project_status)
        title_row.addStretch()
        identity.addLayout(title_row)
        identity.addWidget(self.project_path_label)
        header_layout.addLayout(identity, 1)
        header_layout.addWidget(QLabel("Roadmap"))
        header_layout.addWidget(self.roadmap_header_status)
        header_layout.addWidget(QLabel("Init"))
        header_layout.addWidget(self.init_header_status)
        header_layout.addWidget(self.generate_roadmap_button)
        header_layout.addWidget(self.generate_init_button)
        header_layout.addWidget(self.new_task_button)

        self.workspace_stack = QStackedWidget()
        self.project_overview = ProjectOverviewView()
        self.roadmap_workspace = RoadmapView()
        self.init_workspace = InitView()
        self.task_detail = TaskDetailView()
        self.no_selection = EmptyState(
            "No project selected",
            "Create or import a project from the left navigation.",
            "New Project",
        )
        self.no_selection.action_requested.connect(self.new_project_requested)
        for page in (
            self.project_overview,
            self.roadmap_workspace,
            self.init_workspace,
            self.task_detail,
            self.no_selection,
        ):
            self.workspace_stack.addWidget(page)
        self.workspace_stack.setCurrentWidget(self.no_selection)

        self.project_overview.roadmap_requested.connect(
            lambda: self.show_project_overview("roadmap")
        )
        self.project_overview.init_requested.connect(
            lambda: self.show_project_overview("init")
        )
        self.project_overview.new_task_requested.connect(
            self.new_task_requested
        )
        self.roadmap_workspace.ask_agent_requested.connect(
            self.generate_roadmap_requested
        )
        self.roadmap_workspace.content_saved.connect(
            self.roadmap_content_saved
        )
        self.roadmap_workspace.add_requirement_requested.connect(
            self.roadmap_requirement_requested
        )
        self.roadmap_workspace.import_requested.connect(
            self.roadmap_import_requested
        )
        self.roadmap_workspace.export_requested.connect(
            self.export_roadmap_requested
        )
        self.roadmap_workspace.create_task_requested.connect(
            self.roadmap_task_requested
        )
        self.roadmap_workspace.suggestion_accept_requested.connect(
            self.suggestion_accept_requested
        )
        self.roadmap_workspace.suggestion_reject_requested.connect(
            self.suggestion_reject_requested
        )
        self.init_workspace.run_agent_requested.connect(
            self.generate_init_requested
        )
        self.init_workspace.import_requested.connect(
            self.init_import_requested
        )
        self.init_workspace.suggestion_accept_requested.connect(
            self.suggestion_accept_requested
        )
        self.init_workspace.suggestion_reject_requested.connect(
            self.suggestion_reject_requested
        )
        self.task_detail.cancel_requested.connect(self.cancel_requested)
        self.task_detail.accept_requested.connect(self.accept_requested)
        self.task_detail.reject_requested.connect(self.reject_requested)

        self.bottom_tool_window = BottomToolWindow()
        self.bottom_tool_bar = BottomToolBar()
        self.bottom_tool_bar.tool_toggled.connect(self.toggle_bottom_tool)
        self.bottom_tool_window.close_requested.connect(
            self.hide_bottom_tool
        )
        self.bottom_tool_window.tests_view.run_requested.connect(
            self.run_tests_requested
        )
        self.bottom_tool_window.output_view.refresh_requested.connect(
            self.refresh_repository_requested
        )

        self.vertical_splitter = QSplitter(Qt.Orientation.Vertical)
        self.vertical_splitter.setChildrenCollapsible(False)
        self.vertical_splitter.addWidget(self.workspace_stack)
        self.vertical_splitter.addWidget(self.bottom_tool_window)
        self.vertical_splitter.setStretchFactor(0, 1)
        self.vertical_splitter.setStretchFactor(1, 0)
        self.vertical_splitter.setSizes([700, 0])

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        right_layout.addWidget(header)
        right_layout.addWidget(self.vertical_splitter, 1)
        right_layout.addWidget(self.bottom_tool_bar)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(10)
        layout.addWidget(self.sidebar)
        layout.addWidget(right, 1)

        self.logs = self.bottom_tool_window.logs
        self.optimized_prompt = (
            self.bottom_tool_window.prompt_view.optimized_prompt
        )
        self.task_planner_notes = (
            self.bottom_tool_window.prompt_view.planner_notes
        )
        self.selected_agent_list = (
            self.bottom_tool_window.prompt_view.selected_agents
        )
        self.execution_graph_view = (
            self.bottom_tool_window.prompt_view.execution_graph
        )
        self.subtask_list = self.bottom_tool_window.output_view.subtasks
        self.changed_files = self.bottom_tool_window.output_view.changed_files
        self.test_command_edit = (
            self.bottom_tool_window.tests_view.command_edit
        )
        self.test_output = self.bottom_tool_window.tests_view.output
        self.run_tests_button = self.bottom_tool_window.tests_view.run_button
        self.refresh_button = (
            self.bottom_tool_window.output_view.refresh_button
        )
        self.cancel_button = self.task_detail.cancel_button
        self.accept_button = self.task_detail.accept_button
        self.reject_button = self.task_detail.reject_button
        self.agent_cards = self.task_detail.agent_cards
        self.roadmap_view = self.roadmap_workspace.editor
        self.init_plan_view = self.init_workspace.content
        self.init_candidates = self.init_workspace.documents
        self.overview_generate_roadmap = self.generate_roadmap_button
        self.overview_generate_init = self.generate_init_button
        self.apply_init_button = QPushButton()
        self.apply_init_button.hide()
        self.export_roadmap_button = QPushButton()
        self.export_roadmap_button.hide()
        self.export_init_button = QPushButton()
        self.export_init_button.hide()

    def _create_compatibility_controls(self) -> None:
        self.repository_edit = QLineEdit()
        self.repository_edit.hide()
        self.browse_button = QPushButton()
        self.browse_button.hide()
        self.prompt_edit = QTextEdit()
        self.prompt_edit.hide()
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Auto", "auto")
        self.mode_combo.addItem("Mock", "mock")
        self.mode_combo.addItem("OpenCode", "opencode")
        self.mode_combo.hide()
        self.create_button = QPushButton()
        self.create_button.hide()
        self.create_button.clicked.connect(self._emit_create)
        self.task_list = QListWidget()
        self.task_list.hide()

    def _emit_create(self) -> None:
        self.create_requested.emit(
            self.repository_edit.text().strip(),
            self.prompt_edit.toPlainText().strip(),
            str(self.mode_combo.currentData()),
        )

    def set_projects(
        self, projects: list[Project], selected_id: str | None
    ) -> None:
        self.sidebar.set_projects(projects, selected_id)

    def set_project(self, project: Project | None) -> None:
        self.current_project = project
        self.project_overview.set_project(project)
        self.roadmap_workspace.set_project(project)
        self.init_workspace.set_project(project)
        if project is None:
            self.project_name_label.setText("Select a project")
            self.project_path_label.setText(
                "Create or import a project to begin."
            )
            self.project_status.set_status("Idle")
            self.roadmap_header_status.set_status("missing")
            self.init_header_status.set_status("missing")
            self.new_task_button.setEnabled(False)
            self.generate_roadmap_button.setEnabled(False)
            self.generate_init_button.setEnabled(False)
            self.workspace_stack.setCurrentWidget(self.no_selection)
            self.task_cards.clear()
            return
        self.project_name_label.setText(project.name)
        self.project_path_label.setText(str(project.repo_path))
        self.project_status.set_status(
            "Active" if project.active_task_count else "Idle"
        )
        self.roadmap_header_status.set_status(project.roadmap_status)
        self.init_header_status.set_status(project.init_status)
        self.new_task_button.setEnabled(True)
        self.generate_roadmap_button.setEnabled(True)
        self.generate_init_button.setEnabled(True)
        self.set_tasks(
            project.tasks,
            self.current_task.id
            if self.current_task is not None
            and self.current_task in project.tasks
            else None,
        )

    def show_project_overview(self, tab: str = "project") -> None:
        self.current_task = None
        if tab == "roadmap":
            self.workspace_stack.setCurrentWidget(self.roadmap_workspace)
        elif tab == "init":
            self.workspace_stack.setCurrentWidget(self.init_workspace)
        else:
            self.workspace_stack.setCurrentWidget(self.project_overview)

    def set_project_generation_running(self, running: bool) -> None:
        enabled = not running and self.current_project is not None
        self.generate_roadmap_button.setEnabled(enabled)
        self.generate_init_button.setEnabled(enabled)

    def set_tasks(
        self, tasks: list[Task], selected_id: str | None
    ) -> None:
        self.task_cards = {task.id: task for task in tasks}

    def set_repository(self, path: Path) -> None:
        self.repository_edit.setText(str(path))
        self.project_path_label.setText(str(path))

    def begin_task(self, task: Task) -> None:
        self.current_task = task
        self.logs.clear()
        self.bottom_tool_window.terminal.clear()
        self.bottom_tool_window.output_view.summary.clear()
        self.changed_files.clear()
        self.subtask_list.clear()
        self.test_output.clear()
        self.bottom_tool_window.problems_view.list.clear()
        self.task_detail.begin_task(task)
        self.bottom_tool_window.prompt_view.set_task(task)
        self.workspace_stack.setCurrentWidget(self.task_detail)
        self.set_running(True)

    def show_task(self, task: Task) -> None:
        self.current_task = task
        pending = 0
        if self.current_project is not None:
            pending = sum(
                suggestion.source_task_id == task.id
                for suggestion in self.current_project.pending_suggestions
            )
        self.task_detail.show_task(task, pending)
        self.bottom_tool_window.prompt_view.set_task(task)
        self.bottom_tool_window.output_view.summary.setPlainText(
            task.completion_summary
        )
        self.set_subtasks(task.subtasks)
        for agent in task.agents:
            for line in agent.logs:
                self.logs.append_line(agent.name, line)
        self.workspace_stack.setCurrentWidget(self.task_detail)

    def set_running(self, running: bool) -> None:
        enabled = not running and self.current_project is not None
        self.new_task_button.setEnabled(enabled)
        self.generate_roadmap_button.setEnabled(enabled)
        self.generate_init_button.setEnabled(enabled)
        self.task_detail.set_running(running)
        self.create_button.setEnabled(not running)
        self.browse_button.setEnabled(not running)
        self.prompt_edit.setEnabled(not running)
        self.mode_combo.setEnabled(not running)

    def set_task_status(self, status: str, progress: int) -> None:
        self.task_detail.set_status(status, progress)
        if self.current_task is not None:
            self.current_task.set_progress(progress)

    def set_optimized_prompt(self, prompt: str) -> None:
        self.optimized_prompt.setPlainText(prompt)

    def set_plan(self, task: Task) -> None:
        self.bottom_tool_window.prompt_view.set_task(task)
        for agent_id in task.selected_agents:
            if not DEFAULT_AGENT_REGISTRY.contains(agent_id):
                continue

    def set_subtasks(self, subtasks: list[Subtask]) -> None:
        self.subtask_list.clear()
        for index, subtask in enumerate(subtasks, start=1):
            self.subtask_list.addItem(
                f"{index:02d} {subtask.title}\n"
                f"{subtask.agent_role.value}: {subtask.description}"
            )

    def clear_agents(self) -> None:
        self.task_detail.clear_agents()

    def add_or_update_agent(self, agent: AgentState) -> None:
        self.task_detail.add_or_update_agent(agent)

    def show_repository_state(
        self, files: list[str], diff_text: str
    ) -> None:
        self.changed_files.clear()
        self.changed_files.addItems(files or ["No changed files."])
        if diff_text and not files:
            self.bottom_tool_window.problems_view.add_problem(
                "Repository diff was produced without a changed-file summary."
            )

    def set_decision_enabled(
        self, accept_enabled: bool, reject_enabled: bool
    ) -> None:
        self.task_detail.set_decision_enabled(
            accept_enabled, reject_enabled
        )
        enabled = accept_enabled or reject_enabled
        self.refresh_button.setEnabled(enabled)
        self.run_tests_button.setEnabled(enabled)

    def append_event(self, event: WorkflowEvent) -> None:
        self.bottom_tool_window.append_event(event)

    def toggle_bottom_tool(self, tool_name: str) -> None:
        if (
            self.bottom_tool_window.isVisible()
            and self.bottom_tool_window.current_tool == tool_name
        ):
            self.hide_bottom_tool()
            return
        self.bottom_tool_window.show_tool(tool_name)
        self.bottom_tool_bar.set_active(tool_name)
        height = max(220, self.height() // 3)
        self.vertical_splitter.setSizes(
            [max(320, self.height() - height), height]
        )

    def hide_bottom_tool(self) -> None:
        self.bottom_tool_window.hide_tool()
        self.bottom_tool_bar.set_active(None)
        self.vertical_splitter.setSizes([self.height(), 0])

    def add_problem(self, message: str) -> None:
        self.bottom_tool_window.problems_view.add_problem(message)

    def set_completion_summary(self, summary: str) -> None:
        self.task_detail.completion_summary.setPlainText(summary)
        self.bottom_tool_window.output_view.summary.setPlainText(summary)
