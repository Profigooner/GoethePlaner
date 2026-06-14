from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from agentboard.app.core.agent_registry import (
    AgentDefinition,
    AgentRegistry,
    DEFAULT_AGENT_REGISTRY,
)
from agentboard.app.core.agent_selector import AgentSelectionResult

from .components import StatusBadge
from .theme import THEME, rgba


class AgentOptionRow(QFrame):
    def __init__(
        self,
        definition: AgentDefinition,
        *,
        checked: bool,
        reason: str,
        mandatory: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.definition = definition
        self.setObjectName("agentOptionRow")
        self.setStyleSheet(
            "QFrame#agentOptionRow {"
            f"background-color: {THEME.panel_alt};"
            f"border: 1px solid {THEME.border};"
            "border-radius: 9px;"
            "}"
            "QFrame#agentOptionRow:hover {"
            f"background-color: {THEME.panel_hover};"
            f"border-color: {THEME.border_strong};"
            "}"
            "QFrame#agentOptionRow QLabel, "
            "QFrame#agentOptionRow QCheckBox {"
            "background: transparent; border: none;"
            "}"
        )
        self.checkbox = QCheckBox(definition.display_name)
        self.checkbox.setChecked(checked)
        self.checkbox.setEnabled(not mandatory)
        self.checkbox.setStyleSheet("font-weight: 650;")
        category = QLabel(definition.category)
        category.setObjectName("mutedText")
        risk = StatusBadge(
            definition.risk_level.title(),
        )
        risk_color = {
            "low": THEME.success,
            "medium": THEME.warning,
            "high": THEME.error,
        }[definition.risk_level]
        risk.setStyleSheet(
            f"color: {risk_color};"
            f"background-color: {rgba(risk_color, 25)};"
            f"border: 1px solid {rgba(risk_color, 70)};"
            "border-radius: 6px; padding: 3px 7px;"
            "font-size: 11px; font-weight: 650;"
        )
        permissions = QLabel(
            "Modify code: "
            + ("Yes" if definition.can_modify_code else "No")
            + "  ·  Commands: "
            + ("Yes" if definition.can_run_commands else "No")
        )
        permissions.setObjectName("secondaryText")
        reason_label = QLabel(reason or definition.description)
        reason_label.setObjectName("mutedText")
        reason_label.setWordWrap(True)

        header = QHBoxLayout()
        header.addWidget(self.checkbox)
        header.addWidget(category)
        header.addStretch()
        header.addWidget(risk)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        layout.addLayout(header)
        layout.addWidget(permissions)
        layout.addWidget(reason_label)

    @property
    def selected(self) -> bool:
        return self.checkbox.isChecked()


class AgentSelectionPanel(QWidget):
    def __init__(
        self,
        registry: AgentRegistry = DEFAULT_AGENT_REGISTRY,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.registry = registry
        self.rows: dict[str, AgentOptionRow] = {}
        self.section_widgets: list[QWidget] = []
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.content_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.content)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def set_selection(self, result: AgentSelectionResult) -> None:
        for widget in self.section_widgets:
            self.content_layout.removeWidget(widget)
            widget.deleteLater()
        self.section_widgets.clear()
        self.rows.clear()
        selected = set(result.selected_agents)
        sections = (
            ("RECOMMENDED AGENTS", result.selected_agents),
            ("OPTIONAL AGENTS", result.optional_agents),
            ("DISABLED / HIGH RISK", result.risky_agents),
        )
        for label, agent_ids in sections:
            if not agent_ids:
                continue
            heading = QLabel(label)
            heading.setObjectName("sectionLabel")
            self.section_widgets.append(heading)
            self.content_layout.insertWidget(
                max(0, self.content_layout.count() - 1), heading
            )
            for agent_id in agent_ids:
                definition = self.registry.get(agent_id)
                row = AgentOptionRow(
                    definition,
                    checked=agent_id in selected,
                    reason=result.reasons.get(agent_id, definition.description),
                    mandatory=agent_id == "planner",
                )
                self.rows[agent_id] = row
                self.section_widgets.append(row)
                self.content_layout.insertWidget(
                    max(0, self.content_layout.count() - 1), row
                )

    def selected_agents(self) -> list[str]:
        return [
            definition.id
            for definition in self.registry.all()
            if definition.id in self.rows and self.rows[definition.id].selected
        ]
