from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from agentboard.app.models import Project

from .components import GlassPanel
from .theme import THEME

LOGO_PATH = (
    Path(__file__).resolve().parents[3]
    / "assets"
    / "goetheplaner-logo-icon.png"
)

ITEM_KIND_ROLE = Qt.ItemDataRole.UserRole
PROJECT_ID_ROLE = Qt.ItemDataRole.UserRole + 1
ITEM_ID_ROLE = Qt.ItemDataRole.UserRole + 2


class ProjectSidebar(GlassPanel):
    new_project_requested = Signal()
    project_selected = Signal(str)
    task_selected = Signal(str)
    navigation_selected = Signal(str, str, str)
    new_task_requested = Signal(str)
    settings_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__("sidebarPanel", parent)
        self.project_rows: dict[str, QTreeWidgetItem] = {}
        self._selected_key: tuple[str, str, str] | None = None

        self.logo_label = QLabel()
        self.logo_label.setObjectName("productLogo")
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setFixedSize(40, 40)
        logo = QPixmap(str(LOGO_PATH))
        if logo.isNull():
            self.logo_label.setText("G")
            self.logo_label.setStyleSheet(
                f"background-color: {THEME.violet}; color: white;"
                "border-radius: 10px; font-size: 18px; font-weight: 750;"
            )
        else:
            self.logo_label.setPixmap(
                logo.scaled(
                    self.logo_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        product = QLabel("GoethePlaner")
        product.setObjectName("productName")
        brand = QHBoxLayout()
        brand.setSpacing(10)
        brand.addWidget(self.logo_label)
        brand.addWidget(product)
        brand.addStretch()

        self.new_project_button = QPushButton("+ New Project")
        self.new_project_button.setObjectName("primaryButton")
        self.new_project_button.clicked.connect(self.new_project_requested)

        label = QLabel("PROJECTS")
        label.setObjectName("sectionLabel")
        self.tree = QTreeWidget()
        self.tree.setObjectName("projectTree")
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(18)
        self.tree.setAnimated(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(False)
        self.tree.itemClicked.connect(self._item_clicked)

        self.settings_button = QPushButton("Settings")
        self.settings_button.setObjectName("ghostButton")
        self.settings_button.clicked.connect(self.settings_requested)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 16, 14, 14)
        layout.setSpacing(10)
        layout.addLayout(brand)
        layout.addSpacing(8)
        layout.addWidget(self.new_project_button)
        layout.addSpacing(8)
        layout.addWidget(label)
        layout.addWidget(self.tree, 1)
        layout.addWidget(self.settings_button)

    def set_projects(
        self, projects: list[Project], selected_id: str | None
    ) -> None:
        expanded = {
            item.data(0, PROJECT_ID_ROLE)
            for index in range(self.tree.topLevelItemCount())
            if (item := self.tree.topLevelItem(index)).isExpanded()
        }
        self.tree.clear()
        self.project_rows.clear()
        selected_item: QTreeWidgetItem | None = None
        for project in projects:
            root = self._item(
                project.name,
                "project",
                project.id,
                project.id,
            )
            root.setToolTip(
                0,
                f"{project.repo_path}\n"
                f"Roadmap: {project.roadmap_status}\n"
                f"Init: {project.init_status}",
            )
            font = root.font(0)
            font.setBold(True)
            root.setFont(0, font)
            self.tree.addTopLevelItem(root)
            self.project_rows[project.id] = root

            roadmap = self._item(
                f"Roadmap  [{project.roadmap_status}]",
                "roadmap",
                project.id,
                "roadmap",
            )
            init = self._item(
                f"Init  [{project.init_status}]",
                "init",
                project.id,
                "init",
            )
            tasks = self._item(
                f"Tasks  ({len(project.tasks)})",
                "tasks",
                project.id,
                "tasks",
            )
            root.addChildren([roadmap, init, tasks])
            for task in project.tasks:
                task_item = self._item(
                    f"{task.title}  [{task.status.value}]",
                    "task",
                    project.id,
                    task.id,
                )
                task_item.setToolTip(0, task.original_prompt)
                tasks.addChild(task_item)
                if self._selected_key == (
                    project.id,
                    "task",
                    task.id,
                ):
                    selected_item = task_item
            new_task = self._item(
                "+ New Task",
                "new_task",
                project.id,
                "new_task",
            )
            tasks.addChild(new_task)

            should_expand = (
                project.id in expanded
                or not expanded
                or project.id == selected_id
            )
            root.setExpanded(should_expand)
            tasks.setExpanded(should_expand)
            if self._selected_key == (
                project.id,
                "roadmap",
                "roadmap",
            ):
                selected_item = roadmap
            elif self._selected_key == (
                project.id,
                "init",
                "init",
            ):
                selected_item = init
            elif self._selected_key == (
                project.id,
                "project",
                project.id,
            ):
                selected_item = root
            elif selected_id == project.id and self._selected_key is None:
                selected_item = root

        if selected_item is not None:
            self.tree.setCurrentItem(selected_item)

    def select_item(
        self, project_id: str, kind: str, item_id: str = ""
    ) -> None:
        self._selected_key = (project_id, kind, item_id or kind)

    def _item(
        self, text: str, kind: str, project_id: str, item_id: str
    ) -> QTreeWidgetItem:
        item = QTreeWidgetItem([text])
        item.setData(0, ITEM_KIND_ROLE, kind)
        item.setData(0, PROJECT_ID_ROLE, project_id)
        item.setData(0, ITEM_ID_ROLE, item_id)
        return item

    def _item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        kind = str(item.data(0, ITEM_KIND_ROLE) or "")
        project_id = str(item.data(0, PROJECT_ID_ROLE) or "")
        item_id = str(item.data(0, ITEM_ID_ROLE) or "")
        if not project_id:
            return
        if kind == "new_task":
            self.new_task_requested.emit(project_id)
            return
        self._selected_key = (project_id, kind, item_id)
        self.navigation_selected.emit(project_id, kind, item_id)
        if kind == "project":
            self.project_selected.emit(project_id)
        elif kind == "task":
            self.task_selected.emit(item_id)
