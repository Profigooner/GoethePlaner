from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QFont, QFontDatabase


@dataclass(frozen=True, slots=True)
class Theme:
    background: str = "#080D17"
    background_elevated: str = "#0B1220"
    sidebar: str = "#09111F"
    panel: str = "#0F1828"
    panel_alt: str = "#142033"
    panel_hover: str = "#1B2A42"
    border: str = "#263750"
    border_strong: str = "#3F6FB8"
    text_primary: str = "#F5F7FB"
    text_secondary: str = "#A8B3C7"
    text_muted: str = "#6F7E95"
    accent: str = "#2F81F7"
    accent_hover: str = "#4A93FA"
    accent_pressed: str = "#2469C7"
    violet: str = "#8B5CF6"
    success: str = "#34D399"
    warning: str = "#F59E0B"
    error: str = "#F87171"
    console: str = "#07101D"


THEME = Theme()


def system_font(point_size: int = 13, weight: int = 400) -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
    font.setPointSize(point_size)
    font.setWeight(QFont.Weight(weight))
    return font


def fixed_font(point_size: int = 11) -> QFont:
    font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    font.setPointSize(point_size)
    return font


def rgba(hex_color: str, alpha: int) -> str:
    color = QColor(hex_color)
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {alpha})"


def application_stylesheet(theme: Theme = THEME) -> str:
    return f"""
    * {{
        color: {theme.text_primary};
        font-size: 13px;
    }}
    QMainWindow {{
        background-color: {theme.background};
    }}
    QWidget#appRoot {{
        background: qradialgradient(
            cx: 0.72, cy: 0.10, radius: 1.15,
            fx: 0.72, fy: 0.10,
            stop: 0 {theme.background_elevated},
            stop: 0.48 {theme.background},
            stop: 1 #060A12
        );
    }}
    QStatusBar {{
        background-color: {theme.background};
        color: {theme.text_muted};
        border-top: 1px solid {theme.border};
        padding-left: 10px;
        min-height: 24px;
    }}
    QToolTip {{
        background-color: {theme.panel_alt};
        color: {theme.text_primary};
        border: 1px solid {theme.border_strong};
        border-radius: 6px;
        padding: 6px 8px;
    }}
    QFrame#glassPanel, QFrame#sidebarPanel, QFrame#inspectorPanel,
    QFrame#bottomToolWindow {{
        background-color: {theme.panel};
        border: 1px solid {theme.border};
        border-radius: 13px;
    }}
    QFrame#sidebarPanel {{
        background-color: {theme.sidebar};
    }}
    QFrame#headerPanel {{
        background-color: {theme.panel};
        border: 1px solid {theme.border};
        border-radius: 12px;
    }}
    QLabel#productName {{
        font-size: 20px;
        font-weight: 700;
    }}
    QLabel#projectTitle {{
        font-size: 25px;
        font-weight: 700;
    }}
    QLabel#taskTitle {{
        font-size: 20px;
        font-weight: 650;
    }}
    QLabel#sectionTitle {{
        font-size: 15px;
        font-weight: 650;
    }}
    QLabel#sectionLabel {{
        color: {theme.text_muted};
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 1px;
    }}
    QLabel#secondaryText {{
        color: {theme.text_secondary};
    }}
    QLabel#mutedText {{
        color: {theme.text_muted};
    }}
    QLabel#statusBadge {{
        border-radius: 6px;
        padding: 3px 7px;
        font-size: 11px;
        font-weight: 650;
    }}
    QPushButton {{
        background-color: {theme.panel_alt};
        border: 1px solid {theme.border};
        border-radius: 8px;
        padding: 8px 12px;
        min-height: 18px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {theme.panel_hover};
        border-color: {theme.border_strong};
    }}
    QPushButton:pressed {{
        background-color: {theme.background_elevated};
    }}
    QPushButton:disabled {{
        color: {theme.text_muted};
        background-color: {theme.panel};
        border-color: {theme.border};
    }}
    QPushButton#primaryButton {{
        background-color: {theme.accent};
        border-color: {theme.accent_hover};
        color: white;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {theme.accent_hover};
    }}
    QPushButton#primaryButton:pressed {{
        background-color: {theme.accent_pressed};
    }}
    QPushButton#dangerButton {{
        color: {theme.error};
        background-color: {rgba(theme.error, 18)};
        border-color: {rgba(theme.error, 130)};
    }}
    QPushButton#dangerButton:hover {{
        background-color: {rgba(theme.error, 34)};
    }}
    QPushButton#ghostButton {{
        background: transparent;
        border-color: transparent;
        color: {theme.text_secondary};
    }}
    QPushButton#ghostButton:hover {{
        background-color: {theme.panel_hover};
        color: {theme.text_primary};
    }}
    QPushButton#toolWindowButton {{
        background: transparent;
        border-color: transparent;
        border-radius: 5px;
        color: {theme.text_secondary};
        padding: 5px 10px;
        min-height: 16px;
    }}
    QPushButton#toolWindowButton:hover {{
        background-color: {theme.panel_hover};
        color: {theme.text_primary};
    }}
    QPushButton#toolWindowButton:checked {{
        background-color: {theme.panel_alt};
        border-color: {theme.border_strong};
        color: {theme.accent_hover};
    }}
    QFrame#bottomToolBar {{
        background-color: {theme.background_elevated};
        border: 1px solid {theme.border};
        border-radius: 7px;
    }}
    QFrame#suggestionPanel {{
        background-color: {theme.background_elevated};
        border: 1px solid {theme.border};
        border-radius: 9px;
        padding: 7px;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {{
        background-color: {theme.background_elevated};
        color: {theme.text_primary};
        border: 1px solid {theme.border};
        border-radius: 8px;
        padding: 7px 9px;
        selection-background-color: {theme.accent};
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border-color: {theme.accent};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {theme.panel_alt};
        color: {theme.text_primary};
        border: 1px solid {theme.border};
        selection-background-color: {theme.accent};
        outline: 0;
    }}
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 4px 1px;
    }}
    QScrollBar::handle:vertical {{
        background: {theme.border_strong};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: transparent;
        height: 0;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
    }}
    QScrollBar::handle:horizontal {{
        background: {theme.border_strong};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
        background: transparent;
        width: 0;
    }}
    QProgressBar {{
        background-color: {theme.panel_hover};
        border: none;
        border-radius: 3px;
        min-height: 6px;
        max-height: 6px;
        text-align: center;
        color: transparent;
    }}
    QProgressBar::chunk {{
        background-color: {theme.accent};
        border-radius: 3px;
    }}
    QTabWidget::pane {{
        border: none;
        background-color: {theme.panel};
        top: -1px;
    }}
    QTabBar {{
        background: transparent;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {theme.text_secondary};
        border: none;
        border-bottom: 2px solid transparent;
        padding: 12px 4px 10px 4px;
        font-size: 11px;
        font-weight: 550;
    }}
    QTabBar::tab:selected {{
        color: {theme.accent_hover};
        border-bottom-color: {theme.accent};
    }}
    QTabBar::tab:hover {{
        color: {theme.text_primary};
    }}
    QSplitter::handle {{
        background: transparent;
        width: 8px;
        height: 8px;
    }}
    QListWidget {{
        background: transparent;
        border: none;
        outline: 0;
    }}
    QListWidget::item {{
        border-radius: 7px;
        padding: 8px;
        margin: 2px 0;
        color: {theme.text_secondary};
    }}
    QListWidget::item:selected {{
        background-color: {theme.panel_hover};
        color: {theme.text_primary};
    }}
    QTreeWidget {{
        background: transparent;
        border: none;
        outline: 0;
        color: {theme.text_secondary};
    }}
    QTreeWidget::item {{
        min-height: 25px;
        padding: 3px 5px;
        border-radius: 6px;
    }}
    QTreeWidget::item:hover {{
        background-color: {theme.panel_hover};
        color: {theme.text_primary};
    }}
    QTreeWidget::item:selected {{
        background-color: {rgba(theme.accent, 28)};
        color: {theme.text_primary};
        border: 1px solid {theme.border_strong};
    }}
    QHeaderView::section {{
        background-color: {theme.panel_alt};
        color: {theme.text_secondary};
        border: none;
        border-bottom: 1px solid {theme.border};
        padding: 6px;
    }}
    QDialog {{
        background-color: {theme.background};
    }}
    QMessageBox {{
        background-color: {theme.background};
    }}
    """
