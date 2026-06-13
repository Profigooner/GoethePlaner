from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from agentboard.app.ui.main_window import MainWindow
from agentboard.app.ui.theme import application_stylesheet
from agentboard.app.utils.config import AppConfig
from agentboard.app.utils.logging import configure_logging


def main() -> int:
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName("GoethePlaner")
    app.setOrganizationName("GoethePlaner")
    app.setStyleSheet(application_stylesheet())
    window = MainWindow(AppConfig.from_env())
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
