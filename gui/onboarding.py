# -*- coding: utf-8 -*-
"""Onboarding: the first-run step-by-step wizard and the re-openable
quick start guide dialog.

The wizard is shown once after the language choice and the first main
window; finishing any step or pressing Skip writes the
``onboarding_done`` config flag so the wizard never reappears on its
own. The same five-step content is re-openable at any time as the Quick
Start Guide (toolbar button in the GUI, menu entry in the CLI).
"""
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from core.config import get as config_get, set as config_set
from core.guide import GUIDE_STEPS
from core.i18n import _

ONBOARDING_DONE_KEY = "onboarding_done"


def onboarding_done():
    """True once the wizard was finished or skipped."""
    return bool(config_get(ONBOARDING_DONE_KEY, False))


def mark_onboarding_done():
    """Persist the flag so the wizard does not appear automatically again."""
    config_set(ONBOARDING_DONE_KEY, True)


class GuideContent(QWidget):
    """Renders the translated guide steps as a scrollable page list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for number, (title, lines) in enumerate(GUIDE_STEPS, 1):
            layout.addWidget(
                QLabel(_("Step {number}: {title}").format(
                    number=number, title=_(title))))
            for line in lines:
                layout.addWidget(QLabel("  " + _(line)))
        layout.addStretch(1)


class QuickStartDialog(QDialog):
    """Re-openable quick start guide: all steps at once + Close."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Quick Start Guide"))
        layout = QVBoxLayout(self)
        layout.addWidget(GuideContent(self))
        close_button = QPushButton(_("Close"))
        close_button.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close_button)
        layout.addLayout(row)
        self.resize(640, 480)


class OnboardingWizard(QDialog):
    """First-run step-by-step wizard with Back/Next and Skip.

    Navigating to the last step with Next or pressing Skip finishes the
    wizard; finishing writes the persisted flag.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("Welcome to HJS-Workbench"))
        self.setModal(True)
        self._step = 0
        self._finishing = False

        layout = QVBoxLayout(self)
        self.title_label = QLabel("")
        self.body_label = QLabel("")
        self.body_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.body_label)
        layout.addStretch(1)

        buttons = QHBoxLayout()
        self.back_button = QPushButton(_("Back"))
        self.back_button.clicked.connect(self._go_back)
        buttons.addWidget(self.back_button)
        self.next_button = QPushButton(_("Next"))
        self.next_button.clicked.connect(self._go_next)
        buttons.addWidget(self.next_button)
        self.skip_button = QPushButton(_("Skip"))
        self.skip_button.clicked.connect(self._skip)
        buttons.addWidget(self.skip_button)
        layout.addLayout(buttons)

        self.resize(620, 380)
        self._show_step(0)

    # ------------------------------------------------------------------
    # Step navigation
    # ------------------------------------------------------------------
    def _show_step(self, index):
        self._step = index
        title, lines = GUIDE_STEPS[index]
        self.title_label.setText(
            _("Step {number} of {total}: {title}").format(
                number=index + 1, total=len(GUIDE_STEPS), title=_(title)))
        self.body_label.setText("\n".join(_(line) for line in lines))
        self.back_button.setEnabled(index > 0)
        last = index == len(GUIDE_STEPS) - 1
        self.next_button.setText(_("Finish") if last else _("Next"))

    def _go_back(self):
        if self._step > 0:
            self._show_step(self._step - 1)

    def _go_next(self):
        if self._step < len(GUIDE_STEPS) - 1:
            self._show_step(self._step + 1)
        else:
            self._finishing = True
            self.accept()

    def _skip(self):
        self._finishing = True
        self.accept()

    def closeEvent(self, event):
        """Closing the window counts as finishing the wizard."""
        self._finishing = True
        super().closeEvent(event)


def show_onboarding_once(parent):
    """Show the wizard unless it was already finished or skipped.

    Returns True when the wizard was displayed (and thereby completed);
    False when the persisted flag says it must not appear.
    """
    if onboarding_done():
        return False
    wizard = OnboardingWizard(parent)
    wizard.exec()
    mark_onboarding_done()
    return True
