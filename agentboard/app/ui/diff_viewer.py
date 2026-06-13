from __future__ import annotations

from PySide6.QtGui import QColor, QFontDatabase, QTextCharFormat
from PySide6.QtWidgets import QPlainTextEdit


class DiffViewer(QPlainTextEdit):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont))
        self.setPlaceholderText("Repository diff will appear here.")

        self._addition_format = QTextCharFormat()
        self._addition_format.setForeground(QColor("#15803d"))
        self._deletion_format = QTextCharFormat()
        self._deletion_format.setForeground(QColor("#b91c1c"))
        self._header_format = QTextCharFormat()
        self._header_format.setForeground(QColor("#2563eb"))

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

