from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from agentboard.app.models import AgentState, Project, Task

from .agent_card import AgentCard
from .components import StatusBadge
from .theme import THEME


class ProjectOverviewView(QWidget):
    roadmap_requested = Signal()
    init_requested = Signal()
    new_task_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.title = QLabel("Select a project")
        self.title.setObjectName("projectTitle")
        self.path = QLabel()
        self.path.setObjectName("secondaryText")
        self.goal = QLabel()
        self.goal.setObjectName("secondaryText")
        self.goal.setWordWrap(True)
        self.type_label = QLabel()
        self.roadmap_status = StatusBadge("missing")
        self.init_status = StatusBadge("missing")
        self.task_summary = QLabel()
        self.task_summary.setObjectName("secondaryText")
        self.recent_results = QListWidget()
        self.next_action = QLabel()
        self.next_action.setObjectName("secondaryText")
        self.next_action.setWordWrap(True)

        roadmap = QPushButton("Open Roadmap")
        roadmap.clicked.connect(self.roadmap_requested)
        init = QPushButton("Open Init")
        init.clicked.connect(self.init_requested)
        new_task = QPushButton("New Task")
        new_task.setObjectName("primaryButton")
        new_task.clicked.connect(self.new_task_requested)
        actions = QHBoxLayout()
        actions.addWidget(roadmap)
        actions.addWidget(init)
        actions.addWidget(new_task)
        actions.addStretch()

        statuses = QHBoxLayout()
        statuses.addWidget(QLabel("Roadmap"))
        statuses.addWidget(self.roadmap_status)
        statuses.addSpacing(18)
        statuses.addWidget(QLabel("Init"))
        statuses.addWidget(self.init_status)
        statuses.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(10)
        layout.addWidget(self.title)
        layout.addWidget(self.path)
        layout.addWidget(self.goal)
        layout.addWidget(self.type_label)
        layout.addLayout(statuses)
        layout.addWidget(self.task_summary)
        layout.addLayout(actions)
        layout.addSpacing(10)
        layout.addWidget(QLabel("Recent task results"))
        layout.addWidget(self.recent_results, 1)
        layout.addWidget(QLabel("Suggested next action"))
        layout.addWidget(self.next_action)

    def set_project(self, project: Project | None) -> None:
        self.recent_results.clear()
        if project is None:
            self.title.setText("Select a project")
            self.path.clear()
            self.goal.setText("Create or import a project to begin.")
            self.type_label.clear()
            self.task_summary.clear()
            self.next_action.setText("Use New Project in the sidebar.")
            self.roadmap_status.set_status("missing")
            self.init_status.set_status("missing")
            return
        self.title.setText(project.name)
        self.path.setText(str(project.repo_path))
        self.goal.setText(project.goal or "No project goal recorded.")
        project_type = (
            project.detected_project_type
            or (
                project.analysis.detected_project_type
                if project.analysis is not None
                else "Not analyzed"
            )
        )
        self.type_label.setText(
            f"{project.project_type.title()} project | {project_type}"
        )
        self.roadmap_status.set_status(project.roadmap_status)
        self.init_status.set_status(project.init_status)
        self.task_summary.setText(
            f"{len(project.tasks)} tasks | "
            f"{project.active_task_count} active | "
            f"{len(project.pending_suggestions)} pending project updates"
        )
        for task in reversed(project.tasks[-8:]):
            summary = task.completion_summary or task.original_prompt
            self.recent_results.addItem(
                f"{task.title} [{task.status.value}]\n{summary}"
            )
        if project.roadmap_status == "missing":
            next_action = "Create or import the project Roadmap."
        elif project.init_status == "missing":
            next_action = "Run Init Agent or import existing project context."
        elif project.pending_suggestions:
            next_action = "Review pending Roadmap and Init update suggestions."
        else:
            next_action = "Create the next task from the project tree."
        self.next_action.setText(next_action)


