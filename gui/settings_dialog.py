# -*- coding: utf-8 -*-
"""Modal settings dialog: the user preferences surface of the GUI.

The dialog holds preferences only: the language and the light/dark theme.
Session hardware controls (device backend, port, sample points, capture)
stay in the main window. It is opened modally with ``exec()`` so the main
window is blocked while it is open; closing it returns to the unchanged
main window.

- The language combo is populated from ``core.i18n.SUPPORTED_LANGUAGES``
  and shows the native names, never translated.
- The theme combo is populated from the ordered identifiers in
  ``core.theme`` and shows translated labels.
- OK saves and applies every change and closes; Apply saves and applies
  while staying open; Cancel discards unsaved changes.
- Applying persists through ``core.config``, calls ``set_language`` and
  the application ``apply_theme``, and retranslates the interface so the
  change is visible immediately without a restart.
"""
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.config import set as config_set
from core.i18n import SUPPORTED_LANGUAGES, _, get_language, set_language
from core.theme import THEME_IDS, THEME_LABELS, get_theme, set_theme

from .theme import apply_theme


class SettingsDialog(QDialog):
    """Language and theme preferences with OK / Apply / Cancel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Settings"))
        self.setModal(True)

        form = QFormLayout()
        self.language_label = QLabel(_("Language:"))
        self.language_combo = QComboBox()
        for code, name in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(name, code)
        form.addRow(self.language_label, self.language_combo)

        self.theme_label = QLabel(_("Theme:"))
        self.theme_combo = QComboBox()
        for theme_id in THEME_IDS:
            self.theme_combo.addItem(_(THEME_LABELS[theme_id]), theme_id)
        form.addRow(self.theme_label, self.theme_combo)

        buttons = QHBoxLayout()
        self.ok_button = QPushButton(_("OK"))
        self.apply_button = QPushButton(_("Apply"))
        self.cancel_button = QPushButton(_("Cancel"))
        self.ok_button.clicked.connect(self._on_ok)
        self.apply_button.clicked.connect(self._on_apply)
        self.cancel_button.clicked.connect(self.reject)
        buttons.addStretch(1)
        buttons.addWidget(self.ok_button)
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)

        self._sync_from_saved()

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------
    def retranslate_ui(self):
        """Re-apply the active language to the dialog strings.

        The language names stay native; the theme labels follow the new
        language and the theme combo keeps its data (the identifiers).
        """
        self.setWindowTitle(_("Settings"))
        self.language_label.setText(_("Language:"))
        self.theme_label.setText(_("Theme:"))
        for index in range(self.theme_combo.count()):
            theme_id = self.theme_combo.itemData(index)
            if theme_id in THEME_LABELS:
                self.theme_combo.setItemText(index, _(THEME_LABELS[theme_id]))
        self.ok_button.setText(_("OK"))
        self.apply_button.setText(_("Apply"))
        self.cancel_button.setText(_("Cancel"))

    def _sync_from_saved(self):
        """Show the currently saved language and theme on open."""
        index = self.language_combo.findData(get_language())
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        index = self.theme_combo.findData(get_theme())
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

    # ------------------------------------------------------------------
    # Apply logic
    # ------------------------------------------------------------------
    def _apply_choices(self):
        """Save and apply the current selections immediately.

        Persists through ``core.config``, installs the language and the
        theme, restyles the application, and retranslates the dialog and
        the owning main window. Returns True when something changed.
        """
        code = self.language_combo.currentData()
        theme_id = self.theme_combo.currentData()
        language_changed = bool(code) and code != get_language()
        theme_changed = bool(theme_id) and theme_id != get_theme()

        if language_changed:
            config_set("language", code)
            set_language(code)
        if theme_changed:
            set_theme(theme_id)

        app = QApplication.instance()
        if theme_id and app is not None:
            apply_theme(app, theme_id)

        if language_changed or theme_changed:
            self.retranslate_ui()
            window = self.parent()
            if window is not None and hasattr(window, "retranslate_ui"):
                window.retranslate_ui()
        return language_changed or theme_changed

    def _on_apply(self):
        self._apply_choices()

    def _on_ok(self):
        self._apply_choices()
        self.accept()
