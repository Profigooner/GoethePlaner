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

from agentboard.app.utils.config import AppConfig


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    success: bool
    return_code: int
    summary: str
    cancelled: bool = False


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
        on_log(f"Starting OpenCode agent: {agent_name}")
        on_progress(2, "Starting OpenCode process")

        try:
            process = subprocess.Popen(
                command,
                cwd=repo_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
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
            )

        output_queue: queue.Queue[str | None] = queue.Queue()
        reader = threading.Thread(
            target=self._read_output,
            args=(process, output_queue),
            daemon=True,
        )
        reader.start()
        line_count = 0

        while process.poll() is None or reader.is_alive():
            if cancel_event.is_set():
                self._stop_process(process)
                reader.join(timeout=1)
                return AgentRunResult(
                    success=False,
                    return_code=130,
                    summary="OpenCode agent cancelled.",
                    cancelled=True,
                )

            try:
                line = output_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if line is None:
                continue
            line_count += 1
            on_log(line.rstrip())
            estimated = min(90, 5 + line_count * 2)
            on_progress(estimated, "OpenCode is working")

        reader.join(timeout=1)
        return_code = process.wait()
        self._drain_output(output_queue, on_log)
        if return_code == 0:
            on_progress(100, "Complete")
            return AgentRunResult(
                success=True,
                return_code=0,
                summary=f"{agent_name} completed successfully.",
            )
        return AgentRunResult(
            success=False,
            return_code=return_code,
            summary=f"OpenCode exited with status {return_code}.",
        )

    @staticmethod
    def _read_output(
        process: subprocess.Popen[str],
        output_queue: queue.Queue[str | None],
    ) -> None:
        if process.stdout is not None:
            for line in process.stdout:
                output_queue.put(line)
            process.stdout.close()
        output_queue.put(None)

    @staticmethod
    def _drain_output(
        output_queue: queue.Queue[str | None], on_log: LogCallback
    ) -> None:
        while True:
            try:
                line = output_queue.get_nowait()
            except queue.Empty:
                return
            if line is not None:
                on_log(line.rstrip())

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
