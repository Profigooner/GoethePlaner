from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from agentboard.app.models import AgentState, AgentStatus


_STATUS_COLORS = {
    AgentStatus.WAITING: "#64748b",
    AgentStatus.RUNNING: "#2563eb",
    AgentStatus.DONE: "#15803d",
    AgentStatus.FAILED: "#b91c1c",
    AgentStatus.CANCELLED: "#a16207",
}


class AgentCard(QFrame):
    def __init__(self, agent: AgentState, parent=None) -> None:
        super().__init__(parent)
        self.agent_id = agent.id
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("agentCard")

        self.name_label = QLabel(agent.name)
        self.name_label.setStyleSheet("font-weight: 600;")
        self.status_label = QLabel()
        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self.message_label = QLabel()
        self.message_label.setWordWrap(True)
        self.message_label.setStyleSheet("color: #64748b;")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        header = QHBoxLayout()
        header.addWidget(self.name_label)
        header.addStretch()
        header.addWidget(self.status_label)

        layout = QVBoxLayout(self)
        layout.addLayout(header)
        layout.addWidget(self.message_label)
        layout.addWidget(self.progress_bar)

        self.update_agent(agent)

    def update_agent(self, agent: AgentState) -> None:
        self.name_label.setText(agent.name)
        self.status_label.setText(agent.status.value)
        self.status_label.setStyleSheet(
            f"font-weight: 600; color: {_STATUS_COLORS[agent.status]};"
        )
        self.message_label.setText(agent.current_message or "Waiting to start")
        self.progress_bar.setValue(agent.progress)

