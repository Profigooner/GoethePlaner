from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from threading import Event

from agentboard.app.core.git_manager import GitManager
from agentboard.app.core.test_runner import TestRunner


class GitManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repository = Path(self.temporary.name)
        self._git("init", "-q")
        self._git("config", "user.name", "AgentBoard Test")
        self._git("config", "user.email", "agentboard@example.invalid")
        (self.repository / "tracked.txt").write_text("initial\n")
        self._git("add", "tracked.txt")
        self._git("commit", "-qm", "initial")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _git(self, *args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=self.repository,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_inspect_lists_worktree_and_untracked_changes(self) -> None:
        (self.repository / "tracked.txt").write_text("changed\n")
        (self.repository / "new file.txt").write_text("new\n")

        state = GitManager(self.repository).inspect()

        self.assertTrue(state.is_git_repository)
        self.assertEqual(len(state.files), 2)
        self.assertIn("tracked.txt", state.diff)
        self.assertIn("new file.txt", state.diff)

    def test_capture_baseline_preserves_dirty_file_content(self) -> None:
        (self.repository / "tracked.txt").write_text("user change\n")

        baseline = GitManager(self.repository).capture_baseline()

        snapshot = baseline.snapshots["tracked.txt"]
        self.assertEqual(snapshot.content, b"user change\n")
        self.assertIn("tracked.txt", baseline.tracked_files)

    def test_reject_restores_baseline_and_archives_new_files(self) -> None:
        other = self.repository / "clean.txt"
        other.write_text("clean\n")
        self._git("add", "clean.txt")
        self._git("commit", "-qm", "add clean file")

        tracked = self.repository / "tracked.txt"
        tracked.write_text("pre-existing user change\n")
        manager = GitManager(self.repository)
        baseline = manager.capture_baseline()

        tracked.write_text("agent overwrite\n")
        other.write_text("agent change\n")
        generated = self.repository / "generated.txt"
        generated.write_text("generated\n")
        archive = self.repository.parent / "archive"

        result = manager.reject_changes(
            baseline, "task-id", archive_root=archive
        )

        self.assertEqual(tracked.read_text(), "pre-existing user change\n")
        self.assertEqual(other.read_text(), "clean\n")
        self.assertFalse(generated.exists())
        self.assertEqual((archive / "generated.txt").read_text(), "generated\n")
        self.assertIn("generated.txt", result.archived_paths)
        remaining = manager.changed_files()
        self.assertEqual([item.path for item in remaining], ["tracked.txt"])


class TestRunnerTests(unittest.TestCase):
    def test_test_runner_streams_output_without_shell(self) -> None:
        output: list[str] = []
        result = TestRunner().run(
            [sys.executable, "-c", "print('test-output')"],
            Path.cwd(),
            Event(),
            output.append,
        )

        self.assertTrue(result.success)
        self.assertEqual(output, ["test-output"])


if __name__ == "__main__":
    unittest.main()
