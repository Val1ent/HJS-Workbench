# -*- coding: utf-8 -*-
"""Qt application theming: style sheet + pyqtgraph color push.

All Qt, style-sheet, and pyqtgraph code lives here; the color tokens are
plain data in ``core.theme``. ``apply_theme(app, theme_id)`` restyles the
whole application at runtime without a restart:

- builds the theme style sheet and applies it to the QApplication, which
  repolishes every already-open widget (main window, toolbars, buttons,
  combo boxes, spin boxes, tabs, tables, group boxes, labels, text
  inputs, and dialogs);
- updates the pyqtgraph default background/foreground for any plot
  created later;
- calls ``apply_theme(theme_id)`` on every open widget that implements it
  (the waveform view pushes plot background, axis pens, grid, and channel
  colors).

The saved theme is read with ``core.theme.get_theme`` at startup and the
switch is manual only: nothing here follows the system theme.
"""
from string import Template

import pyqtgraph as pg

from core.theme import normalize, tokens

# Token placeholders use ``$name`` so the QSS braces stay untouched.
_STYLESHEET = Template("""
QWidget {
    background-color: $window;
    color: $text;
}
QMainWindow, QDialog {
    background-color: $window;
}
QToolBar {
    background-color: $base;
    border: none;
    border-bottom: 1px solid $border;
    spacing: 4px;
}
QToolBar::separator {
    background-color: $border;
    width: 1px;
    margin: 4px 6px;
}
QStatusBar {
    background-color: $base;
    border-top: 1px solid $border;
    color: $muted;
}
QPushButton {
    background-color: $button;
    color: $text;
    border: 1px solid $border;
    border-radius: 3px;
    padding: 4px 12px;
}
QPushButton:hover {
    background-color: $alternate;
    border-color: $accent;
}
QPushButton:pressed {
    background-color: $window;
}
QPushButton:disabled {
    color: $muted;
    background-color: $window;
    border-color: $border;
}
QComboBox {
    background-color: $base;
    color: $text;
    border: 1px solid $border;
    border-radius: 3px;
    padding: 3px 8px;
}
QComboBox:hover {
    border-color: $accent;
}
QComboBox:disabled {
    color: $muted;
    border-color: $border;
}
QComboBox QAbstractItemView {
    background-color: $base;
    color: $text;
    border: 1px solid $border;
    selection-background-color: $accent;
    selection-color: $accent_text;
}
QSpinBox {
    background-color: $base;
    color: $text;
    border: 1px solid $border;
    border-radius: 3px;
    padding: 2px 6px;
}
QSpinBox:hover {
    border-color: $accent;
}
QSpinBox:disabled {
    color: $muted;
    border-color: $border;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: $button;
    border: 1px solid $border;
    width: 14px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    border-color: $accent;
}
QTabWidget::pane {
    border: 1px solid $border;
    background-color: $base;
    top: -1px;
}
QTabBar::tab {
    background-color: $button;
    color: $muted;
    border: 1px solid $border;
    padding: 5px 14px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: $base;
    color: $text;
    border-bottom-color: $accent;
}
QTabBar::tab:hover:!selected {
    color: $text;
}
QTableWidget, QTableView {
    background-color: $base;
    alternate-background-color: $alternate;
    color: $text;
    gridline-color: $border;
    border: 1px solid $border;
    selection-background-color: $accent;
    selection-color: $accent_text;
}
QHeaderView::section {
    background-color: $button;
    color: $text;
    border: none;
    border-right: 1px solid $border;
    border-bottom: 1px solid $border;
    padding: 4px 8px;
}
QTableCornerButton::section {
    background-color: $button;
    border: 1px solid $border;
}
QGroupBox {
    border: 1px solid $border;
    border-radius: 4px;
    margin-top: 10px;
    background-color: $window;
    color: $text;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 4px;
    color: $accent;
}
QLabel {
    background: transparent;
    color: $text;
}
QLineEdit {
    background-color: $base;
    color: $text;
    border: 1px solid $border;
    border-radius: 3px;
    padding: 2px 6px;
    selection-background-color: $accent;
    selection-color: $accent_text;
}
QLineEdit:disabled {
    color: $muted;
    border-color: $border;
}
QMenu {
    background-color: $base;
    color: $text;
    border: 1px solid $border;
}
QMenu::item:selected {
    background-color: $accent;
    color: $accent_text;
}
QMenu::item:disabled {
    color: $muted;
}
QToolTip {
    background-color: $base;
    color: $text;
    border: 1px solid $border;
    padding: 2px 6px;
}
QSplitter::handle {
    background-color: $border;
}
QSplitter::handle:hover {
    background-color: $accent;
}
QAbstractScrollArea::corner {
    background-color: $window;
}
QScrollBar:vertical {
    background-color: $window;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: $button;
    border: 1px solid $border;
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar:horizontal {
    background-color: $window;
    height: 12px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: $button;
    border: 1px solid $border;
    border-radius: 3px;
    min-width: 20px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}
""")


def build_stylesheet(theme_id):
    """Return the full Qt style sheet for a theme (non-empty string)."""
    return _STYLESHEET.substitute(tokens(theme_id))


def apply_theme(app, theme_id):
    """Apply the theme to the application and every open widget.

    Unknown identifiers fall back to the dark default, mirroring
    ``core.theme``. The QApplication style sheet restyles all widgets
    immediately; the pyqtgraph config and the per-widget ``apply_theme``
    hooks carry the colors into the plots.
    """
    theme_id = normalize(theme_id)
    tok = tokens(theme_id)

    app.setStyleSheet(build_stylesheet(theme_id))

    pg.setConfigOption("background", tok["plot_background"])
    pg.setConfigOption("foreground", tok["plot_foreground"])

    for widget in app.allWidgets():
        hook = getattr(widget, "apply_theme", None)
        if callable(hook):
            hook(theme_id)
