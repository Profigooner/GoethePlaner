from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentboard.app.core.init_generator import InitGenerator
from agentboard.app.core.project_generation import ProjectGenerationWorker
from agentboard.app.core.roadmap_generator import RoadmapGenerator
from agentboard.app.models import Project, Task


class ProjectGeneratorTests(unittest.TestCase):
    def test_project_model_supports_roadmap_and_init_plan(self) -> None:
        project = Project("Demo", Path("/tmp/demo"), goal="Build a demo")
        project.set_roadmap("# Roadmap", ["Add tests"])
        project.set_init_plan(
            "# Init",
            ["README.md"],
            [".gitignore"],
            ["Review first"],
        )
        task = Task(project.repo_path, "Build it", "Build it")
        task.planner_notes = "Use Python."
        task.selected_agents = ["planner", "python_expert"]
        project.add_task(task)

        self.assertEqual(project.roadmap, "# Roadmap")
        self.assertEqual(project.init_plan, "# Init")
        self.assertEqual(task.selected_agents[-1], "python_expert")
        self.assertEqual(task.planner_notes, "Use Python.")

    def test_generators_are_read_only_and_detect_python(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "README.md").write_text("# Demo\nA data tool.\n")
            (repository / "pyproject.toml").write_text("[project]\n")
            before = sorted(path.name for path in repository.iterdir())
            project = Project("Demo", repository, goal="Analyze data")

            roadmap = RoadmapGenerator().generate(project)
            init = InitGenerator().generate(project)
            after = sorted(path.name for path in repository.iterdir())

            self.assertIn("Python", roadmap.detected_stack)
            self.assertIn("## Suggested Milestones", roadmap.markdown)
            self.assertIn("README.md", init.existing_files)
            self.assertEqual(before, after)

    def test_init_apply_creates_only_missing_selected_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            readme = repository / "README.md"
            readme.write_text("user content\n")
            project = Project("Demo", repository, goal="Build a demo")

            created = InitGenerator().apply_selected(
                project, ["README.md", ".gitignore", "unknown.txt"]
            )

            self.assertEqual(readme.read_text(), "user content\n")
            self.assertEqual(created, (".gitignore",))
            self.assertTrue((repository / ".gitignore").is_file())

    def test_generation_worker_returns_project_scoped_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Project("Demo", Path(directory), goal="Build a demo")
            completed: list[object] = []
            worker = ProjectGenerationWorker(project, "roadmap")
            worker.completed.connect(completed.append)

            worker.run()

            self.assertEqual(len(completed), 1)
            self.assertEqual(completed[0].project_id, project.id)
            self.assertTrue(completed[0].result.suggested_next_tasks)


if __name__ == "__main__":
    unittest.main()
