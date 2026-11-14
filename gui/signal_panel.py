# -*- coding: utf-8 -*-
"""Signal generator panel: drives the real firmware signal modes over
the backend's signal connection.

The firmware on the CH32 board accepts ``U`` (software UART), ``S<freq>``
(50% square wave), ``P<freq>,<duty>`` (PWM, duty in percent),
``B<freq>,<count>`` (a burst of exactly ``count`` pulses), and ``H``/``L``
(forced level). The panel exposes exactly these modes; every numeric
input is bounded to the firmware limits (1-5000 Hz, 1-99 percent duty,
1-65535 pulses) and the matching command line is written through the HAL
connection at the backend's declared signal baud rate. No other option
is offered, and the port is released when the panel is closed or the
window exits.
"""
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

import core
from core.hal import BackendConnectionError
from core.i18n import _

FREQ_MIN = 1
FREQ_MAX = 5000
FREQ_DEFAULT = 1000
DUTY_MIN = 1
DUTY_MAX = 99
DUTY_DEFAULT = 50
COUNT_MIN = 1
COUNT_MAX = 65535
COUNT_DEFAULT = 10

# Mode ids (data, never translated) -> command builder.
MODE_UART = "uart"
MODE_SQUARE = "square"
MODE_PWM = "pwm"
MODE_BURST = "burst"
MODE_HIGH = "high"
MODE_LOW = "low"


