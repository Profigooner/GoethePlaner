from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from agentboard.app.models import Project

from .components import GlassPanel, NavigationButton
from .theme import THEME, rgba


class ProjectRow(QFrame):
    clicked = Signal(str)

    def __init__(self, project: Project, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("projectRow")
        self.project_id = project.id
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.name_label = QLabel(project.name)
        self.name_label.setStyleSheet("font-weight: 650;")
        self.path_label = QLabel(self._short_path(project.repo_path))
        self.path_label.setObjectName("mutedText")
        self.path_label.setToolTip(str(project.repo_path))
        self.status_dot = QLabel("●")
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.task_count = QLabel()
        self.task_count.setObjectName("mutedText")

        header = QHBoxLayout()
        header.addWidget(self.name_label)
        header.addStretch()
        header.addWidget(self.status_dot)

        footer = QHBoxLayout()
        footer.addWidget(self.path_label, 1)
        footer.addWidget(self.task_count)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 9, 11, 9)
        layout.setSpacing(4)
        layout.addLayout(header)
        layout.addLayout(footer)
        self.update_project(project)

    def update_project(self, project: Project) -> None:
        self.name_label.setText(project.name)
        self.path_label.setText(self._short_path(project.repo_path))
        count = project.active_task_count
        self.task_count.setText(
            f"{count} active" if count else f"{len(project.tasks)} tasks"
        )
        self.status_dot.setStyleSheet(
            f"color: {THEME.accent if count else THEME.text_muted};"
            "font-size: 12px;"
        )
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._apply_style()

    def _apply_style(self) -> None:
        if self.selected:
            background = rgba(THEME.accent, 22)
            border = THEME.accent
        else:
            background = THEME.panel_alt
            border = THEME.border
        self.setStyleSheet(
            "QFrame#projectRow {"
            f"background-color: {background};"
            f"border: 1px solid {border};"
            "border-radius: 9px;"
            "}"
            "QFrame#projectRow:hover {"
            f"background-color: {THEME.panel_hover};"
            f"border-color: {THEME.border_strong};"
            "}"
            "QFrame#projectRow QLabel { background: transparent; border: none; }"
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project_id)
        super().mousePressEvent(event)

    @staticmethod
    def _short_path(path: Path) -> str:
        text = str(path)
        if len(text) <= 28:
            return text
        return f"…/{path.parent.name}/{path.name}"


class ProjectSidebar(GlassPanel):
    new_project_requested = Signal()
    project_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__("sidebarPanel", parent)
        self.project_rows: dict[str, ProjectRow] = {}

        mark = QLabel("G")
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark.setFixedSize(36, 36)
        mark.setStyleSheet(
            f"background-color: {THEME.violet}; color: white;"
            "border-radius: 10px; font-size: 18px; font-weight: 750;"
        )
        product = QLabel("GoethePlaner")
        product.setObjectName("productName")
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(mark)
        brand.addWidget(product)
        brand.addStretch()

        self.new_project_button = QPushButton("+  New Project")
        self.new_project_button.setObjectName("primaryButton")
        self.new_project_button.clicked.connect(self.new_project_requested)

        self.navigation_group = QButtonGroup(self)
        self.navigation_group.setExclusive(True)
        self.projects_button = NavigationButton("▣   Projects")
        self.recent_button = NavigationButton("◷   Recent")
        self.settings_button = NavigationButton("⚙   Settings")
        self.about_button = NavigationButton("ⓘ   About")
        for button in (
            self.projects_button,
            self.recent_button,
            self.settings_button,
            self.about_button,
        ):
            self.navigation_group.addButton(button)
        self.projects_button.setChecked(True)

        projects_header = QHBoxLayout()
        project_label = QLabel("PROJECTS")
        project_label.setObjectName("sectionLabel")
        add_button = QPushButton("+")
        add_button.setObjectName("ghostButton")
        add_button.setFixedWidth(32)
        add_button.clicked.connect(self.new_project_requested)
        projects_header.addWidget(project_label)
        projects_header.addStretch()
        projects_header.addWidget(add_button)

        self.project_container = QWidget()
        self.project_layout = QVBoxLayout(self.project_container)
        self.project_layout.setContentsMargins(0, 0, 0, 0)
        self.project_layout.setSpacing(8)
        self.project_layout.addStretch()
        project_scroll = QScrollArea()
        project_scroll.setWidgetResizable(True)
        project_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        project_scroll.setWidget(self.project_container)

        account = QFrame()
        account.setObjectName("accountPanel")
        account.setStyleSheet(
            "QFrame#accountPanel {"
            f"background-color: {THEME.background_elevated};"
            f"border: 1px solid {THEME.border}; border-radius: 9px;"
            "}"
            "QFrame#accountPanel QLabel { background: transparent; border: none; }"
        )
        avatar = QLabel("LC")
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setFixedSize(34, 34)
        avatar.setStyleSheet(
            f"background-color: {THEME.violet}; color: white;"
            "border-radius: 17px; font-weight: 650;"
        )
        identity = QVBoxLayout()
        identity.setSpacing(1)
        identity.addWidget(QLabel("Local Workspace"))
        local_label = QLabel("In-memory projects")
        local_label.setObjectName("mutedText")
        identity.addWidget(local_label)
        account_layout = QHBoxLayout(account)
        account_layout.setContentsMargins(10, 8, 10, 8)
        account_layout.addWidget(avatar)
        account_layout.addLayout(identity)
        account_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(10)
        layout.addLayout(brand)
        layout.addSpacing(8)
        layout.addWidget(self.new_project_button)
        layout.addSpacing(4)
        layout.addWidget(self.projects_button)
        layout.addWidget(self.recent_button)
        layout.addWidget(self.settings_button)
        layout.addWidget(self.about_button)
        layout.addSpacing(8)
        layout.addLayout(projects_header)
        layout.addWidget(project_scroll, 1)
        layout.addWidget(account)

    def set_projects(
        self, projects: list[Project], selected_id: str | None
    ) -> None:
        known = {project.id for project in projects}
        for project_id in list(self.project_rows):
            if project_id not in known:
                row = self.project_rows.pop(project_id)
                self.project_layout.removeWidget(row)
                row.deleteLater()

        for project in projects:
            row = self.project_rows.get(project.id)
            if row is None:
                row = ProjectRow(project)
                row.clicked.connect(self.project_selected)
                self.project_rows[project.id] = row
                self.project_layout.insertWidget(
                    max(0, self.project_layout.count() - 1), row
                )
            row.update_project(project)
            row.set_selected(project.id == selected_id)
