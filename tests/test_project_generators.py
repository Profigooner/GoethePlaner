from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from threading import Event
from unittest.mock import patch

from agentboard.app.core.init_generator import (
    InitGenerator,
    export_init_draft,
)
from agentboard.app.core.opencode_runner import (
    AgentRunResult,
    MockOpenCodeRunner,
    OpenCodeRunner,
)
from agentboard.app.core.project_agents import (
    build_init_prompt,
    build_roadmap_prompt,
)
from agentboard.app.core.roadmap_generator import (
    RoadmapGenerator,
    export_accepted_roadmap,
)
from agentboard.app.models import (
    DraftStatus,
    Project,
    ProposedFileStatus,
    Task,
)


class ProjectAgentWorkflowTests(unittest.TestCase):
    def test_project_model_separates_drafts_from_accepted_state(self) -> None:
        project = Project("Demo", Path("/tmp/demo"), goal="Build a demo")
        draft = RoadmapGenerator().generate(
            project, "Build a reviewed demo roadmap"
        )

        project.set_roadmap_draft(draft)

        self.assertEqual(draft.status, DraftStatus.DRAFT)
        self.assertEqual(project.roadmap, "")
        project.accept_roadmap_draft(draft)
        self.assertEqual(project.roadmap, draft.draft_content)
        self.assertEqual(draft.status, DraftStatus.ACCEPTED)

    def test_roadmap_draft_uses_user_goal_and_is_not_auto_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Project("Demo", Path(directory))
            draft = RoadmapGenerator().generate(
                project,
                "Ship an accessible desktop planner",
                "Python and PySide6 only",
            )

        self.assertIn("Ship an accessible desktop planner", draft.draft_content)
        self.assertEqual(draft.status, DraftStatus.DRAFT)
        self.assertTrue(draft.repository_observations)
        self.assertTrue(draft.suggested_next_tasks)

    def test_roadmap_feedback_creates_revised_draft_with_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Project("Demo", Path(directory))
            original = RoadmapGenerator().generate(project, "Build a demo")

            revised = RoadmapGenerator().revise(
                project,
                original,
                "Add accessibility and release milestones.",
            )

        self.assertEqual(revised.id, original.id)
        self.assertEqual(
            revised.feedback_history,
            ["Add accessibility and release milestones."],
        )
        self.assertIn("accessibility", revised.draft_content)
        self.assertGreater(revised.updated_at, original.updated_at)

    def test_roadmap_export_requires_acceptance_and_no_silent_overwrite(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            project = Project("Demo", repository)
            draft = RoadmapGenerator().generate(project, "Build a demo")
            target = repository / "ROADMAP.generated.md"

            with self.assertRaises(ValueError):
                export_accepted_roadmap(draft, target)
            draft.accept()
            export_accepted_roadmap(draft, target)
            with self.assertRaises(FileExistsError):
                export_accepted_roadmap(draft, target)

        self.assertNotEqual(target.name, "ROADMAP.md")

    def test_init_draft_proposes_files_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "pyproject.toml").write_text("[project]\n")
            before = sorted(path.name for path in repository.iterdir())
            project = Project("Demo", repository)

            draft = InitGenerator().generate(
                project, "Initialize Python contributor documentation"
            )
            after = sorted(path.name for path in repository.iterdir())

            self.assertEqual(before, after)
            self.assertIn(
                "README.md", {proposal.path for proposal in draft.proposed_files}
            )
            self.assertIn(
                "AGENTS.md", {proposal.path for proposal in draft.proposed_files}
            )
            self.assertEqual(draft.status, DraftStatus.DRAFT)

    def test_apply_selected_writes_only_selected_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            project = Project("Demo", repository)
            draft = InitGenerator().generate(project, "Initialize docs")
            for proposal in draft.proposed_files:
                proposal.selected = proposal.path == "AGENTS.md"

            written = InitGenerator().apply_selected(
                project, draft, confirmed=True
            )

            self.assertEqual(written, ("AGENTS.md",))
            self.assertTrue((repository / "AGENTS.md").is_file())
            self.assertFalse((repository / "README.md").exists())

    def test_existing_init_file_requires_explicit_overwrite_confirmation(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            readme = repository / "README.md"
            readme.write_text("user content\n")
            project = Project("Demo", repository)
            draft = InitGenerator().generate(project, "Improve docs")
            for proposal in draft.proposed_files:
                proposal.selected = proposal.path == "README.md"
                if proposal.path == "README.md":
                    self.assertEqual(
                        proposal.status, ProposedFileStatus.UPDATE
                    )

            with self.assertRaises(PermissionError):
                InitGenerator().apply_selected(project, draft)
            with self.assertRaises(PermissionError):
                InitGenerator().apply_selected(
                    project, draft, confirmed=True
                )

            self.assertEqual(readme.read_text(), "user content\n")

    def test_existing_init_file_detects_changes_after_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            readme = repository / "README.md"
            readme.write_text("original\n")
            project = Project("Demo", repository)
            draft = InitGenerator().generate(project, "Improve docs")
            for proposal in draft.proposed_files:
                proposal.selected = proposal.path == "README.md"
            readme.write_text("changed after review\n")

            with self.assertRaises(FileExistsError):
                InitGenerator().apply_selected(
                    project,
                    draft,
                    confirmed=True,
                    overwrite_paths={"README.md"},
                )

    def test_init_feedback_creates_revised_proposals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Project("Demo", Path(directory))
            original = InitGenerator().generate(project, "Initialize docs")

            revised = InitGenerator().revise(
                project, original, "Add release verification guidance."
            )

        self.assertEqual(revised.id, original.id)
        self.assertEqual(
            revised.feedback_history,
            ["Add release verification guidance."],
        )
        self.assertTrue(
            any(
                "release verification" in proposal.content.casefold()
                for proposal in revised.proposed_files
            )
        )

    def test_prompts_include_repository_context_and_read_only_rules(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory)
            (repository / "README.md").write_text("# Demo\nExisting context.\n")
            (repository / "pyproject.toml").write_text("[project]\n")
            project = Project("Demo", repository)

            roadmap_prompt = build_roadmap_prompt(
                project, "Build it", "No network"
            )
            init_prompt = build_init_prompt(project, "Initialize it")

        self.assertIn(str(repository), roadmap_prompt)
        self.assertIn("Existing README content", roadmap_prompt)
        self.assertIn("strict JSON only", roadmap_prompt)
        self.assertIn("do not modify files", roadmap_prompt.lower())
        self.assertIn("Do not modify files directly", init_prompt)
        self.assertIn("README.md", init_prompt)
        self.assertIn("AGENTS.md", init_prompt)

    def test_mock_mode_produces_realistic_diagnostics_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Project("Demo", Path(directory))
            logs: list[str] = []
            draft = RoadmapGenerator(
                MockOpenCodeRunner(step_delay=0)
            ).generate(
                project,
                "Build a demo",
                on_log=logs.append,
            )
            init = InitGenerator(
                MockOpenCodeRunner(step_delay=0)
            ).generate(project, "Initialize docs")
            export_target = Path(directory) / "INIT.generated.md"

            export_init_draft(init, export_target)

            self.assertGreater(len(logs), 2)
            self.assertIn("Milestones", draft.draft_content)
            self.assertIn("README.md", export_target.read_text())

    def test_real_runner_uses_plan_agent_and_structured_safe_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Project("Demo", Path(directory))
            runner = OpenCodeRunner(
                "opencode run --dir {repo_path} --agent {agent_name} {prompt}"
            )
            captured: dict[str, str] = {}
            payload = json.dumps(
                {
                    "draft_content": "# Roadmap",
                    "reasoning_summary": "Repository-aware plan.",
                    "repository_observations": ["Empty repository."],
                    "suggested_milestones": ["Baseline"],
                    "suggested_next_tasks": ["Add docs"],
                    "risks": ["Unknown stack"],
                    "testing_strategy": ["Add tests"],
                }
            )

            def fake_run(
                agent_name,
                repo_path,
                prompt,
                cancel_event,
                on_log,
                on_progress,
            ):
                captured["agent"] = agent_name
                captured["prompt"] = prompt
                self.assertIsInstance(cancel_event, Event)
                return AgentRunResult(
                    True,
                    0,
                    "ok",
                    command=("opencode", "run"),
                    stdout=payload,
                )

            with patch.object(runner, "run_agent", side_effect=fake_run):
                draft = runner.run_roadmap_agent(project, "Build a demo")

        self.assertEqual(captured["agent"], "plan")
        self.assertIn("Do not modify files", captured["prompt"])
        self.assertEqual(draft.command, ("opencode", "run"))
        self.assertEqual(draft.draft_content, "# Roadmap")

    def test_existing_project_task_fields_remain_compatible(self) -> None:
        project = Project("Demo", Path("/tmp/demo"), goal="Build a demo")
        task = Task(project.repo_path, "Build it", "Build it")
        task.planner_notes = "Use Python."
        task.selected_agents = ["planner", "python_expert"]
        project.add_task(task)

        self.assertEqual(task.selected_agents[-1], "python_expert")
        self.assertEqual(task.planner_notes, "Use Python.")


if __name__ == "__main__":
    unittest.main()
