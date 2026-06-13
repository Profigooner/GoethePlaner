from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class NewProjectDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setModal(True)
        self.resize(540, 230)

        title = QLabel("Connect a local project")
        title.setObjectName("taskTitle")
        description = QLabel(
            "Projects group a repository, its tasks, agents, and review output."
        )
        description.setObjectName("secondaryText")
        description.setWordWrap(True)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Project name")
        self.repository_edit = QLineEdit()
        self.repository_edit.setPlaceholderText("Local repository folder")
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        repository_row = QHBoxLayout()
        repository_row.addWidget(self.repository_edit, 1)
        repository_row.addWidget(browse)

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Name", self.name_edit)
        form.addRow("Repository", repository_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Create Project"
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName(
            "primaryButton"
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(4)
        layout.addLayout(form)
        layout.addStretch()
        layout.addWidget(buttons)

    @property
    def project_name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def repository(self) -> Path:
        return Path(self.repository_edit.text().strip()).expanduser().resolve()

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select repository",
            self.repository_edit.text() or str(Path.home()),
        )
        if selected:
            path = Path(selected).resolve()
            self.repository_edit.setText(str(path))
            if not self.name_edit.text().strip():
                self.name_edit.setText(path.name)

    def _validate(self) -> None:
        if not self.project_name:
            QMessageBox.warning(self, "Project name required", "Enter a name.")
            return
        if not self.repository_edit.text().strip() or not self.repository.is_dir():
            QMessageBox.warning(
                self,
                "Repository required",
                "Select an existing local repository folder.",
            )
            return
        self.accept()


class NewTaskDialog(QDialog):
    def __init__(self, project_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Task")
        self.setModal(True)
        self.resize(620, 470)

        title = QLabel(f"New task for {project_name}")
        title.setObjectName("taskTitle")
        description = QLabel(
            "Describe the outcome. GoethePlaner will optimize the prompt, plan "
            "subtasks, and coordinate the default agent team."
        )
        description.setObjectName("secondaryText")
        description.setWordWrap(True)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Short task title")
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText(
            "Describe the programming task, constraints, and expected result."
        )
        self.prompt_edit.setMinimumHeight(180)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Auto · OpenCode when available", "auto")
        self.mode_combo.addItem("Mock · Simulated local workflow", "mock")
        self.mode_combo.addItem("OpenCode · Require installed CLI", "opencode")
        agents = QLabel(
            "Default team: Prompt Optimizer, Planner, Backend, Frontend, "
            "Tester, Reviewer"
        )
        agents.setObjectName("mutedText")
        agents.setWordWrap(True)

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Title", self.title_edit)
        form.addRow("Prompt", self.prompt_edit)
        form.addRow("Execution", self.mode_combo)
        form.addRow("Agents", agents)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Create & Run"
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName(
            "primaryButton"
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(4)
        layout.addLayout(form, 1)
        layout.addWidget(buttons)

    @property
    def task_title(self) -> str:
        return self.title_edit.text().strip()

    @property
    def prompt(self) -> str:
        return self.prompt_edit.toPlainText().strip()

    @property
    def mode(self) -> str:
        return str(self.mode_combo.currentData())

    def _validate(self) -> None:
        if not self.task_title:
            QMessageBox.warning(self, "Title required", "Enter a task title.")
            return
        if not self.prompt:
            QMessageBox.warning(self, "Prompt required", "Enter a task prompt.")
            return
        self.accept()

