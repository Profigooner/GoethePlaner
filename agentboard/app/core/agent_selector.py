from __future__ import annotations

import re
from dataclasses import dataclass

from .agent_registry import AgentRegistry, DEFAULT_AGENT_REGISTRY


@dataclass(frozen=True, slots=True)
class AgentSelectionResult:
    selected_agents: tuple[str, ...]
    optional_agents: tuple[str, ...]
    risky_agents: tuple[str, ...]
    reasons: dict[str, str]
    reason: str
    planner_notes: str


class AgentSelector:
    def __init__(
        self, registry: AgentRegistry = DEFAULT_AGENT_REGISTRY
    ) -> None:
        self.registry = registry

    def select(self, prompt: str, title: str = "") -> AgentSelectionResult:
        text = self._normalize(f"{title}\n{prompt}")
        selected = {"planner", "prompt_optimizer"}
        reasons = {
            "planner": "Planner is required to define dependencies and execution order.",
            "prompt_optimizer": (
                "Prompt Optimizer clarifies constraints and completion criteria."
            ),
        }
        for definition in self.registry.all():
            if definition.id in selected:
                continue
            matches = [
                keyword
                for keyword in definition.keywords
                if self._contains(text, keyword)
            ]
            if matches:
                selected.add(definition.id)
                reasons[definition.id] = (
                    f"Matched task signals: {', '.join(matches[:4])}."
                )

        self._apply_domain_rules(text, selected, reasons)

        implementation = {
            item.id
            for item in self.registry.all()
            if item.can_modify_code
            and item.id
            not in {
                "test_engineer",
                "documentation_writer",
            }
        }
        if selected & implementation:
            selected.update({"test_engineer", "code_reviewer"})
            reasons.setdefault(
                "test_engineer",
                "Implementation work requires focused regression verification.",
            )
            reasons.setdefault(
                "code_reviewer",
                "Implementation work requires a final correctness and safety review.",
            )

        if selected == {"planner", "prompt_optimizer"}:
            selected.update(
                {"software_architect", "test_engineer", "code_reviewer"}
            )
            reasons["software_architect"] = (
                "No narrow domain matched, so architecture analysis is the "
                "safest general implementation starting point."
            )
            reasons["test_engineer"] = "General implementation work needs tests."
            reasons["code_reviewer"] = "General implementation work needs review."

        ordered = tuple(
            item.id for item in self.registry.all() if item.id in selected
        )
        optional = tuple(
            item.id
            for item in self.registry.all()
            if item.id not in selected and item.risk_level != "high"
        )
        risky = tuple(
            item.id
            for item in self.registry.all()
            if item.id not in selected and item.risk_level == "high"
        )
        labels = [self.registry.get(item).display_name for item in ordered]
        reason = (
            "The planner selected "
            + ", ".join(labels)
            + " based on task domain, implementation, verification, and review needs."
        )
        notes = self._planner_notes(ordered, reasons)
        return AgentSelectionResult(
            selected_agents=ordered,
            optional_agents=optional,
            risky_agents=risky,
            reasons=reasons,
            reason=reason,
            planner_notes=notes,
        )

    def _apply_domain_rules(
        self, text: str, selected: set[str], reasons: dict[str, str]
    ) -> None:
        if self._any(text, ("node.js", "nodejs", "express", "nestjs", "npm")):
            self._add(
                selected,
                reasons,
                ("nodejs_expert", "backend_engineer"),
                "Node.js server work needs runtime and backend expertise.",
            )
        if self._any(text, ("bug", "fix", "broken", "crash", "regression")):
            self._add(
                selected,
                reasons,
                ("bug_tracker",),
                "The task describes a defect that should be reproduced and isolated.",
            )
        if self._any(text, ("csv", "sales data", "analytics", "anomaly")):
            self._add(
                selected,
                reasons,
                ("data_analytics",),
                "The task requires structured data analysis or anomaly logic.",
            )
        if "dashboard" in text and self._any(
            text, ("data", "csv", "metric", "chart", "visual")
        ):
            self._add(
                selected,
                reasons,
                ("frontend_engineer",),
                "The requested data dashboard needs a user-facing visualization layer.",
            )
        if self._any(
            text,
            (
                "machine learning",
                "pytorch",
                "tensorflow",
                "sklearn",
                "training",
                "inference",
            ),
        ):
            self._add(
                selected,
                reasons,
                ("ml_engineer", "python_expert"),
                "Machine-learning work needs ML pipeline and Python expertise.",
            )
        if self._any(
            text,
            (
                "security",
                "vulnerability",
                "owasp",
                "authentication",
                "permission",
            ),
        ):
            self._add(
                selected,
                reasons,
                ("cyber_security", "backend_engineer"),
                "Security-sensitive application work needs defensive and backend review.",
            )

    @staticmethod
    def _add(
        selected: set[str],
        reasons: dict[str, str],
        agent_ids: tuple[str, ...],
        reason: str,
    ) -> None:
        for agent_id in agent_ids:
            selected.add(agent_id)
            reasons.setdefault(agent_id, reason)

    def _planner_notes(
        self, selected: tuple[str, ...], reasons: dict[str, str]
    ) -> str:
        lines = ["Planner recommendation:"]
        for agent_id in selected:
            definition = self.registry.get(agent_id)
            lines.append(
                f"- {definition.display_name}: {reasons.get(agent_id, definition.description)}"
            )
        lines.append(
            "- Execution order: prompt optimization, planning, parallel "
            "implementation, tests, review, documentation, final summary."
        )
        return "\n".join(lines)

    @staticmethod
    def _normalize(value: str) -> str:
        return re.sub(r"\s+", " ", value.casefold()).strip()

    @staticmethod
    def _contains(text: str, keyword: str) -> bool:
        keyword = keyword.casefold()
        if " " in keyword or "." in keyword:
            return keyword in text
        return re.search(rf"\b{re.escape(keyword)}\b", text) is not None

    @classmethod
    def _any(cls, text: str, keywords: tuple[str, ...]) -> bool:
        return any(cls._contains(text, keyword) for keyword in keywords)
