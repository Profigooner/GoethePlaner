from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from agentboard.app.models import Task

from .components import ProgressPill, StatusBadge
from .theme import THEME, rgba


class TaskCard(QFrame):
    clicked = Signal(str)

    def __init__(self, task: Task, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("taskCard")
        self.task_id = task.id
        self.selected = False
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 650;")
        self.title_label.setWordWrap(True)
        self.status_badge = StatusBadge()
        self.updated_label = QLabel()
        self.updated_label.setObjectName("mutedText")
        self.summary_label = QLabel()
        self.summary_label.setObjectName("secondaryText")
        self.summary_label.setWordWrap(True)
        self.summary_label.setMaximumHeight(40)
        self.progress = ProgressPill()
        self.agent_label = QLabel()
        self.agent_label.setObjectName("mutedText")

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self.title_label, 1)
        header.addWidget(self.status_badge)
        metadata = QHBoxLayout()
        metadata.addWidget(self.updated_label)
        metadata.addStretch()
        metadata.addWidget(self.agent_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 11, 12, 11)
        layout.setSpacing(8)
        layout.addLayout(header)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.progress)
        layout.addLayout(metadata)
        self.update_task(task)

    def update_task(self, task: Task) -> None:
        self.title_label.setText(task.title)
        self.status_badge.set_status(task.status)
        summary = " ".join(task.original_prompt.split())
        self.summary_label.setText(
            summary if len(summary) <= 112 else f"{summary[:109]}…"
        )
        self.progress.setValue(task.overall_progress)
        self.updated_label.setText(self._relative_time(task.updated_at))
        self.agent_label.setText(f"◌  {len(task.agents) or 6} agents")
        self._apply_style()

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self._apply_style()

    def _apply_style(self) -> None:
        background = (
            rgba(THEME.accent, 18) if self.selected else THEME.panel_alt
        )
        border = THEME.accent if self.selected else THEME.border
        self.setStyleSheet(
            "QFrame#taskCard {"
            f"background-color: {background};"
            f"border: 1px solid {border};"
            "border-radius: 10px;"
            "}"
            "QFrame#taskCard:hover {"
            f"background-color: {THEME.panel_hover};"
            f"border-color: {THEME.border_strong};"
            "}"
            "QFrame#taskCard QLabel { background: transparent; border: none; }"
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.task_id)
        super().mousePressEvent(event)

    @staticmethod
    def _relative_time(value: datetime) -> str:
        seconds = max(
            0,
            int((datetime.now(timezone.utc) - value).total_seconds()),
        )
        if seconds < 60:
            return "Updated now"
        if seconds < 3600:
            return f"Updated {seconds // 60}m ago"
        if seconds < 86_400:
            return f"Updated {seconds // 3600}h ago"
        return f"Updated {seconds // 86_400}d ago"