class SignalPanel(QWidget):
    """Signal-generator controls plus a signal-port connection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._conn = None
        self._status_msgid = "Not connected"
        self._status_kwargs = {}
        self._build()
        self._apply_mode_enables()
        self.retranslate_ui()

    # ------------------------------------------------------------------
    # Building the UI
    # ------------------------------------------------------------------
    def _build(self):
        outer = QVBoxLayout(self)

        # Connection row
        port_row = QHBoxLayout()
        self.port_label = QLabel(" Port:")
        port_row.addWidget(self.port_label)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(260)
        port_row.addWidget(self.port_combo)
        self.refresh_button = QPushButton("Refresh ports")
        self.refresh_button.clicked.connect(self.refresh_ports)
        port_row.addWidget(self.refresh_button)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)
        port_row.addWidget(self.connect_button)
        port_row.addStretch(1)
        outer.addLayout(port_row)

        # Signal parameters
        form = QFormLayout()
        self.mode_combo = QComboBox()
        for label, mode_id in (
                ("Software UART", MODE_UART),
                ("Square wave", MODE_SQUARE),
                ("PWM", MODE_PWM),
                ("Burst", MODE_BURST),
                ("Force high", MODE_HIGH),
                ("Force low", MODE_LOW)):
            self.mode_combo.addItem(label, mode_id)
        self.mode_combo.currentIndexChanged.connect(self._apply_mode_enables)
        self.mode_label = QLabel("Mode")
        form.addRow(self.mode_label, self.mode_combo)

        self.freq_spin = QSpinBox()
        self.freq_spin.setRange(FREQ_MIN, FREQ_MAX)
        self.freq_spin.setValue(FREQ_DEFAULT)
        self.freq_spin.setSuffix(" Hz")
        self.freq_label = QLabel("Frequency")
        form.addRow(self.freq_label, self.freq_spin)

        self.duty_spin = QSpinBox()
        self.duty_spin.setRange(DUTY_MIN, DUTY_MAX)
        self.duty_spin.setValue(DUTY_DEFAULT)
        self.duty_spin.setSuffix(" %")
        self.duty_label = QLabel("Duty cycle")
        form.addRow(self.duty_label, self.duty_spin)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(COUNT_MIN, COUNT_MAX)
        self.count_spin.setValue(COUNT_DEFAULT)
        self.count_spin.setSuffix(" pulses")
        self.count_label = QLabel("Pulse count")
        form.addRow(self.count_label, self.count_spin)
        outer.addLayout(form)

        send_row = QHBoxLayout()
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send)
        send_row.addWidget(self.send_button)
        self.status_label = QLabel("")
        send_row.addWidget(self.status_label, 1)
        outer.addLayout(send_row)
        outer.addStretch(1)

        self.refresh_ports()

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------
    def retranslate_ui(self):
        """Re-apply the active language to every visible string."""
        index = self.mode_combo.currentIndex()
        mode_id = self.mode_combo.itemData(index)
        labels = {
            MODE_UART: _("Software UART"),
            MODE_SQUARE: _("Square wave"),
            MODE_PWM: _("PWM"),
            MODE_BURST: _("Burst"),
            MODE_HIGH: _("Force high"),
            MODE_LOW: _("Force low"),
        }
        for i in range(self.mode_combo.count()):
            self.mode_combo.setItemText(i, labels[self.mode_combo.itemData(i)])
        if mode_id is not None:
            self.mode_combo.setCurrentIndex(index)
        self.port_label.setText(_(" Port:"))
        self.mode_label.setText(_("Mode"))
        self.freq_label.setText(_("Frequency"))
        self.duty_label.setText(_("Duty cycle"))
        self.count_label.setText(_("Pulse count"))
        self.refresh_button.setText(_("Refresh ports"))
        if self._conn is not None:
            self.connect_button.setText(_("Disconnect"))
        else:
            self.connect_button.setText(_("Connect"))
        self.send_button.setText(_("Send"))
        self._render_status()

    def _set_status(self, msgid, **kwargs):
        self._status_msgid = msgid
        self._status_kwargs = kwargs
        self._render_status()

    def _render_status(self):
        self.status_label.setText(
            _(self._status_msgid).format(**self._status_kwargs))

    # ------------------------------------------------------------------
    # Port handling
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

    def toggle_connection(self):
        if self._conn is not None:
            self.disconnect()
        else:
            self.connect_signal_port()

    def connect_signal_port(self):
        port = self.port_combo.currentData()
        if port is None:
            QMessageBox.warning(
                self, _("Cannot connect"),
                _("No usable serial port detected. Connect the device, then click Refresh ports."),
            )
            return
        caps = core.current_backend().capabilities
        try:
            self._conn = core.current_backend().connect(
                port, baud=caps.signal_baud)
        except BackendConnectionError as exc:
            QMessageBox.warning(
                self, _("Cannot connect"),
                _("Failed to open the serial port (close the serial monitor and retry): {error}"
                  ).format(error=exc))
            return
        self._set_connected(True)
        self._set_status("Connected to {port}", port=port)

    def disconnect(self):
        if self._conn is None:
            return
        try:
            self._conn.close()
        except Exception:
            pass
        self._conn = None
        self._set_connected(False)
        self._set_status("Not connected")

    def _set_connected(self, connected):
        self.port_combo.setEnabled(not connected)
        self.refresh_button.setEnabled(not connected)
        self.connect_button.setText(_("Disconnect") if connected
                                    else _("Connect"))
        self.send_button.setEnabled(connected)

    # ------------------------------------------------------------------
    # Sending commands
    # ------------------------------------------------------------------
    def _apply_mode_enables(self):
        mode_id = self.mode_combo.currentData()
        self.freq_spin.setEnabled(mode_id in (MODE_SQUARE, MODE_PWM,
                                              MODE_BURST))
        self.duty_spin.setEnabled(mode_id == MODE_PWM)
        self.count_spin.setEnabled(mode_id == MODE_BURST)

    def command_line(self, mode_id, freq, duty, count):
        """Build the exact firmware command line for a mode.

        The command line is wire data (English by rule); frequencies,
        duty, and count are bounded to the firmware limits by the callers.
        """
        if mode_id == MODE_UART:
            return b"U\n"
        if mode_id == MODE_SQUARE:
            return f"S{freq}\n".encode("ascii")
        if mode_id == MODE_PWM:
            return f"P{freq},{duty}\n".encode("ascii")
        if mode_id == MODE_BURST:
            return f"B{freq},{count}\n".encode("ascii")
        if mode_id == MODE_HIGH:
            return b"H\n"
        if mode_id == MODE_LOW:
            return b"L\n"
        raise ValueError(f"unknown signal mode {mode_id}")

    def send(self):
        if self._conn is None:
            QMessageBox.warning(
                self, _("Not connected"),
                _("Connect the signal port before sending a command."))
            return
        mode_id = self.mode_combo.currentData()
        freq = self.freq_spin.value()
        duty = self.duty_spin.value()
        count = self.count_spin.value()
        if not (FREQ_MIN <= freq <= FREQ_MAX):
            QMessageBox.warning(
                self, _("Invalid frequency"),
                _("Frequency must be between {min} and {max} Hz.").format(
                    min=FREQ_MIN, max=FREQ_MAX))
            return
        if mode_id == MODE_PWM and not (DUTY_MIN <= duty <= DUTY_MAX):
            QMessageBox.warning(
                self, _("Invalid duty cycle"),
                _("Duty cycle must be between {min} and {max} percent."
                  ).format(min=DUTY_MIN, max=DUTY_MAX))
            return
        if mode_id == MODE_BURST and not (COUNT_MIN <= count <= COUNT_MAX):
            QMessageBox.warning(
                self, _("Invalid pulse count"),
                _("Pulse count must be between {min} and {max}.").format(
                    min=COUNT_MIN, max=COUNT_MAX))
            return
        line = self.command_line(mode_id, freq, duty, count)
        try:
            self._conn.write(line)
        except Exception as exc:
            QMessageBox.warning(
                self, _("Send failed"), str(exc).strip())
            return
        self._set_status("Sent: {line}", line=line.decode("ascii").strip())

    def shutdown(self):
        """Release the signal port (window close / panel teardown)."""
        self.disconnect()
