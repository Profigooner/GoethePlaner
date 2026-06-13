from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from agentboard.app.models import AgentRole, AgentState, AgentStatus

from .components import ProgressPill, StatusBadge
from .theme import THEME, rgba


_ROLE_META = {
    AgentRole.PROMPT_OPTIMIZER: ("✦", "Prompt refinement", THEME.violet),
    AgentRole.PLANNER: ("≡", "Task planning", THEME.violet),
    AgentRole.BACKEND: ("</>", "Backend developer", THEME.accent),
    AgentRole.FRONTEND: ("▣", "Frontend developer", THEME.accent),
    AgentRole.TESTER: ("△", "QA engineer", THEME.warning),
    AgentRole.REVIEWER: ("◇", "Code reviewer", THEME.violet),
}


class AgentCard(QFrame):
    def __init__(self, agent: AgentState, parent=None) -> None:
        super().__init__(parent)
        self.agent_id = agent.id
        self.agent = replace(agent)
        self.setObjectName("agentCard")
        self.setMinimumHeight(178)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedSize(38, 38)
        self.name_label = QLabel()
        self.name_label.setStyleSheet("font-size: 14px; font-weight: 650;")
        self.role_label = QLabel()
        self.role_label.setObjectName("mutedText")
        self.status_badge = StatusBadge()
        self.progress = ProgressPill()
        self.activity_caption = QLabel("Current activity")
        self.activity_caption.setObjectName("mutedText")
        self.message_label = QLabel()
        self.message_label.setObjectName("secondaryText")
        self.message_label.setWordWrap(True)
        self.message_label.setMaximumHeight(36)
        self.log_preview = QLabel()
        self.log_preview.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.log_preview.setWordWrap(True)
        self.log_preview.setMinimumHeight(45)
        self.log_preview.setStyleSheet(
            f"background-color: {THEME.console};"
            f"border: 1px solid {THEME.border};"
            "border-radius: 6px; padding: 6px 8px;"
            f"color: {THEME.text_secondary};"
            "font-family: Menlo, monospace; font-size: 10px;"
        )
        self.elapsed_label = QLabel()
        self.elapsed_label.setObjectName("mutedText")
        self.result_label = QLabel()
        self.result_label.setObjectName("mutedText")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        identity = QVBoxLayout()
        identity.setSpacing(1)
        identity.addWidget(self.name_label)
        identity.addWidget(self.role_label)
        header = QHBoxLayout()
        header.setSpacing(9)
        header.addWidget(self.icon_label)
        header.addLayout(identity)
        header.addStretch()
        header.addWidget(self.status_badge, alignment=Qt.AlignmentFlag.AlignTop)

        footer = QHBoxLayout()
        footer.addWidget(self.elapsed_label)
        footer.addStretch()
        footer.addWidget(self.result_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 10, 11, 9)
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self.progress)
        layout.addWidget(self.activity_caption)
        layout.addWidget(self.message_label)
        layout.addWidget(self.log_preview)
        layout.addLayout(footer)

        self.timer = QTimer(self)
        self.timer.setInterval(1_000)
        self.timer.timeout.connect(self._update_elapsed)
        self.timer.start()
        self.update_agent(agent)

    def update_agent(self, agent: AgentState) -> None:
        self.agent = replace(agent)
        icon, role_name, color = _ROLE_META[agent.role]
        self.icon_label.setText(icon)
        self.icon_label.setStyleSheet(
            f"background-color: {rgba(color, 42)};"
            f"border: 1px solid {rgba(color, 80)};"
            f"color: {color}; border-radius: 8px;"
            "font-size: 15px; font-weight: 700;"
        )
        self.name_label.setText(agent.role.value)
        self.role_label.setText(role_name)
        self.status_badge.set_status(agent.status)
        self.progress.setValue(agent.progress)
        self.progress.set_color(self._progress_color(agent.status, color))
        self.message_label.setText(agent.current_message or "Waiting to start")
        preview = agent.logs[-2:]
        self.log_preview.setText(
            "\n".join(f"—  {line}" for line in preview)
            if preview
            else "—  Waiting to start…\n—  …"
        )
        self.result_label.setText(agent.result)
        self.result_label.setVisible(bool(agent.result))
        self._update_elapsed()
        self._apply_style(agent.status)

    def _update_elapsed(self) -> None:
        seconds = self.agent.elapsed_seconds
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.elapsed_label.setText(f"◷  {hours:02d}:{minutes:02d}:{seconds:02d}")

    def _apply_style(self, status: AgentStatus) -> None:
        border = (
            THEME.border_strong
            if status == AgentStatus.RUNNING
            else THEME.border
        )
        background = (
            rgba(THEME.accent, 15)
            if status == AgentStatus.RUNNING
            else THEME.panel_alt
        )
        self.setStyleSheet(
            "QFrame#agentCard {"
            f"background-color: {background};"
            f"border: 1px solid {border};"
            "border-radius: 10px;"
            "}"
            "QFrame#agentCard:hover {"
            f"background-color: {THEME.panel_hover};"
            f"border-color: {THEME.border_strong};"
            "}"
            "QFrame#agentCard QLabel { background: transparent; border: none; }"
        )

    @staticmethod
    def _progress_color(status: AgentStatus, role_color: str) -> str:
        if status == AgentStatus.DONE:
            return THEME.success
        if status == AgentStatus.FAILED:
            return THEME.error
        if status == AgentStatus.CANCELLED:
            return THEME.warning
        return role_color

