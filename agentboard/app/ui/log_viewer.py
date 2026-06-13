from __future__ import annotations

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from agentboard.app.models import WorkflowEvent

from .theme import THEME, fixed_font


class LogViewer(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumBlockCount(10_000)
        self.setFont(fixed_font(11))
        self.setPlaceholderText("Live agent output will appear here.")
        self.setStyleSheet(
            f"background-color: {THEME.console};"
            f"border: 1px solid {THEME.border};"
            "border-radius: 9px; padding: 10px;"
            f"color: {THEME.text_secondary};"
        )

    def append_event(self, event: WorkflowEvent) -> None:
        timestamp = event.timestamp.astimezone().strftime("%H:%M:%S")
        self._append_parts(timestamp, event.source, event.message)

    def append_line(self, source: str, message: str) -> None:
        self._append_parts("--:--:--", source, message)

    def _append_parts(self, timestamp: str, source: str, message: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        muted = QTextCharFormat()
        muted.setForeground(QColor(THEME.text_muted))
        source_format = QTextCharFormat()
        source_format.setForeground(QColor(self._source_color(source)))
        source_format.setFontWeight(600)
        body = QTextCharFormat()
        body.setForeground(QColor(THEME.text_secondary))
        cursor.insertText(timestamp.ljust(10), muted)
        cursor.insertText(source[:18].ljust(20), source_format)
        cursor.insertText(f"{message}\n", body)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    @staticmethod
    def _source_color(source: str) -> str:
        normalized = source.lower()
        if "backend" in normalized or "frontend" in normalized:
            return THEME.accent_hover
        if "prompt" in normalized or "planner" in normalized:
            return THEME.violet
        if "test" in normalized:
            return THEME.warning
        if "review" in normalized:
            return THEME.success
        if "error" in normalized:
            return THEME.error
        return THEME.text_primary

