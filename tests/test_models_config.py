from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from agentboard.app.models import (
    AgentRole,
    AgentState,
    AgentStatus,
    Project,
    Task,
)
from agentboard.app.utils.config import AppConfig


class ModelTests(unittest.TestCase):
    def test_progress_is_clamped(self) -> None:
        agent = AgentState(AgentRole.BACKEND, "Backend Agent")
        agent.update(progress=140)
        task = Task(Path("."), "Build it", "Build it")
        task.set_progress(-5)

        self.assertEqual(agent.progress, 100)
        self.assertEqual(task.overall_progress, 0)

    def test_project_owns_tasks_and_reports_active_count(self) -> None:
        project = Project("Demo", Path("/tmp/demo"))
        task = Task(Path("/tmp/other"), "Build it", "Build it")

        project.add_task(task)

        self.assertEqual(task.project_id, project.id)
        self.assertEqual(task.repository, project.repo_path)
        self.assertEqual(project.active_task_count, 1)
        task.finish(task.status.COMPLETED)
        self.assertEqual(project.active_task_count, 0)

    def test_agent_run_fields_capture_logs_and_timing(self) -> None:
        agent = AgentState(AgentRole.BACKEND, "Backend Agent")
        agent.update(status=AgentStatus.RUNNING, message="Working")
        agent.append_log("First line")
        agent.update(status=AgentStatus.DONE)

        self.assertEqual(agent.logs, ["First line"])
        self.assertIsNotNone(agent.started_at)
        self.assertIsNotNone(agent.finished_at)


class ConfigTests(unittest.TestCase):
    def test_environment_configuration_is_parsed_without_a_shell(self) -> None:
        values = {
            "AGENTBOARD_OPENCODE_COMMAND": (
                "custom-code execute --repo {repo_path} {prompt}"
            ),
            "AGENTBOARD_MOCK_DELAY": "0.01",
            "AGENTBOARD_TEST_COMMAND": "python -m unittest",
        }
        with patch.dict(os.environ, values, clear=False):
            config = AppConfig.from_env()

        self.assertEqual(config.mock_step_delay, 0.01)
        self.assertEqual(
            config.test_command, ("python", "-m", "unittest")
        )
        self.assertIn("custom-code", config.opencode_command_template)


if __name__ == "__main__":
    unittest.main()
