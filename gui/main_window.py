# -*- coding: utf-8 -*-
"""Main window: connection area (port/points/capture/open file) + waveform
+ decode/measure tabs + status bar + toolbar language selector."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QComboBox, QFileDialog, QLabel, QMainWindow,
    QMessageBox, QPushButton, QSpinBox, QSplitter, QTabWidget, QToolBar,
)

import core
from core.config import set as config_set
from core.i18n import SUPPORTED_LANGUAGES, _, get_language, set_language
from core.paths import resource_path
from .decoder_panel import DecoderPanel
from .measure_panel import MeasurePanel
from .onboarding import QuickStartDialog
from .signal_panel import SignalPanel
from .waveform_view import WaveformView
from .worker import AcquireWorker, ContinuousWorker

POINTS_DEFAULT = 3000
POINTS_MIN = 500
POINTS_MAX = 20000
POINTS_STEP = 500


class MainWindow(QMainWindow):
    """HJS-Workbench main window."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HJS-Workbench")
        self._worker = None
        self._cont_worker = None
        self._closing = False
        self._status_msgid = "Ready"
        self._status_kwargs = {}

        self._build_toolbar()
        self._build_central()
        self._sync_language_combo()
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

        self.port_label = QLabel(" Port:")
        self.toolbar.addWidget(self.port_label)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(260)
        self.toolbar.addWidget(self.port_combo)

        self.refresh_button = QPushButton("Refresh ports")
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.toolbar.addWidget(self.refresh_button)

        self.toolbar.addSeparator()
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

        self.open_button = QPushButton("Open file")
        self.open_button.clicked.connect(self.open_file)
        self.toolbar.addWidget(self.open_button)

        # Language selector (native names, never translated)
        self.toolbar.addSeparator()
        self.language_combo = QComboBox()
        for code, name in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(name, code)
        self.language_combo.activated.connect(self._on_language_changed)
        self.toolbar.addWidget(self.language_combo)

        # Re-openable quick start guide (same content as the first-run
        # onboarding wizard)
        self.guide_button = QPushButton("Quick start")
        self.guide_button.clicked.connect(self.show_quick_start)
        self.toolbar.addWidget(self.guide_button)

        # Device entry: backend picker + the real declared capabilities
        self.toolbar.addSeparator()
        self.device_label = QLabel(" Device:")
        self.toolbar.addWidget(self.device_label)
        self.device_combo = QComboBox()
        for backend in core.list_backends():
            self.device_combo.addItem(backend.display_name, backend.id)
        self.device_combo.activated.connect(self._on_device_changed)
        self.toolbar.addWidget(self.device_combo)
        self.device_info = QLabel("")
        self.toolbar.addWidget(self.device_info)

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
    # Language switching
    # ------------------------------------------------------------------
    def _on_language_changed(self, index):
        code = self.language_combo.itemData(index)
        if not code or code == get_language():
            return
        config_set("language", code)
        set_language(code)
        self._sync_language_combo()
        self.retranslate_ui()

    def _sync_language_combo(self):
        self.language_combo.blockSignals(True)
        idx = self.language_combo.findData(get_language())
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        self.language_combo.blockSignals(False)

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

    def retranslate_ui(self):
        """Re-apply the active language to every visible string."""
        self.setWindowTitle("HJS-Workbench")
        self.toolbar.setWindowTitle(_("Capture controls"))
        self.port_label.setText(_(" Port:"))
        self.refresh_button.setText(_("Refresh ports"))
        self.points_label.setText(_(" Sample points:"))
        self.acquire_button.setText(_("Capture"))
        self.cont_start_button.setText(_("Start continuous"))
        self.cont_stop_button.setText(_("Stop"))
        self.open_button.setText(_("Open file"))
        self.guide_button.setText(_("Quick start"))
        self.tabs.setTabText(0, _("Decode"))
        self.tabs.setTabText(1, _("Measure"))
        self.tabs.setTabText(2, _("Signal"))
        self.device_label.setText(_(" Device:"))
        self._update_device_info()
        self._render_status()
        self._retranslate_port_placeholder()
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
        port = self.port_combo.currentData()
        if port is None:
            QMessageBox.warning(
                self, _("Cannot capture"),
                _("No usable serial port detected. Connect the device data port, then click Refresh ports."),
            )
            return
        points = self.points_spin.value()
        self._start_job(
            core.acquire_serial, (port, points),
            "Capturing {points} points from {port}...",
            points=points, port=port,
        )

    def open_file(self):
        start_dir = resource_path("examples")
        path, _filter = QFileDialog.getOpenFileName(
            self, _("Open capture file"), start_dir, "Capture files (*.sr *.bin);;All files (*)",
        )
        if not path:
            return
        self._start_job(core.acquire_file, (path,), "Reading file...")

    def _start_job(self, fn, args, status_msgid, **status_kwargs):
        self._set_busy(True)
        self._set_status(status_msgid, **status_kwargs)
        self._worker = AcquireWorker(fn, args, parent=self)
        self._worker.succeeded.connect(self._on_success)
        self._worker.failed.connect(self._on_failure)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _set_busy(self, busy):
        for widget in (self.acquire_button, self.open_button,
                       self.refresh_button, self.cont_start_button,
                       self.cont_stop_button):
            widget.setEnabled(not busy)

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
        worker = ContinuousWorker(port, capacity, parent=self)
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
        self.cont_start_button.setEnabled(not running)
        self.cont_stop_button.setEnabled(running)
        for widget in (self.acquire_button, self.open_button,
                       self.refresh_button, self.port_combo,
                       self.points_spin):
            widget.setEnabled(not running)

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
