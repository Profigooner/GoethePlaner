from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from agentboard.app.core.task_manager import WorkflowWorker
from agentboard.app.models import DraftStatus, Project, Task, TaskStatus
from agentboard.app.ui.dialogs import NewProjectDialog, NewTaskDialog
from agentboard.app.ui.main_window import MainWindow
from agentboard.app.ui.project_dialogs import InitDialog, RoadmapDialog
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

        self.assertEqual(window.windowTitle(), "GoethePlaner")
        self.assertEqual(window.dashboard.mode_combo.count(), 3)
        self.assertEqual(window.dashboard.agent_cards, {})
        self.assertFalse(window.dashboard.accept_button.isEnabled())
        self.assertEqual(window.projects, [])
        self.assertEqual(
            window.dashboard.generate_roadmap_button.text(),
            "Create Roadmap",
        )
        self.assertEqual(
            window.dashboard.generate_init_button.text(),
            "Run Init Agent",
        )
        logo = window.dashboard.sidebar.logo_label.pixmap()
        self.assertIsNotNone(logo)
        self.assertFalse(logo.isNull())
        window.close()

    def test_creation_dialogs_expose_typed_values(self) -> None:
        project_dialog = NewProjectDialog()
        project_dialog.name_edit.setText("Demo")
        project_dialog.repository_edit.setText(str(Path.cwd()))
        task_dialog = NewTaskDialog("Demo")
        task_dialog.title_edit.setText("Add export")
        task_dialog.prompt_edit.setPlainText("Implement JSON export.")
        task_dialog.mode_combo.setCurrentIndex(1)

        self.assertEqual(project_dialog.project_name, "Demo")
        self.assertEqual(project_dialog.repository, Path.cwd().resolve())
        self.assertEqual(task_dialog.task_title, "Add export")
        self.assertEqual(task_dialog.prompt, "Implement JSON export.")
        self.assertEqual(task_dialog.mode, "mock")

        project_dialog.close()
        task_dialog.close()

    def test_plan_step_recommends_specialized_agents(self) -> None:
        dialog = NewTaskDialog("Demo", "demo")
        dialog.title_edit.setText("Fix login")
        dialog.prompt_edit.setPlainText(
            "Fix a login bug in my Node.js backend and add tests."
        )

        dialog._plan("demo")

        self.assertIn("planner", dialog.selected_agents)
        self.assertIn("nodejs_expert", dialog.selected_agents)
        self.assertIn("backend_engineer", dialog.selected_agents)
        self.assertIn("bug_tracker", dialog.selected_agents)
        self.assertIn("test_engineer", dialog.selected_agents)
        self.assertIn("code_reviewer", dialog.selected_agents)
        self.assertTrue(dialog.optimized_prompt)
        self.assertTrue(dialog.planner_notes)
        self.assertGreaterEqual(len(dialog.execution_graph), 4)

        dialog.close()

    def test_main_window_mock_run_populates_project_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            subprocess.run(
                ["git", "init", "-q"], cwd=repository, check=True
            )
            window = MainWindow(AppConfig(mock_step_delay=0))
            window.start_task(
                repository,
                "Add a task export.",
                "mock",
                title="Task export",
            )
            self.assertIsNotNone(window.workflow_thread)
            loop = QEventLoop()
            window.workflow_thread.finished.connect(loop.quit)
            QTimer.singleShot(5_000, loop.quit)
            loop.exec()
            self.app.processEvents()

            self.assertEqual(len(window.projects), 1)
            self.assertEqual(window.projects[0].name, repository.name)
            self.assertEqual(len(window.projects[0].tasks), 1)
            self.assertEqual(window.current_task.status, TaskStatus.COMPLETED)
            self.assertEqual(len(window.dashboard.agent_cards), 6)
            self.assertEqual(len(window.dashboard.task_cards), 1)
            self.assertTrue(window.dashboard.accept_button.isEnabled())
            self.assertEqual(
                {
                    suggestion.target
                    for suggestion in window.projects[0].pending_suggestions
                },
                {"roadmap", "init"},
            )
            self.assertTrue(window.current_task.completion_summary)

            window.close()

    def test_project_agent_dialogs_create_reviewable_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "README.md").write_text("# Demo\nA Python tool.\n")
            (repository / "pyproject.toml").write_text("[project]\n")
            project = Project(
                "Demo", repository, goal="Build a reliable Python tool."
            )
            roadmap = RoadmapDialog(
                project, AppConfig(mock_step_delay=0)
            )
            roadmap.mode_combo.setCurrentIndex(1)
            roadmap._generate()
            self.assertIsNotNone(roadmap.worker_thread)
            roadmap_loop = QEventLoop()
            roadmap.worker_thread.finished.connect(roadmap_loop.quit)
            QTimer.singleShot(5_000, roadmap_loop.quit)
            roadmap_loop.exec()
            self.app.processEvents()

            self.assertIsNotNone(project.roadmap_draft)
            self.assertEqual(project.roadmap, "")
            self.assertEqual(
                project.roadmap_draft.status, DraftStatus.DRAFT
            )
            roadmap._accept_draft()
            self.assertIn("Roadmap Draft", project.roadmap)
            self.assertTrue(roadmap.ask_button.isEnabled())
            self.assertEqual(roadmap.ask_button.text(), "Create Revision")

            before = sorted(path.name for path in repository.iterdir())
            init = InitDialog(project, AppConfig(mock_step_delay=0))
            init.mode_combo.setCurrentIndex(1)
            init._generate()
            self.assertIsNotNone(init.worker_thread)
            init_loop = QEventLoop()
            init.worker_thread.finished.connect(init_loop.quit)
            QTimer.singleShot(5_000, init_loop.quit)
            init_loop.exec()
            self.app.processEvents()

            after = sorted(path.name for path in repository.iterdir())
            self.assertEqual(before, after)
            self.assertIsNotNone(project.init_draft)
            self.assertIn(
                "AGENTS.md",
                {
                    proposal.path
                    for proposal in project.init_draft.proposed_files
                },
            )

            roadmap.close()
            init.close()


if __name__ == "__main__":
    unittest.main()