class SuggestionReviewPanel(QFrame):
    accept_requested = Signal(str)
    reject_requested = Signal(str)

    def __init__(self, target: str, parent=None) -> None:
        super().__init__(parent)
        self.target = target
        self.setObjectName("suggestionPanel")
        self.list = QTreeWidget()
        self.list.setHeaderLabels(["Suggested change", "Source task"])
        self.list.setRootIsDecorated(False)
        self.list.setMinimumHeight(90)
        accept = QPushButton("Accept Selected")
        accept.setObjectName("primaryButton")
        reject = QPushButton("Reject Selected")
        reject.setObjectName("dangerButton")
        accept.clicked.connect(self._accept)
        reject.clicked.connect(self._reject)
        row = QHBoxLayout()
        row.addWidget(
            QLabel(
                f"Pending {target.title()} updates. Nothing changes until accepted."
            )
        )
        row.addStretch()
        row.addWidget(reject)
        row.addWidget(accept)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.list)
        self.setMaximumHeight(190)

    def set_project(self, project: Project | None) -> None:
        self.list.clear()
        if project is None:
            self.hide()
            return
        suggestions = [
            item
            for item in project.pending_suggestions
            if item.target == self.target
        ]
        task_titles = {task.id: task.title for task in project.tasks}
        for suggestion in suggestions:
            preview = " ".join(suggestion.suggested_change.split())
            item = QTreeWidgetItem(
                [
                    preview[:180],
                    task_titles.get(
                        suggestion.source_task_id or "", "Project"
                    ),
                ]
            )
            item.setData(0, Qt.ItemDataRole.UserRole, suggestion.id)
            item.setToolTip(0, suggestion.suggested_change)
            self.list.addTopLevelItem(item)
        self.setVisible(bool(suggestions))

    def _selected_id(self) -> str:
        item = self.list.currentItem()
        return (
            str(item.data(0, Qt.ItemDataRole.UserRole))
            if item is not None
            else ""
        )

    def _accept(self) -> None:
        if suggestion_id := self._selected_id():
            self.accept_requested.emit(suggestion_id)

    def _reject(self) -> None:
        if suggestion_id := self._selected_id():
            self.reject_requested.emit(suggestion_id)


