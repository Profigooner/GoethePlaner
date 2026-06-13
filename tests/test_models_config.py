from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from agentboard.app.models import AgentRole, AgentState, Task
from agentboard.app.utils.config import AppConfig


class ModelTests(unittest.TestCase):
    def test_progress_is_clamped(self) -> None:
        agent = AgentState(AgentRole.BACKEND, "Backend Agent")
        agent.update(progress=140)
        task = Task(Path("."), "Build it", "Build it")
        task.set_progress(-5)

        self.assertEqual(agent.progress, 100)
        self.assertEqual(task.overall_progress, 0)


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

