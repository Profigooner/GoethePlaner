from __future__ import annotations

from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import QPlainTextEdit


class DiffViewer(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(fixed_font(11))
        self.setPlaceholderText("Repository diff will appear here.")
        self.setStyleSheet(
            f"background-color: {THEME.console};"
            f"border: 1px solid {THEME.border};"
            "border-radius: 9px; padding: 10px;"
            f"color: {THEME.text_secondary};"
        )

        self._addition_format = QTextCharFormat()
        self._addition_format.setForeground(QColor(THEME.success))
        self._deletion_format = QTextCharFormat()
        self._deletion_format.setForeground(QColor(THEME.error))
        self._header_format = QTextCharFormat()
        self._header_format.setForeground(QColor(THEME.accent_hover))

    def set_diff(self, diff_text: str) -> None:
        self.clear()
        cursor = self.textCursor()
        for line in diff_text.splitlines(keepends=True):
            text_format = QTextCharFormat()
            if line.startswith("+") and not line.startswith("+++"):
                text_format = self._addition_format
            elif line.startswith("-") and not line.startswith("---"):
                text_format = self._deletion_format
            elif line.startswith(("diff ", "@@", "index ")):
                text_format = self._header_format
            cursor.insertText(line, text_format)
from .theme import THEME, fixed_font

