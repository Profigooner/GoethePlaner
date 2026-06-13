from __future__ import annotations

import unittest
from pathlib import Path
from threading import Event
from unittest.mock import patch

from agentboard.app.core.opencode_runner import (
    MockOpenCodeRunner,
    OpenCodeRunner,
    select_runner,
)
from agentboard.app.core.prompt_optimizer import PromptOptimizer
from agentboard.app.core.task_planner import TaskPlanner
from agentboard.app.models import AgentRole
from agentboard.app.utils.config import AppConfig


class PipelineComponentTests(unittest.TestCase):
    def test_optimizer_adds_context_and_completion_criteria(self) -> None:
        result = PromptOptimizer().optimize("  Add   export support ", "demo")

        self.assertIn("Add export support", result)
        self.assertIn("Repository\ndemo", result)
        self.assertIn("Completion criteria", result)

    def test_planner_assigns_execution_and_review_roles(self) -> None:
        prompt = PromptOptimizer().optimize("Build search", "demo")
        roles = {item.agent_role for item in TaskPlanner().plan(prompt)}

        self.assertEqual(
            roles,
            {
                AgentRole.BACKEND,
                AgentRole.FRONTEND,
                AgentRole.TESTER,
                AgentRole.REVIEWER,
            },
        )

    def test_mock_runner_streams_progress(self) -> None:
        progress: list[int] = []
        logs: list[str] = []
        result = MockOpenCodeRunner(step_delay=0).run_agent(
            "Backend Agent",
            Path("."),
            "Implement it",
            Event(),
            logs.append,
            lambda value, _message: progress.append(value),
        )

        self.assertTrue(result.success)
        self.assertEqual(progress[-1], 100)
        self.assertGreater(len(logs), 2)

    def test_opencode_command_keeps_prompt_in_one_argument(self) -> None:
        runner = OpenCodeRunner(
            "opencode run --dir {repo_path} --agent {agent_name} {prompt}"
        )
        command = runner.build_command(
            "Backend Agent", Path("/tmp/example repo"), "Fix two things"
        )

        self.assertEqual(command[0:2], ["opencode", "run"])
        self.assertIn("/tmp/example repo", command)
        self.assertEqual(command[-1], "Fix two things")

    def test_auto_mode_falls_back_when_opencode_is_unavailable(self) -> None:
        with patch("shutil.which", return_value=None):
            runner, label = select_runner(AppConfig(), "auto")

        self.assertIsInstance(runner, MockOpenCodeRunner)
        self.assertIn("not found", label)

    def test_explicit_opencode_mode_reports_missing_command(self) -> None:
        with patch("shutil.which", return_value=None):
            with self.assertRaises(RuntimeError):
                select_runner(AppConfig(), "opencode")


if __name__ == "__main__":
    unittest.main()
