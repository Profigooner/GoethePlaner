from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from agentboard.app.core.agent_registry import DEFAULT_AGENT_REGISTRY
from agentboard.app.models import AgentState, Project, Subtask, Task

from .agent_card import AgentCard
from .components import EmptyState, GlassPanel, ProgressPill, StatusBadge
from .diff_viewer import DiffViewer
from .log_viewer import LogViewer
from .sidebar import ProjectSidebar
from .task_card import TaskCard
from .theme import THEME, fixed_font


class TaskDashboard(QWidget):
    create_requested = Signal(str, str, str)
    cancel_requested = Signal()
    run_tests_requested = Signal(str)
    refresh_repository_requested = Signal()
    accept_requested = Signal()
    reject_requested = Signal()
    new_project_requested = Signal()
    project_selected = Signal(str)
    new_task_requested = Signal()
    task_selected = Signal(str)
    generate_roadmap_requested = Signal()
    generate_init_requested = Signal()
    open_roadmap_requested = Signal()
    settings_requested = Signal()
    export_roadmap_requested = Signal()
    export_init_requested = Signal()
    apply_init_requested = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("appRoot")
        self.agent_cards: dict[str, AgentCard] = {}
        self.task_cards: dict[str, TaskCard] = {}
        self.current_task: Task | None = None
        self.current_project: Project | None = None
        self.agent_columns = 2

        self._create_compatibility_controls()
        self.sidebar = ProjectSidebar()
        self.sidebar.new_project_requested.connect(self.new_project_requested)
        self.sidebar.project_selected.connect(self.project_selected)

        self.project_name_label = QLabel("Select a project")
        self.project_name_label.setObjectName("projectTitle")
        self.project_path_label = QLabel(
            "Create or select a project to begin."
        )
        self.project_path_label.setObjectName("secondaryText")
        self.project_status = StatusBadge("Idle")
        self.new_task_button = QPushButton("+  New Task")
        self.new_task_button.setObjectName("primaryButton")
        self.new_task_button.setEnabled(False)
        self.new_task_button.clicked.connect(self.new_task_requested)
        self.generate_roadmap_button = QPushButton("Generate Roadmap")
        self.generate_roadmap_button.setEnabled(False)
        self.generate_roadmap_button.clicked.connect(
            self.generate_roadmap_requested
        )
        self.generate_init_button = QPushButton("Generate Init")
        self.generate_init_button.setEnabled(False)
        self.generate_init_button.clicked.connect(self.generate_init_requested)
        self.open_roadmap_button = QPushButton("Open Roadmap")
        self.open_roadmap_button.setObjectName("ghostButton")
        self.open_roadmap_button.setEnabled(False)
        self.open_roadmap_button.clicked.connect(
            self.open_roadmap_requested
        )
        self.settings_button = QPushButton("Open Settings")
        self.settings_button.setObjectName("ghostButton")
        self.settings_button.setEnabled(False)
        self.settings_button.clicked.connect(self.settings_requested)
        header = GlassPanel("headerPanel")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 12, 14, 12)
        project_identity = QVBoxLayout()
        project_identity.setSpacing(3)
        title_row = QHBoxLayout()
        title_row.addWidget(self.project_name_label)
        title_row.addWidget(self.project_status)
        title_row.addStretch()
        project_identity.addLayout(title_row)
        project_identity.addWidget(self.project_path_label)
        header_layout.addLayout(project_identity, 1)
        header_layout.addWidget(self.open_roadmap_button)
        header_layout.addWidget(self.generate_roadmap_button)
        header_layout.addWidget(self.generate_init_button)
        header_layout.addWidget(self.settings_button)
        header_layout.addWidget(self.new_task_button)

        self.task_rail = self._build_task_rail()
        self.detail_panel = self._build_task_detail()
        self.inspector_panel = self._build_inspector()

        workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        workspace_splitter.setChildrenCollapsible(False)
        workspace_splitter.addWidget(self.task_rail)
        workspace_splitter.addWidget(self.detail_panel)
        workspace_splitter.addWidget(self.inspector_panel)
        workspace_splitter.setStretchFactor(0, 0)
        workspace_splitter.setStretchFactor(1, 1)
        workspace_splitter.setStretchFactor(2, 0)
        workspace_splitter.setSizes([260, 550, 430])

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_layout.addWidget(header)
        right_layout.addWidget(workspace_splitter, 1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 8)
        layout.setSpacing(10)
        layout.addWidget(self.sidebar, 0)
        layout.addWidget(right, 1)
        self.sidebar.setFixedWidth(220)

    def _create_compatibility_controls(self) -> None:
        self.repository_edit = QLineEdit()
        self.repository_edit.hide()
        self.browse_button = QPushButton()
        self.browse_button.hide()
        self.prompt_edit = QTextEdit()
        self.prompt_edit.hide()
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Auto · OpenCode when available", "auto")
        self.mode_combo.addItem("Mock · Simulated local workflow", "mock")
        self.mode_combo.addItem("OpenCode · Require installed CLI", "opencode")
        self.mode_combo.hide()
        self.create_button = QPushButton()
        self.create_button.hide()
        self.create_button.clicked.connect(self._emit_create)
        self.task_list = QListWidget()
        self.task_list.hide()

    def _build_task_rail(self) -> GlassPanel:
        panel = GlassPanel()
        label = QLabel("TASKS")
        label.setObjectName("sectionLabel")
        rail_title = QHBoxLayout()
        rail_title.addWidget(label)
        rail_title.addStretch()
        task_action = QPushButton("+")
        task_action.setObjectName("ghostButton")
        task_action.setFixedWidth(32)
        task_action.clicked.connect(self.new_task_requested)
        rail_title.addWidget(task_action)

        self.task_container = QWidget()
        self.task_layout = QVBoxLayout(self.task_container)
        self.task_layout.setContentsMargins(0, 0, 0, 0)
        self.task_layout.setSpacing(8)
        self.task_empty_label = QLabel(
            "No tasks yet.\nCreate a task to start the agent workflow."
        )
        self.task_empty_label.setObjectName("mutedText")
        self.task_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.task_empty_label.setWordWrap(True)
        self.task_layout.addWidget(self.task_empty_label)
        self.task_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.task_container)

        archive = QPushButton("▣  Show archived tasks")
        archive.setObjectName("ghostButton")
        archive.setEnabled(False)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 14, 12, 12)
        layout.setSpacing(10)
        layout.addLayout(rail_title)
        layout.addWidget(scroll, 1)
        layout.addWidget(archive)
        panel.setMinimumWidth(235)
        return panel

    def _build_task_detail(self) -> GlassPanel:
        panel = GlassPanel()
        self.detail_stack = QStackedWidget()
        self.project_overview = self._build_project_overview()
        self.no_task_state = EmptyState(
            "No task selected",
            "Select a task from the rail or create a new task for this project.",
            "New Task",
        )
        self.no_task_state.action_requested.connect(self.new_task_requested)
        self.detail_content = QWidget()

        self.task_name_label = QLabel("No task selected")
        self.task_name_label.setObjectName("taskTitle")
        self.task_status_label = StatusBadge("Draft")
        self.cancel_button = QPushButton("Cancel run")
        self.cancel_button.setObjectName("ghostButton")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_requested)
        task_header = QHBoxLayout()
        task_header.addWidget(self.task_name_label, 1)
        task_header.addWidget(self.task_status_label)
        task_header.addWidget(self.cancel_button)

        prompt_caption = QLabel("Original prompt")
        prompt_caption.setObjectName("mutedText")
        self.original_prompt = QLabel()
        self.original_prompt.setObjectName("secondaryText")
        self.original_prompt.setWordWrap(True)
        self.original_prompt.setStyleSheet(
            f"background-color: {THEME.background_elevated};"
            f"border: 1px solid {THEME.border}; border-radius: 8px;"
            "padding: 9px 10px;"
        )

        progress_header = QHBoxLayout()
        progress_header.addWidget(QLabel("Overall progress"))
        progress_header.addStretch()
        self.progress_value_label = QLabel("0%")
        self.progress_value_label.setObjectName("secondaryText")
        progress_header.addWidget(self.progress_value_label)
        self.overall_progress = ProgressPill(show_value=False)

        agents_header = QHBoxLayout()
        agents_title = QLabel("Agents")
        agents_title.setObjectName("sectionTitle")
        agents_header.addWidget(agents_title)
        agents_header.addStretch()
        parallel_label = QLabel("Parallel work units")
        parallel_label.setObjectName("mutedText")
        agents_header.addWidget(parallel_label)

        self.agent_container = QWidget()
        self.agent_layout = QGridLayout(self.agent_container)
        self.agent_layout.setContentsMargins(0, 0, 0, 0)
        self.agent_layout.setHorizontalSpacing(8)
        self.agent_layout.setVerticalSpacing(8)
        self.agent_layout.setColumnStretch(0, 1)
        self.agent_layout.setColumnStretch(1, 1)
        agent_scroll = QScrollArea()
        agent_scroll.setWidgetResizable(True)
        agent_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        agent_scroll.setWidget(self.agent_container)

        detail_layout = QVBoxLayout(self.detail_content)
        detail_layout.setContentsMargins(14, 13, 14, 12)
        detail_layout.setSpacing(9)
        detail_layout.addLayout(task_header)
        detail_layout.addWidget(prompt_caption)
        detail_layout.addWidget(self.original_prompt)
        detail_layout.addLayout(progress_header)
        detail_layout.addWidget(self.overall_progress)
        detail_layout.addLayout(agents_header)
        detail_layout.addWidget(agent_scroll, 1)

        self.detail_stack.addWidget(self.project_overview)
        self.detail_stack.addWidget(self.no_task_state)
        self.detail_stack.addWidget(self.detail_content)
        self.detail_stack.setCurrentWidget(self.project_overview)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.detail_stack)
        panel.setMinimumWidth(500)
        return panel

    def _build_project_overview(self) -> QWidget:
        page = QWidget()
        self.overview_title = QLabel("Project workspace")
        self.overview_title.setObjectName("taskTitle")
        self.overview_goal = QLabel(
            "Create a roadmap or init plan, then plan the next task."
        )
        self.overview_goal.setObjectName("secondaryText")
        self.overview_goal.setWordWrap(True)
        self.overview_stats = QLabel()
        self.overview_stats.setObjectName("mutedText")

        self.project_plan_tabs = QTabWidget()
        self.roadmap_view = QPlainTextEdit()
        self.roadmap_view.setReadOnly(True)
        self.roadmap_view.setPlaceholderText(
            "Generate a project roadmap to inspect milestones, risks, and next tasks."
        )
        roadmap_page = QWidget()
        roadmap_actions = QHBoxLayout()
        self.overview_generate_roadmap = QPushButton("Generate Roadmap")
        self.overview_generate_roadmap.setObjectName("primaryButton")
        self.overview_generate_roadmap.clicked.connect(
            self.generate_roadmap_requested
        )
        export_roadmap = QPushButton("Export Roadmap")
        export_roadmap.clicked.connect(self.export_roadmap_requested)
        roadmap_actions.addWidget(self.overview_generate_roadmap)
        roadmap_actions.addWidget(export_roadmap)
        roadmap_actions.addStretch()
        roadmap_layout = QVBoxLayout(roadmap_page)
        roadmap_layout.setContentsMargins(10, 10, 10, 10)
        roadmap_layout.addLayout(roadmap_actions)
        roadmap_layout.addWidget(self.roadmap_view)

        self.init_plan_view = QPlainTextEdit()
        self.init_plan_view.setReadOnly(True)
        self.init_plan_view.setPlaceholderText(
            "Generate a safe init plan. No files are created automatically."
        )
        self.init_candidates = QListWidget()
        self.init_candidates.setMaximumHeight(130)
        init_page = QWidget()
        init_actions = QHBoxLayout()
        self.overview_generate_init = QPushButton("Generate Init")
        self.overview_generate_init.setObjectName("primaryButton")
        self.overview_generate_init.clicked.connect(
            self.generate_init_requested
        )
        self.apply_init_button = QPushButton("Apply Selected Files")
        self.apply_init_button.clicked.connect(self._emit_apply_init)
        export_init = QPushButton("Export Init Plan")
        export_init.clicked.connect(self.export_init_requested)
        init_actions.addWidget(self.overview_generate_init)
        init_actions.addWidget(self.apply_init_button)
        init_actions.addWidget(export_init)
        init_actions.addStretch()
        init_layout = QVBoxLayout(init_page)
        init_layout.setContentsMargins(10, 10, 10, 10)
        init_layout.addLayout(init_actions)
        init_layout.addWidget(self.init_plan_view, 1)
        init_layout.addWidget(QLabel("Files that could be created"))
        init_layout.addWidget(self.init_candidates)

        self.suggested_tasks = QListWidget()
        suggested_page = QWidget()
        suggested_layout = QVBoxLayout(suggested_page)
        suggested_layout.setContentsMargins(10, 10, 10, 10)
        suggested_layout.addWidget(self.suggested_tasks)

        self.project_plan_tabs.addTab(roadmap_page, "Roadmap")
        self.project_plan_tabs.addTab(init_page, "Init Plan")
        self.project_plan_tabs.addTab(suggested_page, "Suggested Tasks")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 15, 16, 14)
        layout.addWidget(self.overview_title)
        layout.addWidget(self.overview_goal)
        layout.addWidget(self.overview_stats)
        layout.addWidget(self.project_plan_tabs, 1)
        return page

    def _emit_apply_init(self) -> None:
        selected = [
            self.init_candidates.item(index).data(
                Qt.ItemDataRole.UserRole
            )
            for index in range(self.init_candidates.count())
            if self.init_candidates.item(index).checkState()
            == Qt.CheckState.Checked
        ]
        self.apply_init_requested.emit(selected)

    def _build_inspector(self) -> GlassPanel:
        panel = GlassPanel("inspectorPanel")
        self.inspector_tabs = QTabWidget()
        self.inspector_tabs.tabBar().setExpanding(True)
        self.inspector_tabs.tabBar().setUsesScrollButtons(False)
        self.inspector_tabs.tabBar().setElideMode(Qt.TextElideMode.ElideNone)

        self.logs = LogViewer()
        self.log_source_combo = QComboBox()
        self.log_source_combo.addItems(
            [
                "All Sources",
                "GoethePlaner",
                "Git",
                *[
                    definition.display_name
                    for definition in DEFAULT_AGENT_REGISTRY.all()
                ],
            ]
        )
        self.log_source_combo.currentTextChanged.connect(
            self.logs.set_source_filter
        )
        self.log_search_edit = QLineEdit()
        self.log_search_edit.setPlaceholderText("Search logs…")
        self.log_search_edit.textChanged.connect(self.logs.set_search_filter)
        clear_logs = QPushButton("Clear")
        clear_logs.setObjectName("ghostButton")
        clear_logs.clicked.connect(self.logs.clear)
        log_page = QWidget()
        log_toolbar = QHBoxLayout()
        log_toolbar.addWidget(self.log_source_combo)
        log_toolbar.addWidget(self.log_search_edit, 1)
        log_toolbar.addWidget(clear_logs)
        log_layout = QVBoxLayout(log_page)
        log_layout.setContentsMargins(10, 10, 10, 10)
        log_layout.setSpacing(8)
        log_layout.addLayout(log_toolbar)
        log_layout.addWidget(self.logs, 1)
        self.optimized_prompt = QPlainTextEdit()
        self.optimized_prompt.setReadOnly(True)
        self.optimized_prompt.setPlaceholderText(
            "The clarified prompt will appear here."
        )
        self.task_planner_notes = QPlainTextEdit()
        self.task_planner_notes.setReadOnly(True)
        self.task_planner_notes.setPlaceholderText(
            "Planner rationale will appear here."
        )
        self.task_planner_notes.setMaximumHeight(140)
        self.selected_agent_list = QListWidget()
        self.selected_agent_list.setMaximumHeight(150)
        self.execution_graph_view = QLabel()
        self.execution_graph_view.setObjectName("secondaryText")
        self.execution_graph_view.setWordWrap(True)
        self.subtask_list = QListWidget()
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
        self.test_output.setFont(fixed_font(11))
        self.test_output.setPlaceholderText("Test output will appear here.")
        self.test_output.setStyleSheet(
            f"background-color: {THEME.console};"
            f"border: 1px solid {THEME.border};"
            "border-radius: 9px; padding: 10px;"
        )
        test_page = QWidget()
        test_row = QHBoxLayout()
        test_row.addWidget(self.test_command_edit, 1)
        test_row.addWidget(self.run_tests_button)
        test_layout = QVBoxLayout(test_page)
        test_layout.setContentsMargins(10, 10, 10, 10)
        test_layout.addLayout(test_row)
        test_layout.addWidget(self.test_output, 1)

        changed_page = QWidget()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setEnabled(False)
        changed_layout = QVBoxLayout(changed_page)
        changed_layout.setContentsMargins(10, 10, 10, 10)
        changed_layout.addWidget(self.refresh_button)
        changed_layout.addWidget(self.changed_files, 1)

        prompt_page = QWidget()
        prompt_layout = QVBoxLayout(prompt_page)
        prompt_layout.setContentsMargins(10, 10, 10, 10)
        optimized_label = QLabel("Optimized prompt")
        optimized_label.setObjectName("sectionLabel")
        prompt_layout.addWidget(optimized_label)
        prompt_layout.addWidget(self.optimized_prompt)
        planner_label = QLabel("Planner notes")
        planner_label.setObjectName("sectionLabel")
        prompt_layout.addWidget(planner_label)
        prompt_layout.addWidget(self.task_planner_notes)
        selected_label = QLabel("Selected agents")
        selected_label.setObjectName("sectionLabel")
        prompt_layout.addWidget(selected_label)
        prompt_layout.addWidget(self.selected_agent_list)
        graph_label = QLabel("Execution graph")
        graph_label.setObjectName("sectionLabel")
        prompt_layout.addWidget(graph_label)
        prompt_layout.addWidget(self.execution_graph_view)

        subtask_page = QWidget()
        subtask_layout = QVBoxLayout(subtask_page)
        subtask_layout.setContentsMargins(10, 10, 10, 10)
        subtask_layout.addWidget(self.subtask_list)

        diff_page = QWidget()
        diff_layout = QVBoxLayout(diff_page)
        diff_layout.setContentsMargins(10, 10, 10, 10)
        diff_layout.addWidget(self.diff_viewer)

        self.review_title = QLabel("Review pending")
        self.review_title.setObjectName("sectionTitle")
        self.review_summary = QLabel(
            "Complete the workflow, inspect changes and tests, then accept or "
            "reject the generated result."
        )
        self.review_summary.setObjectName("secondaryText")
        self.review_summary.setWordWrap(True)
        review_page = QWidget()
        review_layout = QVBoxLayout(review_page)
        review_layout.setContentsMargins(16, 16, 16, 16)
        review_layout.addWidget(self.review_title)
        review_layout.addWidget(self.review_summary)
        review_layout.addStretch()

        self.inspector_tabs.addTab(log_page, "Logs")
        self.inspector_tabs.addTab(prompt_page, "Prompt")
        tasks_index = self.inspector_tabs.addTab(subtask_page, "Tasks")
        self.inspector_tabs.setTabToolTip(tasks_index, "Subtasks")
        files_index = self.inspector_tabs.addTab(changed_page, "Files")
        self.inspector_tabs.setTabToolTip(files_index, "Changed Files")
        self.inspector_tabs.addTab(diff_page, "Diff")
        self.inspector_tabs.addTab(test_page, "Tests")
        self.inspector_tabs.addTab(review_page, "Review")

        self.reject_button = QPushButton("Reject")
        self.reject_button.setObjectName("dangerButton")
        self.reject_button.setEnabled(False)
        self.accept_button = QPushButton("Accept")
        self.accept_button.setObjectName("primaryButton")
        self.accept_button.setEnabled(False)
        actions = QHBoxLayout()
        actions.setContentsMargins(10, 9, 10, 10)
        actions.addStretch()
        actions.addWidget(self.reject_button)
        actions.addWidget(self.accept_button)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.inspector_tabs, 1)
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {THEME.border};")
        layout.addWidget(divider)
        layout.addLayout(actions)

        self.run_tests_button.clicked.connect(
            lambda: self.run_tests_requested.emit(
                self.test_command_edit.text().strip()
            )
        )
        self.refresh_button.clicked.connect(self.refresh_repository_requested)
        self.accept_button.clicked.connect(self.accept_requested)
        self.reject_button.clicked.connect(self.reject_requested)
        panel.setMinimumWidth(350)
        return panel

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
        if project is None:
            self.project_name_label.setText("Select a project")
            self.project_path_label.setText(
                "Create or select a project to begin."
            )
            self.project_status.set_status("Idle")
            self.new_task_button.setEnabled(False)
            self.generate_roadmap_button.setEnabled(False)
            self.generate_init_button.setEnabled(False)
            self.open_roadmap_button.setEnabled(False)
            self.settings_button.setEnabled(False)
            self.overview_generate_roadmap.setEnabled(False)
            self.overview_generate_init.setEnabled(False)
            self.apply_init_button.setEnabled(False)
            self.set_tasks([], None)
            self.detail_stack.setCurrentWidget(self.project_overview)
            return
        self.project_name_label.setText(project.name)
        self.project_path_label.setText(str(project.repo_path))
        self.project_status.set_status(
            "Active" if project.active_task_count else "Idle"
        )
        self.new_task_button.setEnabled(True)
        self.generate_roadmap_button.setEnabled(True)
        self.generate_init_button.setEnabled(True)
        self.open_roadmap_button.setEnabled(bool(project.roadmap))
        self.settings_button.setEnabled(True)
        self.overview_generate_roadmap.setEnabled(True)
        self.overview_generate_init.setEnabled(True)
        self.apply_init_button.setEnabled(True)
        self.overview_title.setText(project.name)
        self.overview_goal.setText(
            project.goal or "No project goal recorded."
        )
        self.overview_stats.setText(
            f"{len(project.tasks)} tasks · "
            f"{project.active_task_count} active · "
            f"{sum(len(task.agents) for task in project.tasks)} agent runs"
        )
        self.roadmap_view.setPlainText(project.roadmap)
        self.init_plan_view.setPlainText(project.init_plan)
        self.suggested_tasks.clear()
        self.suggested_tasks.addItems(project.suggested_next_tasks)
        self.init_candidates.clear()
        for path in project.init_candidate_files:
            item = QListWidgetItem(path)
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.init_candidates.addItem(item)
        self.set_tasks(
            project.tasks,
            self.current_task.id
            if self.current_task and self.current_task in project.tasks
            else None,
        )
        if self.current_task is None or self.current_task not in project.tasks:
            self.detail_stack.setCurrentWidget(self.project_overview)

    def show_project_overview(self, tab: str = "roadmap") -> None:
        self.current_task = None
        self.detail_stack.setCurrentWidget(self.project_overview)
        index = {"roadmap": 0, "init": 1, "tasks": 2}.get(tab, 0)
        self.project_plan_tabs.setCurrentIndex(index)

    def set_project_generation_running(self, running: bool) -> None:
        self.generate_roadmap_button.setEnabled(
            not running and self.current_project is not None
        )
        self.generate_init_button.setEnabled(
            not running and self.current_project is not None
        )
        self.overview_generate_roadmap.setEnabled(
            not running and self.current_project is not None
        )
        self.overview_generate_init.setEnabled(
            not running and self.current_project is not None
        )
        self.apply_init_button.setEnabled(
            not running and self.current_project is not None
        )

    def set_tasks(
        self, tasks: list[Task], selected_id: str | None
    ) -> None:
        known = {task.id for task in tasks}
        for task_id in list(self.task_cards):
            if task_id not in known:
                card = self.task_cards.pop(task_id)
                self.task_layout.removeWidget(card)
                card.deleteLater()
        self.task_empty_label.setVisible(not tasks)
        for task in tasks:
            card = self.task_cards.get(task.id)
            if card is None:
                card = TaskCard(task)
                card.clicked.connect(self.task_selected)
                self.task_cards[task.id] = card
                self.task_layout.insertWidget(
                    max(0, self.task_layout.count() - 1), card
                )
            card.update_task(task)
            card.set_selected(task.id == selected_id)

    def set_repository(self, path: Path) -> None:
        self.repository_edit.setText(str(path))
        self.project_path_label.setText(str(path))

    def begin_task(self, task: Task) -> None:
        self.current_task = task
        self.task_name_label.setText(task.title)
        self.task_status_label.set_status(task.status)
        self.overall_progress.setValue(task.overall_progress)
        self.progress_value_label.setText(f"{task.overall_progress}%")
        self.original_prompt.setText(task.original_prompt)
        self.optimized_prompt.clear()
        self.task_planner_notes.clear()
        self.selected_agent_list.clear()
        self.execution_graph_view.clear()
        self.subtask_list.clear()
        self.logs.clear()
        self.changed_files.clear()
        self.diff_viewer.clear()
        self.test_output.clear()
        self.review_title.setText("Review pending")
        self.review_summary.setText(
            "Agents are working. Review results will become available when the "
            "workflow completes."
        )
        self.clear_agents()
        self.detail_stack.setCurrentWidget(self.detail_content)
        self.set_plan(task)
        self.set_running(True)
        if self.current_project is not None:
            self.set_tasks(self.current_project.tasks, task.id)

    def show_task(self, task: Task) -> None:
        self.begin_task(task)
        self.set_running(False)
        self.set_optimized_prompt(task.optimized_prompt)
        self.set_plan(task)
        self.set_subtasks(task.subtasks)
        for agent in task.agents:
            self.add_or_update_agent(agent)
            for line in agent.logs:
                self.logs.append_line(agent.name, line)

    def set_running(self, running: bool) -> None:
        self.new_task_button.setEnabled(
            not running and self.current_project is not None
        )
        planning_enabled = not running and self.current_project is not None
        self.generate_roadmap_button.setEnabled(planning_enabled)
        self.generate_init_button.setEnabled(planning_enabled)
        self.overview_generate_roadmap.setEnabled(planning_enabled)
        self.overview_generate_init.setEnabled(planning_enabled)
        self.apply_init_button.setEnabled(planning_enabled)
        self.cancel_button.setEnabled(running)
        self.create_button.setEnabled(not running)
        self.browse_button.setEnabled(not running)
        self.prompt_edit.setEnabled(not running)
        self.mode_combo.setEnabled(not running)

    def set_task_status(self, status: str, progress: int) -> None:
        self.task_status_label.set_status(status)
        self.overall_progress.setValue(progress)
        self.progress_value_label.setText(f"{progress}%")
        if self.current_task is not None:
            self.current_task.set_progress(progress)
            self.review_title.setText(
                "Ready for review" if progress == 100 else "Review pending"
            )
            if self.current_project is not None:
                self.set_tasks(self.current_project.tasks, self.current_task.id)

    def set_optimized_prompt(self, prompt: str) -> None:
        self.optimized_prompt.setPlainText(prompt)

    def set_plan(self, task: Task) -> None:
        self.task_planner_notes.setPlainText(task.planner_notes)
        self.selected_agent_list.clear()
        for agent_id in task.selected_agents:
            if DEFAULT_AGENT_REGISTRY.contains(agent_id):
                definition = DEFAULT_AGENT_REGISTRY.get(agent_id)
                reason = task.agent_selection_reasons.get(
                    agent_id, definition.description
                )
                self.selected_agent_list.addItem(
                    f"{definition.display_name} · {definition.risk_level.title()} risk\n"
                    f"{reason}"
                )
            else:
                self.selected_agent_list.addItem(agent_id)
        stages: list[str] = []
        for stage in task.execution_graph:
            names = [
                DEFAULT_AGENT_REGISTRY.get(agent_id).display_name
                if DEFAULT_AGENT_REGISTRY.contains(agent_id)
                else agent_id
                for agent_id in stage
            ]
            stages.append(" + ".join(names))
        self.execution_graph_view.setText("  →  ".join(stages))

    def set_subtasks(self, subtasks: list[Subtask]) -> None:
        self.subtask_list.clear()
        for index, subtask in enumerate(subtasks, start=1):
            self.subtask_list.addItem(
                f"{index:02d}  {subtask.title}\n"
                f"      {subtask.agent_role.value} · {subtask.description}"
            )

    def clear_agents(self) -> None:
        for card in self.agent_cards.values():
            self.agent_layout.removeWidget(card)
            card.deleteLater()
        self.agent_cards.clear()

    def add_or_update_agent(self, agent: AgentState) -> None:
        card = self.agent_cards.get(agent.id)
        if card is None:
            card = AgentCard(agent)
            self.agent_cards[agent.id] = card
            self._relayout_agent_cards()
        else:
            card.update_agent(agent)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._relayout_agent_cards)

    def _relayout_agent_cards(self) -> None:
        if not hasattr(self, "detail_panel"):
            return
        columns = 2 if self.detail_panel.width() >= 540 else 1
        if columns == self.agent_columns and all(
            self.agent_layout.indexOf(card) >= 0
            for card in self.agent_cards.values()
        ):
            return
        self.agent_columns = columns
        for index, card in enumerate(self.agent_cards.values()):
            self.agent_layout.removeWidget(card)
            self.agent_layout.addWidget(
                card, index // columns, index % columns
            )
        self.agent_layout.setColumnStretch(0, 1)
        self.agent_layout.setColumnStretch(1, 1 if columns == 2 else 0)

    def show_repository_state(
        self, files: list[str], diff_text: str
    ) -> None:
        self.changed_files.clear()
        self.changed_files.addItems(files)
        if not files:
            self.changed_files.addItem("No changed files.")
        self.diff_viewer.set_diff(diff_text or "No working-tree changes.")

    def set_decision_enabled(
        self, accept_enabled: bool, reject_enabled: bool
    ) -> None:
        self.accept_button.setEnabled(accept_enabled)
        self.reject_button.setEnabled(reject_enabled)
        enabled = accept_enabled or reject_enabled
        self.refresh_button.setEnabled(enabled)
        self.run_tests_button.setEnabled(enabled)
        if enabled:
            self.review_title.setText("Ready for review")
            self.review_summary.setText(
                "Inspect the logs, changed files, diff, and test output before "
                "accepting or rejecting this task."
            )
