from __future__ import annotations

import unittest

from agentboard.app.core.agent_registry import (
    DEFAULT_AGENT_REGISTRY,
    SAFE_OPENCODE_AGENTS,
    AgentDefinition,
    safe_opencode_agent,
)
from agentboard.app.core.agent_selector import AgentSelector
from agentboard.app.models import AgentRole


class AgentRegistryTests(unittest.TestCase):
    def test_registry_contains_expected_professional_agents(self) -> None:
        expected = {
            "planner",
            "prompt_optimizer",
            "software_architect",
            "frontend_engineer",
            "backend_engineer",
            "nodejs_expert",
            "python_expert",
            "data_analytics",
            "ml_engineer",
            "cyber_security",
            "system_engineer",
            "database_engineer",
            "devops_engineer",
            "test_engineer",
            "bug_tracker",
            "code_reviewer",
            "documentation_writer",
        }

        self.assertEqual(
            {item.id for item in DEFAULT_AGENT_REGISTRY.all()}, expected
        )

    def test_safe_mapping_never_uses_unconfigured_internal_name(self) -> None:
        unsafe = AgentDefinition(
            id="custom",
            display_name="Custom",
            description="Custom",
            category="Custom",
            default_enabled=False,
            can_modify_code=True,
            can_run_commands=True,
            risk_level="medium",
            keywords=(),
            system_prompt="Custom role.",
            opencode_agent="ml_engineer",
            role=AgentRole.ML_ENGINEER,
        )

        self.assertEqual(safe_opencode_agent(unsafe), "plan")
        self.assertIn(
            safe_opencode_agent(DEFAULT_AGENT_REGISTRY.get("ml_engineer")),
            SAFE_OPENCODE_AGENTS,
        )
        self.assertEqual(
            safe_opencode_agent(unsafe, {"custom": "configured-custom"}),
            "configured-custom",
        )


class AgentSelectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.selector = AgentSelector()

    def test_nodejs_login_bug_selects_backend_bug_and_tests(self) -> None:
        selected = set(
            self.selector.select(
                "Fix a login bug in my Node.js backend."
            ).selected_agents
        )

        self.assertTrue(
            {
                "planner",
                "nodejs_expert",
                "backend_engineer",
                "bug_tracker",
                "test_engineer",
                "code_reviewer",
            }.issubset(selected)
        )

    def test_csv_dashboard_selects_data_analytics(self) -> None:
        selected = set(
            self.selector.select(
                "Add a dashboard that visualizes CSV sales data and detects anomalies."
            ).selected_agents
        )

        self.assertIn("data_analytics", selected)
        self.assertIn("frontend_engineer", selected)

    def test_security_task_selects_cyber_security(self) -> None:
        selected = set(
            self.selector.select(
                "Check this backend app for security vulnerabilities."
            ).selected_agents
        )

        self.assertIn("cyber_security", selected)
        self.assertIn("backend_engineer", selected)

    def test_ml_task_selects_ml_and_python(self) -> None:
        selected = set(
            self.selector.select(
                "Build a PyTorch model training and evaluation pipeline."
            ).selected_agents
        )

        self.assertIn("ml_engineer", selected)
        self.assertIn("python_expert", selected)


if __name__ == "__main__":
    unittest.main()

