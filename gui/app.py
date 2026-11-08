# -*- coding: utf-8 -*-
"""Qt bootstrap: create the application object, show the main window, and
run the event loop.

On the very first run (no saved language) a modal language picker is shown
before the main window; the chosen code is saved and applied, then the
main window opens. The picker lists the native names and is not translated.

After the main window is shown, the onboarding wizard walks through the
first steps once (connecting, port selection, capture, waveform/decode/
measurement, and the signal generator); finishing or skipping persists the
flag and it never appears automatically again. The same guide stays
available through the Quick Start button.

After the main window is shown, the release notes are shown once when the
installed GUI version changed: a "What's new" dialog with the version and
the translated note lines, on top of the already visible main window.

A ``--check`` command-line option runs a headless packaged-app check
instead of starting the window: it loads the bundled examples, verifies
every registered decoder, performs a measurement, checks the compiled
catalogs, and exits. The summary is collected line by line, printed to
stdout when a console exists, and always written to a UTF-8 report file;
the exit code is 0 for PASS and 1 for FAIL. ``--check-output PATH``
selects the report file, otherwise a fixed name under the system
temporary directory is used. It lets the packaged GUI be verified
without a display.
"""
import os
import sys

from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QLabel, QPushButton,
    QVBoxLayout,
)

from core import updates
from core.config import get as config_get, set as config_set
from core.i18n import SUPPORTED_LANGUAGES, _, set_language
from core.paths import resource_path

from .main_window import MainWindow
from .onboarding import show_onboarding_once
from .version import __version__


class LanguageDialog(QDialog):
    """First-run language picker: native-name list + OK/Cancel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Language")
        self.selected_code = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Choose language / 选择语言 / 選擇語言:"))
        self.combo = QComboBox()
        for code, name in SUPPORTED_LANGUAGES:
            self.combo.addItem(name, code)
        layout.addWidget(self.combo)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        self.selected_code = self.combo.currentData()
        super().accept()


class ReleaseNotesDialog(QDialog):
    """What's new dialog: version number + translated note lines + Close."""

    def __init__(self, version, notes, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_("What's new"))
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(_("Version {version}").format(version=version)))
        for line in notes:
            layout.addWidget(QLabel(_(line)))
        close_button = QPushButton(_("Close"))
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)


def show_release_notes(parent):
    """Show the translated notes once after an update, then mark them seen.

    First runs and unchanged versions return no notes, so no dialog appears.
    The marker is written only after the dialog has been closed.
    """
    notes = updates.pending_notes("gui", __version__)
    if not notes:
        return
    dialog = ReleaseNotesDialog(__version__, notes, parent)
    dialog.exec()
    updates.mark_seen("gui", __version__)


def _check_output_path(argv):
    """Report-file path from ``--check-output PATH`` (or NAME=VALUE)."""
    for i, arg in enumerate(argv):
        if arg == "--check-output" and i + 1 < len(argv):
            return argv[i + 1]
        if arg.startswith("--check-output="):
            return arg.split("=", 1)[1]
    return None


