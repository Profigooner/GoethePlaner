from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from agentboard.app.core.agent_registry import DEFAULT_AGENT_REGISTRY
from agentboard.app.models import Task, WorkflowEvent

from .log_viewer import LogViewer
from .theme import THEME, fixed_font


TOOL_NAMES = ("Terminal", "Logs", "Prompt", "Output", "Tests", "Problems")


class ToolWindowButton(QPushButton):
    def __init__(self, tool_name: str, parent=None) -> None:
        super().__init__(tool_name, parent)
        self.tool_name = tool_name
        self.setCheckable(True)
        self.setObjectName("toolWindowButton")


class BottomToolBar(QFrame):
    tool_toggled = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("bottomToolBar")
        self.buttons: dict[str, ToolWindowButton] = {}
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)
        for name in TOOL_NAMES:
            button = ToolWindowButton(name)
            button.clicked.connect(
                lambda _checked=False, tool=name: self.tool_toggled.emit(tool)
            )
            self.buttons[name] = button
            layout.addWidget(button)
        layout.addStretch()

    def set_active(self, tool_name: str | None) -> None:
        for name, button in self.buttons.items():
            button.setChecked(name == tool_name)


class TerminalOutputView(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(10_000)
        self.setFont(fixed_font(11))
        self.setPlaceholderText(
            "OpenCode commands, workflow output, and test output appear here."
        )
        self.setStyleSheet(
            f"background-color: {THEME.console};"
            f"border: 1px solid {THEME.border};"
            "border-radius: 8px; padding: 9px;"
        )


class LogsToolView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.viewer = LogViewer()
        source = QComboBox()
        source.addItems(
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
        source.currentTextChanged.connect(self.viewer.set_source_filter)
        search = QLineEdit()
        search.setPlaceholderText("Search logs...")
        search.textChanged.connect(self.viewer.set_search_filter)
        clear = QPushButton("Clear")
        clear.clicked.connect(self.viewer.clear)
        toolbar = QHBoxLayout()
        toolbar.addWidget(source)
        toolbar.addWidget(search, 1)
        toolbar.addWidget(clear)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(toolbar)
        layout.addWidget(self.viewer, 1)


class PromptToolView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.original_prompt = QPlainTextEdit()
        self.original_prompt.setReadOnly(True)
        self.optimized_prompt = QPlainTextEdit()
        self.optimized_prompt.setReadOnly(True)
        self.planner_notes = QPlainTextEdit()
        self.planner_notes.setReadOnly(True)
        self.selected_agents = QListWidget()
        self.execution_graph = QLabel()
        self.execution_graph.setObjectName("secondaryText")
        self.execution_graph.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(QLabel("Original prompt"))
        layout.addWidget(self.original_prompt, 1)
        layout.addWidget(QLabel("Optimized prompt"))
        layout.addWidget(self.optimized_prompt, 1)
        layout.addWidget(QLabel("Planner notes"))
        layout.addWidget(self.planner_notes, 1)
        layout.addWidget(QLabel("Selected agents"))
        layout.addWidget(self.selected_agents, 1)
        layout.addWidget(QLabel("Execution graph"))
        layout.addWidget(self.execution_graph)

    def set_task(self, task: Task) -> None:
        self.original_prompt.setPlainText(task.original_prompt)
        self.optimized_prompt.setPlainText(task.optimized_prompt)
        self.planner_notes.setPlainText(task.planner_notes)
        self.selected_agents.clear()
        for agent_id in task.selected_agents:
            if DEFAULT_AGENT_REGISTRY.contains(agent_id):
                definition = DEFAULT_AGENT_REGISTRY.get(agent_id)
                self.selected_agents.addItem(definition.display_name)
            else:
                self.selected_agents.addItem(agent_id)
        stages: list[str] = []
        for stage in task.execution_graph:
            stages.append(
                " + ".join(
                    DEFAULT_AGENT_REGISTRY.get(agent_id).display_name
                    if DEFAULT_AGENT_REGISTRY.contains(agent_id)
                    else agent_id
                    for agent_id in stage
                )
            )
        self.execution_graph.setText(" -> ".join(stages))


class OutputToolView(QWidget):
    refresh_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.summary = QPlainTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setPlaceholderText("The final task summary appears here.")
        self.changed_files = QListWidget()
        self.subtasks = QListWidget()
        self.refresh_button = QPushButton("Refresh Repository")
        self.refresh_button.clicked.connect(self.refresh_requested)
        row = QHBoxLayout()
        row.addWidget(QLabel("Completion summary and generated artifacts"))
        row.addStretch()
        row.addWidget(self.refresh_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(row)
        layout.addWidget(self.summary, 1)
        layout.addWidget(QLabel("Agent assignments"))
        layout.addWidget(self.subtasks, 1)
        layout.addWidget(QLabel("Changed files"))
        layout.addWidget(self.changed_files, 1)


class TestsToolView(QWidget):
    run_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText(
            "Test command, for example: python -m unittest discover -v"
        )
        self.run_button = QPushButton("Run Tests")
        self.run_button.clicked.connect(
            lambda: self.run_requested.emit(self.command_edit.text().strip())
        )
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(fixed_font(11))
        self.output.setPlaceholderText("Test output appears here.")
        row = QHBoxLayout()
        row.addWidget(self.command_edit, 1)
        row.addWidget(self.run_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(row)
        layout.addWidget(self.output, 1)


class ProblemsToolView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.list = QListWidget()
        clear = QPushButton("Clear")
        clear.clicked.connect(self.list.clear)
        row = QHBoxLayout()
        row.addWidget(QLabel("Warnings and workflow problems"))
        row.addStretch()
        row.addWidget(clear)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(row)
        layout.addWidget(self.list, 1)

    def add_problem(self, message: str) -> None:
        if message.strip():
            self.list.addItem(message.strip())


class BottomToolWindow(QFrame):
    close_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("bottomToolWindow")
        self.current_tool: str | None = None
        self.title = QLabel()
        self.title.setObjectName("sectionTitle")
        close = QPushButton("Close")
        close.setObjectName("ghostButton")
        close.clicked.connect(self.close_requested)
        header = QHBoxLayout()
        header.addWidget(self.title)
        header.addStretch()
        header.addWidget(close)

        self.stack = QStackedWidget()
        self.terminal = TerminalOutputView()
        self.logs_view = LogsToolView()
        self.prompt_view = PromptToolView()
        self.output_view = OutputToolView()
        self.tests_view = TestsToolView()
        self.problems_view = ProblemsToolView()
        self.pages: dict[str, QWidget] = {
            "Terminal": self.terminal,
            "Logs": self.logs_view,
            "Prompt": self.prompt_view,
            "Output": self.output_view,
            "Tests": self.tests_view,
            "Problems": self.problems_view,
        }
        for page in self.pages.values():
            self.stack.addWidget(page)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.addLayout(header)
        layout.addWidget(self.stack, 1)
        self.hide()

    @property
    def logs(self) -> LogViewer:
        return self.logs_view.viewer

    def show_tool(self, tool_name: str) -> None:
        page = self.pages.get(tool_name)
        if page is None:
            raise ValueError(f"Unknown bottom tool: {tool_name}")
        self.current_tool = tool_name
        self.title.setText(tool_name)
        self.stack.setCurrentWidget(page)
        self.show()

    def hide_tool(self) -> None:
        self.current_tool = None
        self.hide()

    def append_event(self, event: WorkflowEvent) -> None:
        self.logs.append_event(event)
        self.terminal.appendPlainText(
            f"[{event.source}] {event.message}"
        )
        if event.kind.value == "error":
            self.problems_view.add_problem(
                f"{event.source}: {event.message}"
            )
