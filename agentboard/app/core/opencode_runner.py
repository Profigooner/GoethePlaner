from __future__ import annotations

import queue
import shlex
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable, Protocol

from agentboard.app.models import InitDraft, Project, RoadmapDraft
from agentboard.app.utils.config import AppConfig

from .project_agents import (
    build_init_prompt,
    build_roadmap_prompt,
    mock_init_draft,
    mock_roadmap_draft,
    parse_init_output,
    parse_roadmap_output,
)


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    success: bool
    return_code: int
    summary: str
    cancelled: bool = False
    command: tuple[str, ...] = ()
    stdout: str = ""
    stderr: str = ""


class AgentRunner(Protocol):
    def run_agent(
        self,
        agent_name: str,
        repo_path: Path,
        prompt: str,
        cancel_event: Event,
        on_log: LogCallback,
        on_progress: ProgressCallback,
    ) -> AgentRunResult: ...


class MockOpenCodeRunner:
    def __init__(self, step_delay: float = 0.2) -> None:
        self.step_delay = max(0.0, step_delay)

    def run_agent(
        self,
        agent_name: str,
        repo_path: Path,
        prompt: str,
        cancel_event: Event,
        on_log: LogCallback,
        on_progress: ProgressCallback,
    ) -> AgentRunResult:
        steps = [
            (5, "Reading repository context"),
            (25, "Analyzing the assigned subtask"),
            (50, "Preparing focused changes"),
            (75, "Checking implementation details"),
            (95, "Summarizing the result"),
            (100, "Complete"),
        ]
        on_log(f"Mock mode: {agent_name} started in {repo_path}.")
        on_log(f"Assignment: {prompt}")

        for progress, message in steps:
            if cancel_event.wait(self.step_delay):
                on_log("Cancellation requested; stopping mock agent.")
                return AgentRunResult(
                    success=False,
                    return_code=130,
                    summary="Agent cancelled.",
                    cancelled=True,
                )
            on_progress(progress, message)
            on_log(message)

        return AgentRunResult(
            success=True,
            return_code=0,
            summary=f"{agent_name} completed its mock assignment.",
        )

    def run_roadmap_agent(
        self,
        project: Project,
        goal: str,
        constraints: str = "",
        *,
        target_users: str = "",
        mvp_scope: str = "",
        notes: str = "",
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> RoadmapDraft:
        self._project_steps(
            "Roadmap Agent",
            project.repo_path,
            cancel_event,
            on_log,
            on_progress,
        )
        return mock_roadmap_draft(
            project,
            goal,
            constraints,
            target_users=target_users,
            mvp_scope=mvp_scope,
            notes=notes,
        )

    def revise_roadmap_agent(
        self,
        project: Project,
        previous_draft: RoadmapDraft,
        feedback: str,
        *,
        constraints: str = "",
        target_users: str = "",
        mvp_scope: str = "",
        notes: str = "",
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> RoadmapDraft:
        self._project_steps(
            "Roadmap Revision Agent",
            project.repo_path,
            cancel_event,
            on_log,
            on_progress,
        )
        return mock_roadmap_draft(
            project,
            previous_draft.user_goal,
            constraints,
            target_users=target_users,
            mvp_scope=mvp_scope,
            notes=notes,
            previous_draft=previous_draft,
            feedback=feedback,
        )

    def run_init_agent(
        self,
        project: Project,
        goal: str,
        *,
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> InitDraft:
        self._project_steps(
            "Init Agent",
            project.repo_path,
            cancel_event,
            on_log,
            on_progress,
        )
        return mock_init_draft(project, goal)

    def revise_init_agent(
        self,
        project: Project,
        previous_draft: InitDraft,
        feedback: str,
        *,
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> InitDraft:
        self._project_steps(
            "Init Revision Agent",
            project.repo_path,
            cancel_event,
            on_log,
            on_progress,
        )
        return mock_init_draft(
            project,
            previous_draft.user_goal,
            previous_draft=previous_draft,
            feedback=feedback,
        )

    def _project_steps(
        self,
        label: str,
        repository: Path,
        cancel_event: Event | None,
        on_log: LogCallback | None,
        on_progress: ProgressCallback | None,
    ) -> None:
        cancel = cancel_event or Event()
        log = on_log or (lambda _message: None)
        progress = on_progress or (lambda _value, _message: None)
        log(f"Mock mode: {label} inspecting {repository}.")
        for value, message in (
            (10, "Reading repository structure"),
            (35, "Reviewing project conventions"),
            (65, "Preparing structured draft"),
            (90, "Checking safety boundaries"),
            (100, "Draft ready for review"),
        ):
            if cancel.wait(self.step_delay):
                raise RuntimeError(f"{label} was cancelled.")
            progress(value, message)
            log(message)


class OpenCodeRunner:
    def __init__(self, command_template: str) -> None:
        self.command_template = command_template

    def build_command(
        self, agent_name: str, repo_path: Path, prompt: str
    ) -> list[str]:
        tokens = shlex.split(self.command_template)
        if not tokens:
            raise ValueError("The OpenCode command template is empty.")

        values = {
            "agent_name": agent_name,
            "repo_path": str(repo_path),
            "prompt": prompt,
        }
        try:
            return [token.format_map(values) for token in tokens]
        except KeyError as exc:
            raise ValueError(
                f"Unknown OpenCode command placeholder: {exc.args[0]}"
            ) from exc

    def is_available(self) -> bool:
        try:
            executable = self.build_command(
                "agent", Path.cwd(), "availability check"
            )[0]
        except ValueError:
            return False

        path = Path(executable).expanduser()
        if path.parent != Path("."):
            return path.is_file() and path.stat().st_mode & 0o111 != 0
        return shutil.which(executable) is not None

    def run_agent(
        self,
        agent_name: str,
        repo_path: Path,
        prompt: str,
        cancel_event: Event,
        on_log: LogCallback,
        on_progress: ProgressCallback,
    ) -> AgentRunResult:
        command = self.build_command(agent_name, repo_path, prompt)
        on_log(f"$ {shlex.join(command)}")
        on_log(f"Starting OpenCode agent: {agent_name}")
        on_progress(2, "Starting OpenCode process")

        try:
            process = subprocess.Popen(
                command,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                shell=False,
            )
        except OSError as exc:
            return AgentRunResult(
                success=False,
                return_code=127,
                summary=f"Could not start OpenCode: {exc}",
                command=tuple(command),
                stderr=str(exc),
            )

        output_queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        stdout_reader = threading.Thread(
            target=self._read_output,
            args=(process.stdout, "stdout", output_queue),
            daemon=True,
        )
        stderr_reader = threading.Thread(
            target=self._read_output,
            args=(process.stderr, "stderr", output_queue),
            daemon=True,
        )
        stdout_reader.start()
        stderr_reader.start()
        line_count = 0
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        while (
            process.poll() is None
            or stdout_reader.is_alive()
            or stderr_reader.is_alive()
        ):
            if cancel_event.is_set():
                self._stop_process(process)
                stdout_reader.join(timeout=1)
                stderr_reader.join(timeout=1)
                return AgentRunResult(
                    success=False,
                    return_code=130,
                    summary="OpenCode agent cancelled.",
                    cancelled=True,
                    command=tuple(command),
                    stdout="".join(stdout_lines),
                    stderr="".join(stderr_lines),
                )

            try:
                source, line = output_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if line is None:
                continue
            line_count += 1
            if source == "stdout":
                stdout_lines.append(line)
            else:
                stderr_lines.append(line)
            on_log(f"[{source}] {line.rstrip()}")
            estimated = min(90, 5 + line_count * 2)
            on_progress(estimated, "OpenCode is working")

        stdout_reader.join(timeout=1)
        stderr_reader.join(timeout=1)
        return_code = process.wait()
        self._drain_output(
            output_queue,
            on_log,
            stdout_lines,
            stderr_lines,
        )
        if return_code == 0:
            on_progress(100, "Complete")
            return AgentRunResult(
                success=True,
                return_code=0,
                summary=f"{agent_name} completed successfully.",
                command=tuple(command),
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines),
            )
        return AgentRunResult(
            success=False,
            return_code=return_code,
            summary=f"OpenCode exited with status {return_code}.",
            command=tuple(command),
            stdout="".join(stdout_lines),
            stderr="".join(stderr_lines),
        )

    @staticmethod
    def _read_output(
        stream,
        source: str,
        output_queue: queue.Queue[tuple[str, str | None]],
    ) -> None:
        if stream is not None:
            for line in stream:
                output_queue.put((source, line))
            stream.close()
        output_queue.put((source, None))

    @staticmethod
    def _drain_output(
        output_queue: queue.Queue[tuple[str, str | None]],
        on_log: LogCallback,
        stdout_lines: list[str],
        stderr_lines: list[str],
    ) -> None:
        while True:
            try:
                source, line = output_queue.get_nowait()
            except queue.Empty:
                return
            if line is not None:
                if source == "stdout":
                    stdout_lines.append(line)
                else:
                    stderr_lines.append(line)
                on_log(f"[{source}] {line.rstrip()}")

    @staticmethod
    def _stop_process(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)

    def run_roadmap_agent(
        self,
        project: Project,
        goal: str,
        constraints: str = "",
        *,
        target_users: str = "",
        mvp_scope: str = "",
        notes: str = "",
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> RoadmapDraft:
        prompt = build_roadmap_prompt(
            project,
            goal,
            constraints,
            target_users=target_users,
            mvp_scope=mvp_scope,
            notes=notes,
        )
        result = self._run_project_agent(
            project, prompt, cancel_event, on_log, on_progress
        )
        draft = parse_roadmap_output(project, goal, result.stdout)
        self._attach_diagnostics(draft, result)
        return draft

    def revise_roadmap_agent(
        self,
        project: Project,
        previous_draft: RoadmapDraft,
        feedback: str,
        *,
        constraints: str = "",
        target_users: str = "",
        mvp_scope: str = "",
        notes: str = "",
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> RoadmapDraft:
        prompt = build_roadmap_prompt(
            project,
            previous_draft.user_goal,
            constraints,
            target_users=target_users,
            mvp_scope=mvp_scope,
            notes=notes,
            previous_draft=previous_draft,
            feedback=feedback,
        )
        result = self._run_project_agent(
            project, prompt, cancel_event, on_log, on_progress
        )
        draft = parse_roadmap_output(
            project,
            previous_draft.user_goal,
            result.stdout,
            previous_draft=previous_draft,
            feedback=feedback,
        )
        self._attach_diagnostics(draft, result)
        return draft

    def run_init_agent(
        self,
        project: Project,
        goal: str,
        *,
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> InitDraft:
        prompt = build_init_prompt(project, goal)
        result = self._run_project_agent(
            project, prompt, cancel_event, on_log, on_progress
        )
        draft = parse_init_output(project, goal, result.stdout)
        self._attach_diagnostics(draft, result)
        return draft

    def revise_init_agent(
        self,
        project: Project,
        previous_draft: InitDraft,
        feedback: str,
        *,
        cancel_event: Event | None = None,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> InitDraft:
        prompt = build_init_prompt(
            project,
            previous_draft.user_goal,
            previous_draft=previous_draft,
            feedback=feedback,
        )
        result = self._run_project_agent(
            project, prompt, cancel_event, on_log, on_progress
        )
        draft = parse_init_output(
            project,
            previous_draft.user_goal,
            result.stdout,
            previous_draft=previous_draft,
            feedback=feedback,
        )
        self._attach_diagnostics(draft, result)
        return draft

    def _run_project_agent(
        self,
        project: Project,
        prompt: str,
        cancel_event: Event | None,
        on_log: LogCallback | None,
        on_progress: ProgressCallback | None,
    ) -> AgentRunResult:
        result = self.run_agent(
            "plan",
            project.repo_path,
            prompt,
            cancel_event or Event(),
            on_log or (lambda _message: None),
            on_progress or (lambda _value, _message: None),
        )
        if not result.success:
            detail = result.stderr.strip() or result.stdout.strip()
            if detail:
                detail = f" {detail[-2_000:]}"
            raise RuntimeError(f"{result.summary}{detail}")
        return result

    @staticmethod
    def _attach_diagnostics(
        draft: RoadmapDraft | InitDraft, result: AgentRunResult
    ) -> None:
        draft.command = result.command
        draft.stdout = result.stdout
        draft.stderr = result.stderr


def select_runner(
    config: AppConfig, mode: str
) -> tuple[AgentRunner, str]:
    if mode == "mock":
        return MockOpenCodeRunner(config.mock_step_delay), "Mock"

    opencode = OpenCodeRunner(config.opencode_command_template)
    if opencode.is_available():
        return opencode, "OpenCode"
    if mode == "opencode":
        raise RuntimeError(
            "OpenCode is not available. Install it, configure "
            "AGENTBOARD_OPENCODE_COMMAND, or choose Mock mode."
        )
    return MockOpenCodeRunner(config.mock_step_delay), (
        "Mock (OpenCode was not found)"
    )
