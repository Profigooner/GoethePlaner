from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from agentboard.app.core.project_analysis import ProjectAnalyzer
from agentboard.app.core.project_updates import ProjectUpdateService
from agentboard.app.models import Project, Task, TaskStatus
from agentboard.app.ui.dialogs import NewProjectDialog
from agentboard.app.ui.sidebar import ProjectSidebar
from agentboard.app.ui.task_dashboard import TaskDashboard
from agentboard.app.ui.workspace_views import RoadmapView


class ProjectLifecycleTests(unittest.TestCase):
    def test_existing_project_analysis_detects_docs_and_stack_without_writes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "README.md").write_text("# Demo\n")
            (repository / "AGENTS.md").write_text("# Agents\n")
            (repository / "ROADMAP.md").write_text("# Roadmap\n")
            (repository / "pyproject.toml").write_text(
                "[project]\ndependencies = ['PySide6']\n"
            )
            before = {
                path.name: path.read_text()
                for path in repository.iterdir()
            }

            analysis = ProjectAnalyzer().analyze(repository)

            after = {
                path.name: path.read_text()
                for path in repository.iterdir()
            }
        self.assertEqual(before, after)
        self.assertIn("README.md", analysis.documentation_files)
        self.assertEqual(analysis.roadmap_path, "ROADMAP.md")
        self.assertIn("Python", analysis.detected_stack)
        self.assertIn("PySide6", analysis.detected_stack)
        self.assertTrue(analysis.has_init_context)

    def test_imported_docs_populate_context_without_rewriting_files(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            roadmap = repository / "ROADMAP.md"
            agents = repository / "AGENTS.md"
            roadmap.write_text("# Existing Roadmap\n")
            agents.write_text("# Existing Agent Context\n")
            project = Project("Demo", repository)
            analysis = ProjectAnalyzer().analyze(repository)

            imported = ProjectAnalyzer().import_existing_documents(
                project, analysis
            )

            self.assertEqual(roadmap.read_text(), "# Existing Roadmap\n")
            self.assertEqual(agents.read_text(), "# Existing Agent Context\n")
        self.assertEqual(project.roadmap_status, "imported")
        self.assertEqual(project.init_status, "imported")
        self.assertEqual(len(imported), 2)

    def test_task_completion_creates_reviewable_unapplied_updates(self) -> None:
        project = Project("Demo", Path("/tmp/demo"))
        project.update_roadmap("# Roadmap\n", "accepted")
        project.update_init("# Init\n", "accepted")
        task = Task(project.repo_path, "Implement export", "Export")
        project.add_task(task)
        task.finish(TaskStatus.COMPLETED)
        roadmap_before = project.roadmap
        init_before = project.init_plan

        roadmap, init = ProjectUpdateService().create_for_completed_task(
            project, task
        )

        self.assertEqual(project.roadmap, roadmap_before)
        self.assertEqual(project.init_plan, init_before)
        self.assertEqual(roadmap.status, "pending")
        self.assertEqual(init.status, "pending")
        self.assertEqual(project.roadmap_status, "needs_update")
        self.assertEqual(project.init_status, "needs_update")

        project.apply_update_suggestion(roadmap.id)
        self.assertIn("Export", project.roadmap)
        self.assertEqual(project.roadmap_status, "updated_after_task")
        self.assertEqual(project.init_plan, init_before)

        project.reject_update_suggestion(init.id)
        self.assertEqual(project.init_plan, init_before)


class ProductUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def test_new_project_dialog_distinguishes_existing_and_new(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dialog = NewProjectDialog()
            self.assertEqual(dialog.project_type, "existing")
            dialog.project_type_combo.setCurrentIndex(1)
            dialog.name_edit.setText("Fresh")
            dialog.repository_edit.setText(directory)
            dialog.goal_edit.setPlainText("Build a fresh project")

            self.assertEqual(dialog.project_type, "new")
            self.assertEqual(
                dialog.repository,
                Path(directory).resolve() / "Fresh",
            )
            self.assertTrue(dialog.create_missing_roadmap)
            self.assertTrue(dialog.run_missing_init)
            dialog.close()

    def test_project_tree_contains_first_class_resources_and_tasks(self) -> None:
        project = Project("Demo", Path("/tmp/demo"))
        task = Task(project.repo_path, "Fix login", "Fix login")
        project.add_task(task)
        sidebar = ProjectSidebar()

        sidebar.set_projects([project], project.id)

        root = sidebar.tree.topLevelItem(0)
        self.assertEqual(root.text(0), "Demo")
        self.assertTrue(root.text(0))
        self.assertTrue(root.child(0).text(0).startswith("Roadmap"))
        self.assertTrue(root.child(1).text(0).startswith("Init"))
        tasks = root.child(2)
        self.assertTrue(tasks.text(0).startswith("Tasks"))
        self.assertIn("Fix login", tasks.child(0).text(0))
        self.assertEqual(tasks.child(1).text(0), "+ New Task")
        sidebar.close()

    def test_bottom_tools_toggle_and_only_one_is_open(self) -> None:
        dashboard = TaskDashboard()
        dashboard.show()
        self.app.processEvents()

        dashboard.toggle_bottom_tool("Logs")
        self.app.processEvents()
        self.assertEqual(dashboard.bottom_tool_window.current_tool, "Logs")
        self.assertTrue(dashboard.bottom_tool_window.isVisible())

        dashboard.toggle_bottom_tool("Prompt")
        self.app.processEvents()
        self.assertEqual(dashboard.bottom_tool_window.current_tool, "Prompt")
        self.assertFalse(
            dashboard.bottom_tool_bar.buttons["Logs"].isChecked()
        )
        self.assertTrue(
            dashboard.bottom_tool_bar.buttons["Prompt"].isChecked()
        )

        dashboard.toggle_bottom_tool("Prompt")
        self.app.processEvents()
        self.assertIsNone(dashboard.bottom_tool_window.current_tool)
        self.assertFalse(dashboard.bottom_tool_window.isVisible())
        dashboard.close()

    def test_diff_review_and_separate_task_rail_are_removed(self) -> None:
        dashboard = TaskDashboard()

        self.assertFalse(hasattr(dashboard, "inspector_tabs"))
        self.assertFalse(hasattr(dashboard, "diff_viewer"))
        self.assertFalse(hasattr(dashboard, "review_title"))
        self.assertFalse(hasattr(dashboard, "task_rail"))
        dashboard.close()

    def test_roadmap_can_be_modified_and_item_becomes_task_seed(self) -> None:
        project = Project("Demo", Path("/tmp/demo"))
        project.update_roadmap(
            "# Roadmap\n\n- [ ] Add export support\n",
            "accepted",
        )
        view = RoadmapView()
        emitted: list[str] = []
        task_seeds: list[str] = []
        view.content_saved.connect(emitted.append)
        view.create_task_requested.connect(task_seeds.append)
        view.set_project(project)
        view.editor.find("Add export support")

        view._mark_current_line_complete()
        view.editor.find("Add export support")
        view._create_task()

        self.assertIn("- [x] Add export support", emitted[-1])
        self.assertEqual(task_seeds, ["Add export support"])
        view.close()


if __name__ == "__main__":
    unittest.main()
