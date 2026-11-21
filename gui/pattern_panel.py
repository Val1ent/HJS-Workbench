# -*- coding: utf-8 -*-
"""Pattern playback panel: six-channel level sequence editor plus replay.

The panel edits one level byte per cell; bit k of the byte drives GPO
channel k (bit0 PA15 .. bit5 PC11) and every byte is masked to 0x3F
before it reaches the firmware. Playback loads the sequence into the
firmware pattern buffer through the backend's signal connection, replays
it on the real pins, and reads the real capture back; the result is
handed to the main window through the result callback and never faked.

The editing logic that does not depend on Qt lives in module-level pure
functions (masking, per-bit set/get/toggle, length resize, template
build) so the unit tests cover it without a display or any hardware.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

import core
from core.capture import PATTERN_PLAYBACK_RATE
from core.hal import BackendConnectionError, pattern
from core.i18n import _
from core.theme import normalize, tokens

from .worker import AcquireWorker

# Fixed hardware facts of the pattern feature (data, never translated).
CELL_US = 100            # every pattern cell lasts 100 microseconds
MIN_CELLS = 1
MAX_CELLS = pattern.PATTERN_MAX
DEFAULT_CELLS = 100
GPO_ROW_COUNT = 6
CELL_MASK = 0x3F

# GPO channel rows: bit index -> physical pin (bit6/bit7 have no GPO).
GPO_ROWS = [
    "bit0 PA15",
    "bit1 PC7",
    "bit2 PC8",
    "bit3 PC9",
    "bit4 PC10",
    "bit5 PC11",
]


def mask_cell(value):
    """Keep only the six GPO bits of one level byte."""
    return int(value) & CELL_MASK


def masked_cells(values):
    """Mask a whole level sequence to the six GPO bits."""
    return [mask_cell(value) for value in values]


def get_bit(cells, index, bit):
    """True when ``bit`` (0..5) of the cell at ``index`` is high."""
    return bool(mask_cell(cells[index]) & (1 << bit))


def set_bit(cells, index, bit, value):
    """Return a copy of ``cells`` with one GPO bit set or cleared."""
    out = list(cells)
    cell = mask_cell(out[index])
    if value:
        out[index] = cell | (1 << bit)
    else:
        out[index] = cell & ~(1 << bit)
    return out


def toggle_bit(cells, index, bit):
    """Return a copy of ``cells`` with one GPO bit toggled."""
    return set_bit(cells, index, bit, not get_bit(cells, index, bit))


def resize_cells(cells, new_length):
    """Resize a level sequence, keeping the overlapping cells.

    New cells default to 0 and the tail is dropped when shortening.
    """
    if new_length < MIN_CELLS or new_length > MAX_CELLS:
        raise ValueError(
            _("Pattern length must be between {min} and {max} cells."
              ).format(min=MIN_CELLS, max=MAX_CELLS))
    kept = list(cells[:new_length])
    return kept + [0] * (new_length - len(kept))


def template_cells(make_result, max_cells=MAX_CELLS):
    """Mask a decoder test waveform for playback; reject invalid lengths.

    An over-long or empty result raises ``ValueError`` so the caller can
    leave the existing pattern untouched.
    """
    values = masked_cells(make_result)
    if len(values) > max_cells:
        raise ValueError(
            _("Template too long: {n} cells (max {max})"
              ).format(n=len(values), max=max_cells))
    if not values:
        raise ValueError(_("Template is empty"))
    return values


def duration_us(cells):
    """Total playback duration of a sequence in microseconds."""
    return len(cells) * CELL_US


class PatternPanel(QWidget):
    """Connection row, level-sequence editor, and playback controls."""

    def __init__(self, parent=None, result_callback=None):
        super().__init__(parent)
        self._result_callback = result_callback
        self._conn = None
        self._worker = None
        self._closing = False
        self._reconnect_after_playback = False
        self._theme_id = None
        self._cells = [0] * DEFAULT_CELLS
        self._status_msgid = "Not connected"
        self._status_kwargs = {}
        self._result_msgid = ""
        self._result_kwargs = {}
        self._build()
        self._refresh_table()
        self._apply_enables()
        self.retranslate_ui()

    # ------------------------------------------------------------------
    # Building the UI
    # ------------------------------------------------------------------
    def _build(self):
        outer = QVBoxLayout(self)

        # Connection row (same flow as the signal panel): the playback
        # gate is the panel's own signal-baud connection.
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

        # Sequence length and clear action.
        edit_row = QHBoxLayout()
        self.length_label = QLabel("Sequence length")
        edit_row.addWidget(self.length_label)
        self.length_spin = QSpinBox()
        self.length_spin.setRange(MIN_CELLS, MAX_CELLS)
        self.length_spin.setValue(DEFAULT_CELLS)
        self.length_spin.setSuffix(" cells")
        self.length_spin.valueChanged.connect(self._on_length_changed)
        edit_row.addWidget(self.length_spin)
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_pattern)
        edit_row.addWidget(self.clear_button)
        edit_row.addStretch(1)
        outer.addLayout(edit_row)

        # Protocol template picker: decoder ids as item data.
        template_row = QHBoxLayout()
        self.template_label = QLabel("Protocol template")
        template_row.addWidget(self.template_label)
        self.template_combo = QComboBox()
        for name, deck in core.DECKS.items():
            label = f"{name} - {deck['desc']}" if deck.get("desc") else name
            self.template_combo.addItem(label, name)
        template_row.addWidget(self.template_combo, 1)
        self.template_button = QPushButton("Load template")
        self.template_button.clicked.connect(self.load_template)
        template_row.addWidget(self.template_button)
        outer.addLayout(template_row)

        # Editor: one row per GPO channel, one column per cell; a click
        # toggles the level of that cell and channel between 0 and 1.
        self.table = QTableWidget(GPO_ROW_COUNT, DEFAULT_CELLS)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.cellClicked.connect(self._on_cell_clicked)
        outer.addWidget(self.table, 1)

        # Playback, stop, and status.
        play_row = QHBoxLayout()
        self.play_button = QPushButton("Playback")
        self.play_button.clicked.connect(self.start_playback)
        play_row.addWidget(self.play_button)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_playback)
        play_row.addWidget(self.stop_button)
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        play_row.addWidget(self.status_label, 1)
        outer.addLayout(play_row)

        self.refresh_ports()

    # ------------------------------------------------------------------
    # Language
    # ------------------------------------------------------------------
    def retranslate_ui(self):
        """Re-apply the active language to every visible string."""
        self.port_label.setText(_(" Port:"))
        self.refresh_button.setText(_("Refresh ports"))
        self.length_label.setText(_("Sequence length"))
        self.clear_button.setText(_("Clear"))
        self.template_label.setText(_("Protocol template"))
        self.template_button.setText(_("Load template"))
        self.play_button.setText(_("Playback"))
        self.stop_button.setText(_("Stop"))
        self._retranslate_port_placeholder()
        self._render_status()
        self._apply_enables()

    def _retranslate_port_placeholder(self):
        """Re-apply the language to the empty-port placeholder row only."""
        if self.port_combo.count() == 0:
            self.port_combo.addItem(_(" (no serial port detected)"), None)
            self.port_combo.setEnabled(False)
        elif self.port_combo.itemData(0) is None:
            self.port_combo.setItemText(0, _(" (no serial port detected)"))

    def _set_status(self, msgid, **kwargs):
        self._status_msgid = msgid
        self._status_kwargs = kwargs
        self._render_status()

    def _set_result_status(self, msgid, **kwargs):
        self._result_msgid = msgid
        self._result_kwargs = kwargs
        self._render_status()

    def _render_status(self):
        """Connection state, sequence length/duration, and last result."""
        parts = [
            _(self._status_msgid).format(**self._status_kwargs),
            _("Pattern: {n} cells, {us} us").format(
                n=len(self._cells), us=duration_us(self._cells)),
        ]
        if self._result_msgid:
            parts.append(_(self._result_msgid).format(**self._result_kwargs))
        self.status_label.setText("  |  ".join(parts))

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------
    def _cell_colors(self):
        """Black/white/gray level colors from the theme tokens only."""
        tok = tokens(self._theme_id)
        return {
            "high_bg": tok["text"],
            "high_fg": tok["window"],
            "low_bg": tok["alternate"],
            "low_fg": tok["muted"],
        }

    def apply_theme(self, theme_id):
        """Re-color the level cells from the active theme tokens."""
        self._theme_id = normalize(theme_id)
        self._refresh_table()

    # ------------------------------------------------------------------
    # Level editor
    # ------------------------------------------------------------------
    def _refresh_table(self):
        """Rebuild the editor grid from the authoritative ``_cells``."""
        self.table.setRowCount(GPO_ROW_COUNT)
        self.table.setColumnCount(len(self._cells))
        self.table.setVerticalHeaderLabels(GPO_ROWS)
        self.table.setHorizontalHeaderLabels(
            [str(i) for i in range(1, len(self._cells) + 1)])
        for col in range(len(self._cells)):
            for row in range(GPO_ROW_COUNT):
                self._update_cell_item(row, col)

    def _update_cell_item(self, row, col):
        """Sync one cell item with the level of bit ``row`` in cell
        ``col``."""
        colors = self._cell_colors()
        high = get_bit(self._cells, col, row)
        item = self.table.item(row, col)
        if item is None:
            item = QTableWidgetItem()
            self.table.setItem(row, col, item)
        item.setText("1" if high else "0")
        item.setTextAlignment(Qt.AlignCenter)
        item.setBackground(
            QBrush(QColor(colors["high_bg" if high else "low_bg"])))
        item.setForeground(
            QBrush(QColor(colors["high_fg" if high else "low_fg"])))

    def _on_cell_clicked(self, row, col):
        self._cells = toggle_bit(self._cells, col, row)
        self._update_cell_item(row, col)

    def _on_length_changed(self, value):
        if value == len(self._cells):
            return
        self._cells = resize_cells(self._cells, value)
        self._refresh_table()
        self._render_status()

    def clear_pattern(self):
        """Set every channel of every cell to 0."""
        self._cells = [0] * len(self._cells)
        self._refresh_table()
        self._set_result_status("")

    def load_template(self):
        """Overwrite the pattern with a masked decoder test waveform."""
        name = self.template_combo.currentData()
        if not name:
            return
        try:
            values = core.DECKS[name]["make"](PATTERN_PLAYBACK_RATE)
        except Exception as exc:
            QMessageBox.warning(
                self, _("Template load failed"), str(exc).strip())
            return
        try:
            cells = template_cells(values)
        except ValueError as exc:
            QMessageBox.warning(self, _("Template load failed"), str(exc))
            return
        self._cells = cells
        self.length_spin.blockSignals(True)
        self.length_spin.setValue(len(cells))
        self.length_spin.blockSignals(False)
        self._refresh_table()
        self._set_result_status("")
        self._render_status()

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
            self.connect_pattern_port()

    def connect_pattern_port(self):
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
        self._apply_enables()

    def _apply_enables(self):
        busy = self._worker is not None and self._worker.isRunning()
        connected = self._conn is not None
        self.play_button.setEnabled(connected and not busy)
        self.stop_button.setEnabled(connected and not busy)
        self.template_button.setEnabled(self.template_combo.count() > 0)

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------
    def start_playback(self):
        """Play the edited sequence in a background thread.

        The playback flow opens its own long signal connection, so the
        panel connection releases the port first and is re-opened when
        the worker finishes.
        """
        if self._conn is None:
            QMessageBox.warning(
                self, _("Not connected"),
                _("Connect the pattern port before playing back."))
            return
        port = self.port_combo.currentData()
        cells = list(self._cells)
        self._reconnect_after_playback = True
        self.disconnect()
        self._set_status("Playback started")
        self._worker = AcquireWorker(
            core.playback_pattern, (port, cells), parent=self)
        self._worker.succeeded.connect(self._on_playback_succeeded)
        self._worker.failed.connect(self._on_playback_failed)
        self._worker.finished.connect(self._on_playback_finished)
        self._worker.start()

    def stop_playback(self):
        """Force every GPO low on the established panel connection."""
        if self._conn is None:
            return
        try:
            pattern.stop(self._conn)
        except Exception as exc:
            QMessageBox.warning(self, _("Playback failed"), str(exc).strip())
            return
        self._set_status("Forced all GPO channels low")

    def _on_playback_succeeded(self, rate, samples):
        if self._closing:
            return
        self._set_result_status(
            "Playback captured {n} points ({rate} Hz)",
            n=len(samples), rate=rate)
        callback = self._result_callback
        if callback is not None:
            callback(rate, samples)

    def _on_playback_failed(self, message):
        if self._closing:
            return
        QMessageBox.warning(self, _("Playback failed"), message)
        self._set_result_status("Playback failed")

    def _on_playback_finished(self):
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        if self._closing:
            return
        if self._reconnect_after_playback:
            self._reconnect_after_playback = False
            self._reconnect_panel_port()
        self._apply_enables()

    def _reconnect_panel_port(self):
        """Restore the panel connection that playback released."""
        port = self.port_combo.currentData()
        if port is None:
            return
        try:
            self._conn = core.current_backend().connect(
                port, baud=core.current_backend().capabilities.signal_baud)
        except BackendConnectionError:
            self._conn = None
            self._set_status("Playback failed")
            return
        self._set_connected(True)

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------
    def shutdown(self):
        """Force GPOs low, join the worker, and release the port."""
        self._closing = True
        if self._conn is not None:
            try:
                pattern.stop(self._conn)
            except Exception:
                pass
        worker = self._worker
        if worker is not None and worker.isRunning():
            waited = 0.0
            while worker.isRunning() and waited < 20.0:
                worker.wait(100)
                waited += 0.1
                QApplication.processEvents()
        self._worker = None
        self.disconnect()