def run_check(argv):
    """Headless packaged-app check; return True when everything passed.

    Loads the bundled examples, verifies every registered decoder is
    present and runs, checks the current device backend's declared
    capabilities, performs a measurement on the bundled square-wave
    example, and checks that the compiled catalogs load from the frozen
    locale directory.
    The summary lines are collected in memory, printed to stdout when it
    is available, and always written to a UTF-8 report file
    (``--check-output PATH``, or a fixed name in the system temporary
    directory). No window is created and no display is needed.
    """
    import core
    import tempfile

    output_path = _check_output_path(argv)
    if not output_path:
        output_path = os.path.join(tempfile.gettempdir(),
                                   "hjs_workbench_gui_check.txt")

    lines = []
    problems = []

    def emit(line):
        lines.append(line)
        stream = sys.stdout
        if stream is not None:
            stream.write(line + "\n")
            stream.flush()

    def check_line(name, ok, detail=""):
        if not ok:
            problems.append(name)
        emit(f"[{'PASS' if ok else 'FAIL'}] {name}"
             + (f"  {detail}" if detail else ""))

    emit(f"HJS-Workbench GUI self-check (version {__version__})")
    emit(f"Resource root: {resource_path()}")

    # Bundled examples: every file in the examples directory must load.
    examples_dir = resource_path("examples")
    example_names = []
    try:
        example_names = sorted(os.listdir(examples_dir))
        check_line("examples directory", len(example_names) >= 2,
                   f"{len(example_names)} file(s)")
    except OSError as exc:
        check_line("examples directory", False, str(exc))
    square_samples = None
    for name in example_names:
        path = os.path.join(examples_dir, name)
        if name.endswith(".sr"):
            try:
                rate, samples = core.acquire_file(path)
            except Exception as exc:  # noqa: BLE001 - readable report
                check_line(f"examples/{name}", False, str(exc))
                continue
            check_line(f"examples/{name}", bool(rate) and len(samples) > 0,
                       f"{rate} Hz, {len(samples)} points")
            if name == "demo_square.sr":
                square_samples = samples
        else:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    nonempty = sum(1 for line in f if line.strip())
            except Exception as exc:  # noqa: BLE001 - readable report
                check_line(f"examples/{name}", False, str(exc))
                continue
            check_line(f"examples/{name}", nonempty > 0,
                       f"{nonempty} non-empty line(s)")

    # Measurement on the bundled square-wave example (~1000 Hz, 50% duty).
    if square_samples is None:
        check_line("measurement (demo_square.sr)", False,
                   "demo_square.sr did not load")
    else:
        metrics = core.measure(core.channel_bits(square_samples, 0))
        if metrics is None:
            check_line("measurement (demo_square.sr)", False, "no result")
        else:
            check_line("measurement (demo_square.sr)",
                       abs(metrics["freq"] - 1000.0) < 100.0,
                       f"freq={metrics['freq']:.1f} Hz")

    # Every decoder the registry declares must be registered and run.
    # The expected count comes from the decoders package itself, so the
    # check follows the registry instead of hard-coding a number.
    from core.decoders import __all__ as _decoder_modules
    deck_names = list(core.DECKS)
    expected_decks = len(_decoder_modules)
    check_line(f"decoder registry ({len(deck_names)}/{expected_decks})",
               len(deck_names) == expected_decks, ", ".join(deck_names))
    deck_rate = core.current_backend().capabilities.sample_rate
    for name, deck in core.DECKS.items():
        try:
            samples = deck["make"](deck_rate)
            events = deck["decode"](samples, deck_rate)
        except Exception as exc:  # noqa: BLE001 - readable report
            check_line(f"decoder {name}", False, str(exc))
            continue
        check_line(f"decoder {name}", len(events) > 0,
                   f"{len(events)} event(s)")

    # Device backend: registered, default, and its declared capabilities
    # accept exactly their own values and reject everything else.
    try:
        backend = core.current_backend()
        caps = backend.capabilities
        problems_backend = []
        try:
            backend.validate_config(sample_rate=caps.sample_rate,
                                    unit_size=caps.unit_size,
                                    channels=caps.channel_count)
        except ValueError as exc:  # noqa: BLE001 - readable report
            problems_backend.append(f"own values rejected: {exc}")
        for label, kwargs in (
                ("sample rate", {"sample_rate": caps.sample_rate + 1}),
                ("byte mode", {"unit_size": caps.unit_size + 1}),
                ("channel count", {"channels": caps.channel_count + 1})):
            try:
                backend.validate_config(**kwargs)
                problems_backend.append(f"{label} accepted outside capabilities")
            except ValueError:
                pass
        if len(caps.channel_names) != caps.channel_count:
            problems_backend.append("channel names do not match channel count")
        check_line(f"device backend {backend.id}",
                   not problems_backend,
                   (f"{caps.channel_count} channels, {caps.unit_size} byte(s), "
                    f"{caps.sample_rate} Hz"
                    + ("" if not problems_backend else
                       "; " + "; ".join(problems_backend))))
    except Exception as exc:  # noqa: BLE001 - readable report
        check_line("device backend", False, str(exc))

    # Compiled catalogs load from the frozen locales directory.
    for code, _native in SUPPORTED_LANGUAGES:
        set_language(code)
        if code == "en":
            check_line(f"language {code}", True, "source, no catalog")
        else:
            check_line(f"language {code}", _("Capture") != "Capture")
    set_language("en")

    emit("-" * 60)
    if problems:
        emit(f"Self-check: FAIL ({len(problems)} problem(s))")
        passed = False
    else:
        emit("Self-check: PASS")
        passed = True

    # The report line is part of the summary, so the file content matches
    # exactly what a normal run prints when a console exists.
    emit(f"Report file: {output_path}")
    with open(output_path, "w", encoding="utf-8") as report:
        report.write("\n".join(lines) + "\n")
    return passed


def main():
    if "--check" in sys.argv:
        sys.exit(0 if run_check(sys.argv) else 1)
    app = QApplication(sys.argv)
    app.setApplicationName("HJS-Workbench")

    saved = config_get("language")
    if saved:
        set_language(saved)
    else:
        dialog = LanguageDialog()
        if dialog.exec() == QDialog.Accepted and dialog.selected_code:
            config_set("language", dialog.selected_code)
            set_language(dialog.selected_code)

    window = MainWindow()
    window.show()
    # First-run onboarding: shown after the language choice and once the
    # main window is visible; finishing or skipping writes the flag and
    # the wizard never appears on its own again.
    show_onboarding_once(window)
    show_release_notes(window)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
