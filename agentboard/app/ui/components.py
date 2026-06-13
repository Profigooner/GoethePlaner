from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from agentboard.app.models import AgentStatus, TaskStatus

from .theme import THEME, rgba


_STATUS_COLORS = {
    "Draft": THEME.text_muted,
    "Optimizing": THEME.violet,
    "Planning": THEME.violet,
    "Running": THEME.accent,
    "Reviewing": THEME.violet,
    "Completed": THEME.success,
    "Done": THEME.success,
    "Accepted": THEME.success,
    "Waiting": THEME.warning,
    "Failed": THEME.error,
    "Rejected": THEME.error,
    "Cancelled": THEME.warning,
    "Active": THEME.success,
    "Idle": THEME.text_muted,
}


class GlassPanel(QFrame):
    def __init__(self, object_name: str = "glassPanel", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)


class StatusBadge(QLabel):
    def __init__(self, status: str = "Idle", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statusBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_status(status)

    def set_status(
        self, status: str | AgentStatus | TaskStatus, label: str | None = None
    ) -> None:
        value = status.value if hasattr(status, "value") else str(status)
        color = _STATUS_COLORS.get(value, THEME.text_muted)
        self.setText(label or value)
        self.setStyleSheet(
            "QLabel#statusBadge {"
            f"color: {color};"
            f"background-color: {rgba(color, 28)};"
            f"border: 1px solid {rgba(color, 75)};"
            "border-radius: 6px; padding: 3px 7px;"
            "font-size: 11px; font-weight: 650;"
            "}"
        )


class ProgressPill(QFrame):
    def __init__(self, show_value: bool = True, parent=None) -> None:
        super().__init__(parent)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.value_label = QLabel("0%")
        self.value_label.setObjectName("secondaryText")
        self.value_label.setMinimumWidth(38)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.value_label.setVisible(show_value)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)
        layout.addWidget(self.progress_bar, 1)
        layout.addWidget(self.value_label)

    def setValue(self, value: int) -> None:
        value = max(0, min(100, value))
        self.progress_bar.setValue(value)
        self.value_label.setText(f"{value}%")

    def value(self) -> int:
        return self.progress_bar.value()

    def set_color(self, color: str) -> None:
        self.progress_bar.setStyleSheet(
            "QProgressBar {"
            f"background-color: {THEME.panel_hover};"
            "border: none; border-radius: 3px;"
            "min-height: 6px; max-height: 6px;"
            "}"
            "QProgressBar::chunk {"
            f"background-color: {color};"
            "border-radius: 3px;"
            "}"
        )


class EmptyState(QFrame):
    action_requested = Signal()

    def __init__(
        self,
        title: str,
        message: str,
        action_text: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("emptyState")
        self.setStyleSheet(
            "QFrame#emptyState {"
            f"background-color: {rgba(THEME.panel_alt, 120)};"
            f"border: 1px dashed {THEME.border_strong};"
            "border-radius: 12px;"
            "}"
        )
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label = QLabel(message)
        message_label.setObjectName("secondaryText")
        message_label.setWordWrap(True)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setMaximumWidth(420)
        action = QPushButton(action_text)
        action.setObjectName("primaryButton")
        action.clicked.connect(self.action_requested)
        action.setVisible(bool(action_text))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(10)
        layout.addStretch()
        layout.addWidget(title_label)
        layout.addWidget(message_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(6)
        layout.addWidget(action, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()


class NavigationButton(QPushButton):
    def __init__(self, text: str, parent=None) -> None:
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setObjectName("navigationButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "QPushButton#navigationButton {"
            "text-align: left; padding: 10px 12px;"
            "background: transparent; border: 1px solid transparent;"
            f"color: {THEME.text_secondary};"
            "}"
            "QPushButton#navigationButton:hover {"
            f"background-color: {THEME.panel_hover};"
            f"color: {THEME.text_primary};"
            "}"
            "QPushButton#navigationButton:checked {"
            f"background-color: {THEME.panel_alt};"
            f"border-color: {THEME.border};"
            f"color: {THEME.text_primary};"
            "}"
        )

