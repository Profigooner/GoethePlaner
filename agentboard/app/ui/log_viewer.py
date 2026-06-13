from __future__ import annotations

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from agentboard.app.models import WorkflowEvent

from .theme import THEME, fixed_font


class LogViewer(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._entries: list[tuple[str, str, str]] = []
        self._source_filter = ""
        self._search_filter = ""
        self.setReadOnly(True)
        self.setMaximumBlockCount(10_000)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
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
        self._append_entry(timestamp, event.source, event.message)

    def append_line(self, source: str, message: str) -> None:
        self._append_entry("--:--:--", source, message)

    def clear(self) -> None:
        self._entries.clear()
        super().clear()

    def set_source_filter(self, value: str) -> None:
        self._source_filter = "" if value == "All Sources" else value
        self._render_entries()

    def set_search_filter(self, value: str) -> None:
        self._search_filter = value.strip().casefold()
        self._render_entries()

    def _append_entry(
        self, timestamp: str, source: str, message: str
    ) -> None:
        self._entries.append((timestamp, source, message))
        if self._matches(source, message):
            self._insert_parts(timestamp, source, message)

    def _render_entries(self) -> None:
        super().clear()
        for timestamp, source, message in self._entries:
            if self._matches(source, message):
                self._insert_parts(timestamp, source, message)

    def _matches(self, source: str, message: str) -> bool:
        if self._source_filter and (
            self._source_filter.casefold() not in source.casefold()
        ):
            return False
        if self._search_filter and (
            self._search_filter not in f"{source} {message}".casefold()
        ):
            return False
        return True

    def _insert_parts(self, timestamp: str, source: str, message: str) -> None:
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
