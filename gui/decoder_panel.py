# -*- coding: utf-8 -*-
"""Decode panel: built-in UART text decoding (first channel, 8N1) + the 9
registered decoders, results listed in a table."""
import core

from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
from core.i18n import _


def _headers():
    """Table column headers in the active language."""
    return [_("Time(ms)"), _("Channel"), _("Type"), _("Content")]


class DecoderPanel(QWidget):
    """Choose a decoder and run it; events are shown in the table in time order."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rate = 0
        self._samples = []
        self._last_event_count = None

        self.decoder_combo = QComboBox()
        self.decoder_combo.addItem(
            _("UART text ({ch}, 8N1)").format(
                ch=core.current_backend().capabilities.channel_names[0]),
            None)
        for name, deck in core.DECKS.items():
            label = f"{name} - {deck['desc']}" if deck.get("desc") else name
            self.decoder_combo.addItem(label, name)

        self.run_button = QPushButton(_("Run decode"))
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_decode)

        self.decoder_label = QLabel(_("Decoder:"))
        top = QHBoxLayout()
        top.addWidget(self.decoder_label)
        top.addWidget(self.decoder_combo, 1)
        top.addWidget(self.run_button)

        self.table = QTableWidget(0, len(_headers()))
        self.table.setHorizontalHeaderLabels(_headers())
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.status_label)

    def retranslate_ui(self):
        """Re-apply the active language to all panel strings."""
        self.decoder_combo.setItemText(
            0, _("UART text ({ch}, 8N1)").format(
                ch=core.current_backend().capabilities.channel_names[0]))
        self.run_button.setText(_("Run decode"))
        self.decoder_label.setText(_("Decoder:"))
        self.table.setHorizontalHeaderLabels(_headers())
        if self._last_event_count:
            self.status_label.setText(
                _("Decoded {n} events").format(n=self._last_event_count))
        elif self._last_event_count == 0:
            self.status_label.setText(_("No events decoded"))

    def set_data(self, rate, samples):
        """Store the current data; clear old decode results (no automatic rerun)."""
        self._rate = rate
        self._samples = list(samples)
        self.clear_results()
        self.run_button.setEnabled(bool(self._samples) and rate > 0)

    def clear_results(self):
        self.table.setRowCount(0)
        self._last_event_count = None
        self.status_label.setText("")

    def _run_uart(self):
        bits = [s & 1 for s in self._samples]          # first channel
        events = []
        for start, char in core.scan_frames(bits):
            events.append({
                "t": start / self._rate,
                "ch": 0,
                "type": "char",
                "text": char,
            })
        return events

    def run_decode(self):
        if not self._samples or self._rate <= 0:
            return
        name = self.decoder_combo.currentData()
        try:
            if name is None:
                events = self._run_uart()
            else:
                events = core.DECKS[name]["decode"](self._samples, self._rate)
        except Exception as exc:
            QMessageBox.warning(self, _("Decode failed"), str(exc))
            return
        events.sort(key=lambda e: e["t"])
        self.table.setRowCount(0)
        self.table.setRowCount(len(events))
        for row, ev in enumerate(events):
            items = [
                QTableWidgetItem(f"{ev['t'] * 1000:.3f}"),
                QTableWidgetItem(f"D{ev['ch']}"),
                QTableWidgetItem(str(ev["type"])),
                QTableWidgetItem(str(ev["text"])),
            ]
            for col, item in enumerate(items):
                self.table.setItem(row, col, item)
        if events:
            self._last_event_count = len(events)
            self.status_label.setText(
                _("Decoded {n} events").format(n=len(events)))
        else:
            self._last_event_count = 0
            self.status_label.setText(_("No events decoded"))