class RoadmapView(QWidget):
    content_saved = Signal(str)
    ask_agent_requested = Signal()
    add_requirement_requested = Signal()
    import_requested = Signal()
    export_requested = Signal()
    create_task_requested = Signal(str)
    suggestion_accept_requested = Signal(str)
    suggestion_reject_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.project: Project | None = None
        self.title = QLabel("Roadmap")
        self.title.setObjectName("projectTitle")
        self.status = StatusBadge("missing")
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setPlaceholderText(
            "No roadmap yet.\n\nCreate Roadmap with Agent or import ROADMAP.md."
        )
        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self._toggle_edit)
        save = QPushButton("Save")
        save.clicked.connect(
            lambda: self.content_saved.emit(self.editor.toPlainText())
        )
        ask = QPushButton("Ask Agent")
        ask.clicked.connect(self.ask_agent_requested)
        add = QPushButton("Add Requirement")
        add.clicked.connect(self.add_requirement_requested)
        remove = QPushButton("Remove Requirement")
        remove.clicked.connect(self._remove_current_line)
        complete = QPushButton("Mark Complete")
        complete.clicked.connect(self._mark_current_line_complete)
        up = QPushButton("Move Up")
        up.clicked.connect(lambda: self._move_current_line(-1))
        down = QPushButton("Move Down")
        down.clicked.connect(lambda: self._move_current_line(1))
        task = QPushButton("Turn Into Task")
        task.clicked.connect(self._create_task)
        import_button = QPushButton("Import")
        import_button.clicked.connect(self.import_requested)
        export_button = QPushButton("Export")
        export_button.clicked.connect(self.export_requested)

        header = QHBoxLayout()
        header.addWidget(self.title)
        header.addWidget(self.status)
        header.addStretch()
        header.addWidget(ask)
        header.addWidget(import_button)
        header.addWidget(export_button)
        row = QHBoxLayout()
        for button in (
            self.edit_button,
            save,
            add,
            remove,
            complete,
            up,
            down,
            task,
        ):
            row.addWidget(button)
        row.addStretch()
        self.suggestions = SuggestionReviewPanel("roadmap")
        self.suggestions.accept_requested.connect(
            self.suggestion_accept_requested
        )
        self.suggestions.reject_requested.connect(
            self.suggestion_reject_requested
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.addLayout(header)
        layout.addLayout(row)
        layout.addWidget(self.editor, 1)
        layout.addWidget(self.suggestions)

    def set_project(self, project: Project | None) -> None:
        self.project = project
        self.title.setText(
            f"{project.name} Roadmap" if project is not None else "Roadmap"
        )
        self.status.set_status(
            project.roadmap_status if project is not None else "missing"
        )
        self.editor.setPlainText(project.roadmap if project is not None else "")
        self.editor.setReadOnly(True)
        self.edit_button.setText("Edit")
        self.suggestions.set_project(project)

    def _toggle_edit(self) -> None:
        editable = self.editor.isReadOnly()
        self.editor.setReadOnly(not editable)
        self.edit_button.setText("Stop Editing" if editable else "Edit")

    def _line_state(self) -> tuple[list[str], int]:
        lines = self.editor.toPlainText().splitlines()
        index = self.editor.textCursor().blockNumber()
        return lines, index

    def _commit_lines(self, lines: list[str]) -> None:
        content = "\n".join(lines)
        if content and not content.endswith("\n"):
            content += "\n"
        self.editor.setPlainText(content)
        self.content_saved.emit(content)

    def _remove_current_line(self) -> None:
        lines, index = self._line_state()
        if 0 <= index < len(lines) and lines[index].strip():
            lines.pop(index)
            self._commit_lines(lines)

    def _mark_current_line_complete(self) -> None:
        lines, index = self._line_state()
        if not 0 <= index < len(lines):
            return
        line = lines[index]
        if "- [ ]" in line:
            lines[index] = line.replace("- [ ]", "- [x]", 1)
        elif "- [x]" not in line:
            lines[index] = f"- [x] {line.lstrip('- ').strip()}"
        self._commit_lines(lines)

    def _move_current_line(self, offset: int) -> None:
        lines, index = self._line_state()
        target = index + offset
        if not (0 <= index < len(lines) and 0 <= target < len(lines)):
            return
        lines[index], lines[target] = lines[target], lines[index]
        self._commit_lines(lines)

    def _create_task(self) -> None:
        lines, index = self._line_state()
        if not 0 <= index < len(lines):
            return
        requirement = (
            lines[index]
            .replace("- [ ]", "", 1)
            .replace("- [x]", "", 1)
            .lstrip("- ")
            .strip()
        )
        if requirement:
            self.create_task_requested.emit(requirement)


class InitView(QWidget):
    run_agent_requested = Signal()
    import_requested = Signal()
    suggestion_accept_requested = Signal(str)
    suggestion_reject_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.title = QLabel("Init")
        self.title.setObjectName("projectTitle")
        self.status = StatusBadge("missing")
        self.content = QPlainTextEdit()
        self.content.setReadOnly(True)
        self.content.setPlaceholderText(
            "No init context yet.\n\nRun Init Agent or import AGENTS/README."
        )
        self.documents = QListWidget()
        run = QPushButton("Run Init Agent")
        run.setObjectName("primaryButton")
        run.clicked.connect(self.run_agent_requested)
        import_button = QPushButton("Import Existing Context")
        import_button.clicked.connect(self.import_requested)
        header = QHBoxLayout()
        header.addWidget(self.title)
        header.addWidget(self.status)
        header.addStretch()
        header.addWidget(import_button)
        header.addWidget(run)
        self.suggestions = SuggestionReviewPanel("init")
        self.suggestions.accept_requested.connect(
            self.suggestion_accept_requested
        )
        self.suggestions.reject_requested.connect(
            self.suggestion_reject_requested
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.addLayout(header)
        layout.addWidget(QLabel("Current project context"))
        layout.addWidget(self.content, 2)
        layout.addWidget(QLabel("Detected and imported documents"))
        layout.addWidget(self.documents, 1)
        layout.addWidget(self.suggestions)

    def set_project(self, project: Project | None) -> None:
        self.documents.clear()
        self.title.setText(
            f"{project.name} Init" if project is not None else "Init"
        )
        self.status.set_status(
            project.init_status if project is not None else "missing"
        )
        self.content.setPlainText(project.init_plan if project is not None else "")
        if project is not None:
            for document in project.documents:
                self.documents.addItem(
                    f"{document.path or document.kind} [{document.status}]"
                )
            if project.analysis is not None:
                known = {
                    document.path for document in project.documents
                }
                for path in project.analysis.documentation_files:
                    if path not in known:
                        self.documents.addItem(f"{path} [detected]")
        self.suggestions.set_project(project)


class TaskDetailView(QWidget):
    cancel_requested = Signal()
    accept_requested = Signal()
    reject_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.agent_cards: dict[str, AgentCard] = {}
        self.agent_columns = 2
        self.title = QLabel("No task selected")
        self.title.setObjectName("projectTitle")
        self.status = StatusBadge("Draft")
        self.cancel_button = QPushButton("Cancel Run")
        self.cancel_button.clicked.connect(self.cancel_requested)
        self.accept_button = QPushButton("Accept")
        self.accept_button.setObjectName("primaryButton")
        self.accept_button.clicked.connect(self.accept_requested)
        self.reject_button = QPushButton("Reject")
        self.reject_button.setObjectName("dangerButton")
        self.reject_button.clicked.connect(self.reject_requested)
        self.prompt = QLabel()
        self.prompt.setObjectName("secondaryText")
        self.prompt.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress_value = QLabel("0%")
        self.completion_summary = QPlainTextEdit()
        self.completion_summary.setReadOnly(True)
        self.completion_summary.setMaximumHeight(100)
        self.completion_summary.setPlaceholderText(
            "A completion summary appears after the task finishes."
        )
        self.update_notice = QLabel()
        self.update_notice.setObjectName("secondaryText")
        self.update_notice.setWordWrap(True)

        header = QHBoxLayout()
        header.addWidget(self.title, 1)
        header.addWidget(self.status)
        header.addWidget(self.cancel_button)
        header.addWidget(self.reject_button)
        header.addWidget(self.accept_button)
        progress_row = QHBoxLayout()
        progress_row.addWidget(QLabel("Progress"))
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.progress_value)
        self.agent_container = QWidget()
        self.agent_layout = QGridLayout(self.agent_container)
        self.agent_layout.setContentsMargins(0, 0, 0, 0)
        self.agent_layout.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.agent_container)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.addLayout(header)
        layout.addWidget(QLabel("Original prompt"))
        layout.addWidget(self.prompt)
        layout.addLayout(progress_row)
        layout.addWidget(QLabel("Agent execution"))
        layout.addWidget(scroll, 1)
        layout.addWidget(QLabel("Final result summary"))
        layout.addWidget(self.completion_summary)
        layout.addWidget(self.update_notice)
        self.set_running(False)
        self.set_decision_enabled(False, False)

    def begin_task(self, task: Task) -> None:
        self.title.setText(task.title)
        self.prompt.setText(task.original_prompt)
        self.status.set_status(task.status)
        self.progress.setValue(task.progress)
        self.progress_value.setText(f"{task.progress}%")
        self.completion_summary.setPlainText(task.completion_summary)
        self.update_notice.clear()
        self.clear_agents()
        self.set_running(True)

    def show_task(self, task: Task, pending_updates: int = 0) -> None:
        self.begin_task(task)
        for agent in task.agents:
            self.add_or_update_agent(agent)
        self.set_running(False)
        self.completion_summary.setPlainText(task.completion_summary)
        if pending_updates:
            self.update_notice.setText(
                f"{pending_updates} project update suggestion(s) await review "
                "in Roadmap and Init."
            )

    def set_running(self, running: bool) -> None:
        self.cancel_button.setEnabled(running)

    def set_status(self, status: str, progress: int) -> None:
        self.status.set_status(status)
        self.progress.setValue(progress)
        self.progress_value.setText(f"{progress}%")

    def set_decision_enabled(
        self, accept_enabled: bool, reject_enabled: bool
    ) -> None:
        self.accept_button.setEnabled(accept_enabled)
        self.reject_button.setEnabled(reject_enabled)

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
        else:
            card.update_agent(agent)
        self._relayout()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        columns = 2 if self.width() >= 760 else 1
        self.agent_columns = columns
        for index, card in enumerate(self.agent_cards.values()):
            self.agent_layout.removeWidget(card)
            self.agent_layout.addWidget(
                card, index // columns, index % columns
            )
        self.agent_layout.setColumnStretch(0, 1)
        self.agent_layout.setColumnStretch(1, 1 if columns == 2 else 0)
