# -*- coding: utf-8 -*-
"""Main window: grouped toolbar (connection / acquisition / file /
settings) + waveform + decode/measure tabs + status bar."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QToolBar,
    QWidget,
)

import core
from core.files import format_rate
from core.i18n import _
from core.paths import resource_path

from .decoder_panel import DecoderPanel
from .measure_panel import MeasurePanel
from .onboarding import QuickStartDialog
from .settings_dialog import SettingsDialog
from .signal_panel import SignalPanel
from .waveform_view import WaveformView
from .worker import AcquireWorker, ContinuousWorker

POINTS_DEFAULT = 3000
POINTS_MIN = 500
POINTS_MAX = 20000
POINTS_STEP = 500

CAPTURE_FILE_FILTER = "Capture files (*.sr *.bin);;All files (*)"


class MainWindow(QMainWindow):
    """HJS-Workbench main window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HJS-Workbench")
        self._worker = None
        self._cont_worker = None
        self._closing = False
        self._busy = False
        self._cont_running = False
        self._status_msgid = "Ready"
        self._status_kwargs = {}
        self._imported_paths = []
        self._imported_keys = set()

        self._build_toolbar()
        self._sync_rate_mode_combos()
        self._build_central()
        self._sync_device_combo()
        self.retranslate_ui()
        self.refresh_ports()
        self.resize(1280, 760)

    # ------------------------------------------------------------------
    # Building the UI
    # ------------------------------------------------------------------
    def _build_toolbar(self):
        self.toolbar = QToolBar("Capture controls")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        # Connection group: device selector, port selector, Refresh ports.
        self.device_label = QLabel(" Device:")
        self.toolbar.addWidget(self.device_label)
        self.device_combo = QComboBox()
        for backend in core.list_backends():
            self.device_combo.addItem(backend.display_name, backend.id)
        self.device_combo.activated.connect(self._on_device_changed)
        self.toolbar.addWidget(self.device_combo)
        self.device_info = QLabel("")
        self.toolbar.addWidget(self.device_info)

        self.port_label = QLabel(" Port:")
        self.toolbar.addWidget(self.port_label)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(260)
        self.toolbar.addWidget(self.port_combo)

        self.refresh_button = QPushButton("Refresh ports")
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.toolbar.addWidget(self.refresh_button)

        # Acquisition group: sample rate, capture mode, restore defaults,
        # sample points, Capture, Start continuous, Stop.
        self.toolbar.addSeparator()
        self.rate_label = QLabel(" Sample rate:")
        self.toolbar.addWidget(self.rate_label)
        self.rate_combo = QComboBox()
        self.rate_combo.activated.connect(self._on_rate_changed)
        self.toolbar.addWidget(self.rate_combo)

        self.mode_label = QLabel(" Mode:")
        self.toolbar.addWidget(self.mode_label)
        self.mode_combo = QComboBox()
        self.mode_combo.activated.connect(self._on_mode_changed)
        self.toolbar.addWidget(self.mode_combo)

        self.restore_button = QPushButton("Restore defaults")
        self.restore_button.clicked.connect(self.restore_session_defaults)
        self.toolbar.addWidget(self.restore_button)

        self.points_label = QLabel(" Sample points:")
        self.toolbar.addWidget(self.points_label)
        self.points_spin = QSpinBox()
        self.points_spin.setRange(POINTS_MIN, POINTS_MAX)
        self.points_spin.setSingleStep(POINTS_STEP)
        self.points_spin.setValue(POINTS_DEFAULT)
        self.toolbar.addWidget(self.points_spin)

        self.acquire_button = QPushButton("Capture")
        self.acquire_button.clicked.connect(self.acquire_serial)
        self.toolbar.addWidget(self.acquire_button)

        self.cont_start_button = QPushButton("Start continuous")
        self.cont_start_button.clicked.connect(self.start_continuous)
        self.toolbar.addWidget(self.cont_start_button)

        self.cont_stop_button = QPushButton("Stop")
        self.cont_stop_button.setEnabled(False)
        self.cont_stop_button.clicked.connect(self.stop_continuous)
        self.toolbar.addWidget(self.cont_stop_button)

        # File group: Open file, Import, the imported-file selector, Remove.
        self.toolbar.addSeparator()
        self.open_button = QPushButton("Open file")
        self.open_button.clicked.connect(self.open_file)
        self.toolbar.addWidget(self.open_button)

        self.import_button = QPushButton("Import")
        self.import_button.setToolTip(_("Import capture files"))
        self.import_button.clicked.connect(self.import_files)
        self.toolbar.addWidget(self.import_button)

        self.import_combo = QComboBox()
        self.import_combo.setMinimumWidth(220)
        self.import_combo.addItem(_(" (no imported files)"), None)
        self.import_combo.activated.connect(self._on_import_selected)
        self.toolbar.addWidget(self.import_combo)

        self.remove_button = QPushButton("Remove")
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self.remove_import)
        self.toolbar.addWidget(self.remove_button)

        # Right side: Settings and Quick start.
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        self.toolbar.addWidget(self.settings_button)

        # Re-openable quick start guide (same content as the first-run
        # onboarding wizard)
        self.guide_button = QPushButton("Quick start")
        self.guide_button.clicked.connect(self.show_quick_start)
        self.toolbar.addWidget(self.guide_button)

    def _build_central(self):
        self.waveform = WaveformView()
        self.decoder = DecoderPanel()
        self.measure = MeasurePanel()
        self.signal = SignalPanel()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.decoder, "Decode")
        self.tabs.addTab(self.measure, "Measure")
        self.tabs.addTab(self.signal, "Signal")

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.waveform)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([880, 380])
        self.setCentralWidget(splitter)

    # ------------------------------------------------------------------
    # Settings and language
    # ------------------------------------------------------------------
    def open_settings(self):
        """Open the modal settings dialog on top of the main window.

        The dialog is the single place for user preferences (language and
        theme); the main window is blocked while it is open.
        """
        dialog = SettingsDialog(self)
        dialog.exec()

    def show_quick_start(self):
        """Open the re-openable quick start guide dialog."""
        dialog = QuickStartDialog(self)
        dialog.exec()

    # ------------------------------------------------------------------
    # Device selection
    # ------------------------------------------------------------------
    def _on_device_changed(self, index):
        backend_id = self.device_combo.itemData(index)
        if not backend_id or backend_id == core.current_backend().id:
            return
        try:
            backend = core.select_backend(backend_id)
        except ValueError as exc:
            QMessageBox.warning(self, _("Cannot change device"), str(exc))
            self._sync_device_combo()
            return
        # The signal connection baud comes from the backend capabilities;
        # an open connection to the old backend must not survive the switch.
        self.signal.disconnect()
        self._update_device_info()
        self.waveform.refresh_channels()
        self.measure.refresh_channels()
        self._sync_rate_mode_combos()
        self._set_status("Device selected: {name}",
                         name=backend.display_name)

    def _sync_device_combo(self):
        self.device_combo.blockSignals(True)
        idx = self.device_combo.findData(core.current_backend().id)
        if idx >= 0:
            self.device_combo.setCurrentIndex(idx)
        self.device_combo.blockSignals(False)

    def _update_device_info(self):
        caps = core.current_backend().capabilities
        self.device_info.setText(
            _("{name} - {count} channels, {unit} byte(s)/sample, "
              "{rate} Hz").format(name=caps.display_name,
                                  count=caps.channel_count,
                                  unit=caps.unit_size,
                                  rate=caps.sample_rate))

    # ------------------------------------------------------------------
    # Sample rate and capture mode
    # ------------------------------------------------------------------
    def _sync_rate_mode_combos(self):
        """Repopulate the rate and mode selectors strictly from the current
        backend's capabilities and select the effective session values.

        The rate items show the human-readable rate and hold the integer
        rate as item data; the mode items show the translated label and
        hold the mode id as item data.
        """
        caps = core.current_backend().capabilities
        self.rate_combo.blockSignals(True)
        self.rate_combo.clear()
        for rate in caps.supported_rates:
            self.rate_combo.addItem(format_rate(rate), rate)
        self.rate_combo.blockSignals(False)

        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        for mode in caps.supported_modes:
            self.mode_combo.addItem(core.session.mode_label(mode), mode)
        self.mode_combo.blockSignals(False)

        self._select_effective_rate_mode()

    def _select_effective_rate_mode(self):
        """Move both selectors to the current effective session values and
        refresh the mode-dependent control states."""
        self.rate_combo.blockSignals(True)
        index = self.rate_combo.findData(core.session.effective_sample_rate())
        if index >= 0:
            self.rate_combo.setCurrentIndex(index)
        self.rate_combo.blockSignals(False)

        self.mode_combo.blockSignals(True)
        index = self.mode_combo.findData(
            core.session.effective_capture_mode())
        if index >= 0:
            self.mode_combo.setCurrentIndex(index)
        self.mode_combo.blockSignals(False)
        self._apply_controls()

    def _current_rate(self):
        """The sample rate selected in the rate combo (never None in a
        populated selector)."""
        rate = self.rate_combo.currentData()
        if rate is None:
            rate = core.session.effective_sample_rate()
        return rate

    def _current_mode(self):
        """The capture mode id selected in the mode combo."""
        mode = self.mode_combo.currentData()
        if mode is None:
            mode = core.current_backend().capabilities.default_mode
        return mode

    def _on_rate_changed(self, index):
        """Persist the newly selected rate immediately.

        A rejected value leaves the selector on the last valid value so
        the combo and the saved config never disagree.
        """
        rate = self.rate_combo.itemData(index)
        try:
            core.session.save_sample_rate(rate)
        except ValueError as exc:
            QMessageBox.warning(self, _("Cannot save"), str(exc))
        self._select_effective_rate_mode()

    def _on_mode_changed(self, index):
        """Persist the newly selected mode immediately and apply the
        mode-dependent control states."""
        mode = self.mode_combo.itemData(index)
        try:
            core.session.save_capture_mode(mode)
        except ValueError as exc:
            QMessageBox.warning(self, _("Cannot save"), str(exc))
        self._select_effective_rate_mode()

    def restore_session_defaults(self):
        """Remove the saved rate and mode and re-sync the selectors to the
        backend defaults."""
        core.session.reset_to_defaults()
        self._select_effective_rate_mode()
        self._set_status("Restored default sample rate and capture mode")

    def _retranslate_mode_combo(self):
        """Re-apply the language to the mode item labels only; the stored
        mode ids stay unchanged."""
        for index in range(self.mode_combo.count()):
            mode = self.mode_combo.itemData(index)
            if mode is not None:
                self.mode_combo.setItemText(
                    index, core.session.mode_label(mode))

    def _apply_controls(self):
        """Enable or disable the acquisition controls from the current
        busy, streaming, and capture-mode state.

        Burst mode disables the realtime-only controls: the sample
        points spin box and the continuous start button. Realtime mode
        keeps the previous behavior.
        """
        busy = self._busy
        running = self._cont_running
        realtime = self._current_mode() == "realtime"
        for widget in (self.acquire_button, self.open_button,
                       self.import_button, self.import_combo,
                       self.remove_button, self.refresh_button):
            widget.setEnabled(not busy and not running)
        self.cont_start_button.setEnabled(realtime and not busy
                                          and not running)
        self.cont_stop_button.setEnabled(running and not busy)
        self.points_spin.setEnabled(realtime and not running)
        self.port_combo.setEnabled(not running)
        self.rate_combo.setEnabled(not busy and not running)
        self.mode_combo.setEnabled(not busy and not running)
        self.restore_button.setEnabled(not busy and not running)

    def retranslate_ui(self):
        """Re-apply the active language to every visible string."""
        self.setWindowTitle("HJS-Workbench")
        self.toolbar.setWindowTitle(_("Capture controls"))
        self.port_label.setText(_(" Port:"))
        self.refresh_button.setText(_("Refresh ports"))
        self.rate_label.setText(_(" Sample rate:"))
        self.mode_label.setText(_(" Mode:"))
        self.restore_button.setText(_("Restore defaults"))
        self.points_label.setText(_(" Sample points:"))
        self.acquire_button.setText(_("Capture"))
        self.cont_start_button.setText(_("Start continuous"))
        self.cont_stop_button.setText(_("Stop"))
        self.open_button.setText(_("Open file"))
        self.import_button.setText(_("Import"))
        self.import_button.setToolTip(_("Import capture files"))
        self.remove_button.setText(_("Remove"))
        self.settings_button.setText(_("Settings"))
        self.guide_button.setText(_("Quick start"))
        self.tabs.setTabText(0, _("Decode"))
        self.tabs.setTabText(1, _("Measure"))
        self.tabs.setTabText(2, _("Signal"))
        self.device_label.setText(_(" Device:"))
        self._update_device_info()
        self._render_status()
        self._retranslate_port_placeholder()
        self._retranslate_import_placeholder()
        self._retranslate_mode_combo()
        self.waveform.retranslate_ui()
        self.decoder.retranslate_ui()
        self.measure.retranslate_ui()
        self.signal.retranslate_ui()

    def _retranslate_port_placeholder(self):
        """Re-apply the language to the empty-port placeholder row only."""
        if self.port_combo.count() == 0:
            self.port_combo.addItem(_(" (no serial port detected)"), None)
            self.port_combo.setEnabled(False)
        elif self.port_combo.itemData(0) is None:
            self.port_combo.setItemText(0, _(" (no serial port detected)"))

    def _retranslate_import_placeholder(self):
        """Re-apply the language to the empty import-list placeholder row."""
        if self.import_combo.count() and self.import_combo.itemData(0) is None:
            self.import_combo.setItemText(0, _(" (no imported files)"))

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------
    def _set_status(self, msgid, **kwargs):
        """Remember the current status as a msgid so retranslate can re-render."""
        self._status_msgid = msgid
        self._status_kwargs = kwargs
        self._render_status()

    def _render_status(self):
        self.statusBar().showMessage(
            _(self._status_msgid).format(**self._status_kwargs))

    # ------------------------------------------------------------------
    # Serial port
    # ------------------------------------------------------------------
    def refresh_ports(self):
        self.port_combo.clear()
        for device, description in core.list_serial_ports():
            self.port_combo.addItem(f"{device} - {description}", device)
        if self.port_combo.count() == 0:
            self.port_combo.addItem(_(" (no serial port detected)"), None)
            self.port_combo.setEnabled(False)
        else:
            self.port_combo.setEnabled(True)

    # ------------------------------------------------------------------
    # Capture and files
    # ------------------------------------------------------------------
    def acquire_serial(self):
        """Route the Capture button on the current capture mode.

        Realtime keeps the one-shot AcquireWorker path with the selected
        rate; burst records the whole burst buffer through
        acquire_burst and ignores the sample points spin box.
        """
        port = self.port_combo.currentData()
        if port is None:
            QMessageBox.warning(
                self, _("Cannot capture"),
                _("No usable serial port detected. Connect the device data port, then click Refresh ports."),
            )
            return
        rate = self._current_rate()
        if self._current_mode() == "burst":
            self._start_job(
                core.acquire_burst, (port,),
                "Capturing burst from {port}...",
                fn_kwargs={"sample_rate": rate}, port=port,
            )
            return
        points = self.points_spin.value()
        self._start_job(
            core.acquire_serial, (port, points),
            "Capturing {points} points from {port}...",
            fn_kwargs={"sample_rate": rate}, points=points, port=port,
        )

    def open_file(self):
        start_dir = resource_path("examples")
        path, _filter = QFileDialog.getOpenFileName(
            self, _("Open capture file"), start_dir, CAPTURE_FILE_FILTER,
        )
        if not path:
            return
        self._start_job(core.acquire_file, (path,), "Reading file...")

    # ------------------------------------------------------------------
    # User file import (multi-file management, in-app references only)
    # ------------------------------------------------------------------
    def import_files(self):
        """Add the chosen capture files to the imported-file list.

        The files are registered in the application, not copied or
        modified anywhere. Duplicates are rejected by absolute path.
        """
        start_dir = resource_path("examples")
        paths, _filter = QFileDialog.getOpenFileNames(
            self, _("Import capture files"), start_dir, CAPTURE_FILE_FILTER,
        )
        if not paths:
            return
        added = 0
        duplicates = []
        for raw in paths:
            path = os.path.abspath(raw)
            key = os.path.normcase(path)
            if key in self._imported_keys:
                duplicates.append(path)
                continue
            self._imported_keys.add(key)
            self._imported_paths.append(path)
            self._drop_import_placeholder()
            self.import_combo.addItem(path, path)
            added += 1
        self.remove_button.setEnabled(bool(self._imported_paths))
        if added:
            self._set_status("Imported {n} file(s)", n=added)
        elif duplicates:
            self._set_status("File already imported: {path}",
                             path=duplicates[-1])

    def _drop_import_placeholder(self):
        """Remove the empty-list placeholder before adding a real entry."""
        if (self.import_combo.count() == 1
                and self.import_combo.itemData(0) is None):
            self.import_combo.clear()

    def _on_import_selected(self, index):
        """Load the selected imported file through the shared core loader."""
        path = self.import_combo.itemData(index)
        if not path:
            return
        self._start_job(core.acquire_file, (path,), "Reading file...")

    def remove_import(self):
        """Remove the selected entry from the in-app import list.

        Only the registration is removed; the file on disk is never
        modified or deleted.
        """
        path = self.import_combo.currentData()
        if path is None:
            return
        index = self.import_combo.currentIndex()
        self.import_combo.removeItem(index)
        self._imported_keys.discard(os.path.normcase(path))
        if path in self._imported_paths:
            self._imported_paths.remove(path)
        if not self._imported_paths:
            self.import_combo.addItem(_(" (no imported files)"), None)
            self.remove_button.setEnabled(False)
        self._set_status("Removed from the import list: {path}", path=path)

    def _start_job(self, fn, args, status_msgid, fn_kwargs=None,
                   **status_kwargs):
        self._set_busy(True)
        self._set_status(status_msgid, **status_kwargs)
        self._worker = AcquireWorker(fn, args, kwargs=fn_kwargs, parent=self)
        self._worker.succeeded.connect(self._on_success)
        self._worker.failed.connect(self._on_failure)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _set_busy(self, busy):
        self._busy = busy
        self._apply_controls()

    # ------------------------------------------------------------------
    # Continuous capture
    # ------------------------------------------------------------------
    def start_continuous(self):
        """Start the streaming worker on the selected port.

        One-shot capture and continuous capture share the same data port,
        so they never run together: while streaming runs, the one-shot
        controls are disabled (and vice versa). The worker opens the HAL
        connection itself and emits throttled snapshots that refresh the
        waveform about every 150 ms.
        """
        if self._cont_worker is not None and self._cont_worker.isRunning():
            return
        port = self.port_combo.currentData()
        if port is None:
            QMessageBox.warning(
                self, _("Cannot capture"),
                _("No usable serial port detected. Connect the device data port, then click Refresh ports."),
            )
            return
        capacity = self.points_spin.value()
        worker = ContinuousWorker(port, capacity,
                                  rate=self._current_rate(), parent=self)
        worker.snapshot.connect(self._on_continuous_snapshot)
        worker.failed.connect(self._on_continuous_failure)
        worker.finished.connect(self._on_continuous_finished)
        self._cont_worker = worker
        self._set_continuous_running(True)
        self._set_status("Streaming from {port}...", port=port)
        worker.start()

    def stop_continuous(self):
        """Signal the streaming worker to stop; it closes the connection
        and the port is released before the controls re-enable."""
        worker = self._cont_worker
        if worker is None or not worker.isRunning():
            return
        self._set_status("Stopping continuous capture...")
        worker.stop()

    def _set_continuous_running(self, running):
        """Enable/disable the controls per mode exclusivity.

        While streaming runs, the one-shot capture controls (capture,
        open file, refresh, sample points, port picker) are disabled so
        the two modes cannot run together on the same port.
        """
        self._cont_running = running
        self._apply_controls()

    def _on_continuous_snapshot(self, rate, samples):
        if self._closing:
            return
        self.waveform.set_data(rate, samples)
        self._set_status("Streaming {n} points", n=len(samples))

    def _on_continuous_failure(self, message):
        if self._closing:
            return
        QMessageBox.warning(self, _("Capture failed"), message)
        self._set_status("Capture failed")

    def _on_continuous_finished(self):
        worker = self._cont_worker
        self._cont_worker = None
        if worker is not None:
            worker.deleteLater()
        if not self._closing:
            self._set_continuous_running(False)
            self._set_status("Ready")

    def _on_success(self, rate, samples):
        if self._closing:
            return
        self.waveform.set_data(rate, samples)
        self.decoder.set_data(rate, samples)
        self.measure.set_data(rate, samples)
        self._set_status("Captured {n} points ({rate} Hz)",
                         n=len(samples), rate=rate)

    def _on_failure(self, message):
        if self._closing:
            return
        QMessageBox.warning(self, _("Capture failed"), message)
        self._set_status("Capture failed")

    def _on_finished(self):
        self._set_busy(False)
        if self._worker is not None:
            self._worker.deleteLater()
            self._worker = None

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    def closeEvent(self, event):
        # Wait for the background thread to finish (a serial capture lasts no
        # longer than its timeout) to avoid leftover resources
        worker = self._worker
        if worker is not None and worker.isRunning():
            self._closing = True
            self._set_status("Waiting for the background capture to finish...")
            waited = 0.0
            while worker.isRunning() and waited < 20.0:
                worker.wait(100)
                waited += 0.1
                QApplication.processEvents()
        # Stop the streaming worker and join it so no background thread or
        # open port outlives the window.
        cont = self._cont_worker
        if cont is not None and cont.isRunning():
            self._closing = True
            cont.stop()
            cont.wait(2000)
        # Release the signal-generator port as well.
        self.signal.shutdown()
        super().closeEvent(event)
