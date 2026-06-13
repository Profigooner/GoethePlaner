from __future__ import annotations

import os
import queue
import shlex
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Callable

from PySide6.QtCore import QObject, Signal, Slot


@dataclass(frozen=True, slots=True)
class TestRunResult:
    success: bool
    return_code: int
    cancelled: bool = False


class TestRunner:
    def run(
        self,
        command: list[str],
        repository: Path,
        cancel_event: Event,
        on_output: Callable[[str], None],
    ) -> TestRunResult:
        if not command:
            raise ValueError("Enter a test command.")

        process = subprocess.Popen(
            command,
            cwd=repository,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            shell=False,
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
        )
        output_queue: queue.Queue[str | None] = queue.Queue()
        reader = threading.Thread(
            target=self._read_output,
            args=(process, output_queue),
            daemon=True,
        )
        reader.start()

        while process.poll() is None or reader.is_alive():
            if cancel_event.is_set():
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                return TestRunResult(False, 130, cancelled=True)
            try:
                line = output_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if line is not None:
                on_output(line.rstrip())

        reader.join(timeout=1)
        self._drain(output_queue, on_output)
        return_code = process.wait()
        return TestRunResult(return_code == 0, return_code)

    @staticmethod
    def detect_command(repository: Path) -> list[str]:
        if any(
            (repository / name).exists()
            for name in ("pytest.ini", "pyproject.toml", "setup.cfg")
        ):
            return [sys.executable, "-m", "pytest"]
        if (repository / "package.json").exists():
            return ["npm", "test"]
        return []

    @staticmethod
    def parse_command(command_text: str) -> list[str]:
        return shlex.split(command_text)

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
    def _drain(
        output_queue: queue.Queue[str | None],
        on_output: Callable[[str], None],
    ) -> None:
        while True:
            try:
                line = output_queue.get_nowait()
            except queue.Empty:
                return
            if line is not None:
                on_output(line.rstrip())


class TestWorker(QObject):
    output = Signal(str)
    completed = Signal(object)
    failed = Signal(str)
    terminal = Signal()

    def __init__(self, repository: Path, command_text: str) -> None:
        super().__init__()
        self.repository = repository
        self.command_text = command_text
        self.cancel_event = Event()

    @Slot()
    def run(self) -> None:
        try:
            command = TestRunner.parse_command(self.command_text)
            result = TestRunner().run(
                command,
                self.repository,
                self.cancel_event,
                self.output.emit,
            )
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.terminal.emit()

    def cancel(self) -> None:
        self.cancel_event.set()

