from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from agentboard.app.core.task_manager import WorkflowWorker
from agentboard.app.models import Task, TaskStatus
from agentboard.app.ui.main_window import MainWindow
from agentboard.app.utils.config import AppConfig


class WorkflowTests(unittest.TestCase):
    def test_complete_mock_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            subprocess.run(
                ["git", "init", "-q"], cwd=repository, check=True
            )
            task = Task(repository, "Add a task export", "Task export")
            worker = WorkflowWorker(
                task, AppConfig(mock_step_delay=0), "mock"
            )
            completed: list[Task] = []
            baselines: list[object] = []
            states: list[object] = []
            worker.completed.connect(completed.append)
            worker.baseline_ready.connect(baselines.append)
            worker.repository_state_ready.connect(states.append)

            worker.run()

            self.assertEqual(task.status, TaskStatus.COMPLETED)
            self.assertEqual(task.overall_progress, 100)
            self.assertEqual(len(task.agents), 6)
            self.assertEqual(len(task.subtasks), 4)
            self.assertEqual(completed, [task])
            self.assertEqual(len(baselines), 1)
            self.assertEqual(len(states), 1)


class WindowSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_builds_all_primary_controls(self) -> None:
        window = MainWindow(AppConfig())
        window.show()
        self.app.processEvents()

        self.assertEqual(window.windowTitle(), "AgentBoard")
        self.assertEqual(window.dashboard.mode_combo.count(), 3)
        self.assertEqual(window.dashboard.agent_cards, {})
        self.assertFalse(window.dashboard.accept_button.isEnabled())

        window.close()


if __name__ == "__main__":
    unittest.main()

