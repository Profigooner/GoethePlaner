from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from threading import Event, Lock

from agentboard.app.core.agent_dispatcher import StagedAgentDispatcher
from agentboard.app.core.agent_registry import DEFAULT_AGENT_REGISTRY
from agentboard.app.core.opencode_runner import AgentRunResult
from agentboard.app.models import AgentState, AgentStatus


class RecordingRunner:
    def __init__(self) -> None:
        self.lock = Lock()
        self.active = 0
        self.max_active = 0
        self.started: dict[str, float] = {}
        self.finished: dict[str, float] = {}
        self.opencode_names: list[str] = []

    def run_agent(
        self,
        agent_name: str,
        repo_path: Path,
        prompt: str,
        cancel_event: Event,
        on_log,
        on_progress,
    ) -> AgentRunResult:
        role = prompt.splitlines()[0].removeprefix("You are the ").removesuffix(
            " agent in GoethePlaner."
        )
        with self.lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            self.started[role] = time.monotonic()
            self.opencode_names.append(agent_name)
        on_progress(50, "Working")
        on_log(f"{role} running")
        time.sleep(0.03)
        with self.lock:
            self.finished[role] = time.monotonic()
            self.active -= 1
        return AgentRunResult(True, 0, f"{role} complete")


class StagedExecutionTests(unittest.TestCase):
    def test_mock_style_execution_parallelizes_implementation_only(self) -> None:
        selected = [
            "backend_engineer",
            "frontend_engineer",
            "test_engineer",
            "code_reviewer",
        ]
        definitions = [
            DEFAULT_AGENT_REGISTRY.get(agent_id)
            for agent_id in selected
        ]
        agents = [
            AgentState(
                definition.role,
                definition.display_name,
                agent_id=definition.id,
            )
            for definition in definitions
        ]
        runner = RecordingRunner()
        running_events: list[str] = []

        with tempfile.TemporaryDirectory() as directory:
            success = StagedAgentDispatcher(
                runner, parallel_implementation=True
            ).dispatch(
                repository=Path(directory),
                optimized_prompt="Implement the feature.",
                planner_notes="Backend and frontend can run together.",
                definitions=definitions,
                agents=agents,
                cancel_event=Event(),
                on_agent=lambda agent: (
                    running_events.append(agent.agent_id)
                    if agent.status == AgentStatus.RUNNING
                    else None
                ),
                on_log=lambda _source, _message: None,
                on_completion=lambda _completed, _total: None,
            )

        self.assertTrue(success)
        self.assertGreaterEqual(runner.max_active, 2)
        self.assertIn("backend_engineer", running_events)
        self.assertIn("frontend_engineer", running_events)
        implementation_finished = max(
            runner.finished["Backend Engineer"],
            runner.finished["Frontend Engineer"],
        )
        self.assertGreaterEqual(
            runner.started["Test Engineer"], implementation_finished
        )
        self.assertGreaterEqual(
            runner.started["Code Reviewer"],
            runner.finished["Test Engineer"],
        )
        self.assertTrue(
            set(runner.opencode_names).issubset({"plan", "build"})
        )

    def test_real_style_execution_is_sequential(self) -> None:
        definitions = [
            DEFAULT_AGENT_REGISTRY.get("backend_engineer"),
            DEFAULT_AGENT_REGISTRY.get("frontend_engineer"),
        ]
        agents = [
            AgentState(
                definition.role,
                definition.display_name,
                agent_id=definition.id,
            )
            for definition in definitions
        ]
        runner = RecordingRunner()

        with tempfile.TemporaryDirectory() as directory:
            success = StagedAgentDispatcher(
                runner, parallel_implementation=False
            ).dispatch(
                repository=Path(directory),
                optimized_prompt="Implement the feature.",
                planner_notes="Run safely.",
                definitions=definitions,
                agents=agents,
                cancel_event=Event(),
                on_agent=lambda _agent: None,
                on_log=lambda _source, _message: None,
                on_completion=lambda _completed, _total: None,
            )

        self.assertTrue(success)
        self.assertEqual(runner.max_active, 1)


if __name__ == "__main__":
    unittest.main()
