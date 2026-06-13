from __future__ import annotations

from PySide6.QtGui import QFontDatabase, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from agentboard.app.models import WorkflowEvent


class LogViewer(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(10_000)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.setPlaceholderText("Agent output will appear here.")

    def append_event(self, event: WorkflowEvent) -> None:
        timestamp = event.timestamp.astimezone().strftime("%H:%M:%S")
        self.appendPlainText(f"[{timestamp}] [{event.source}] {event.message}")
        self.moveCursor(QTextCursor.MoveOperation.End)

    def append_line(self, source: str, message: str) -> None:
        self.appendPlainText(f"[{source}] {message}")
        self.moveCursor(QTextCursor.MoveOperation.End)

