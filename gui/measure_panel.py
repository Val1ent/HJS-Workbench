# -*- coding: utf-8 -*-
"""Measure panel: per-channel frequency/duty overview + main channel detailed
metrics. The channel count and names come from the current backend."""
import core

from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QHeaderView, QLabel, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from core.i18n import _

# (display label msgid, data key, unit symbol). Keys and units stay English;
# only the display label is passed through _() during setup and retranslation.
DETAIL_FIELDS = [
    ("Frequency", "freq", "Hz"),
    ("Period", "period", "ms"),
    ("High pulse width", "high", "ms"),
    ("Low pulse width", "low", "ms"),
    ("Duty", "duty", "%"),
    ("Min period", "pmin", "ms"),
    ("Max period", "pmax", "ms"),
    ("Cycles counted", "cycles", ""),
]


def _headers():
    """Overview table headers; unit symbols stay as-is."""
    return [_("Channel"), _("Frequency") + "(Hz)", _("Duty") + "(%)"]


class MeasurePanel(QWidget):
    """Per-channel frequency/duty table plus the main channel's detailed
metrics; both derive their rows from the current backend."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_result = None
        self._has_data = False
        self._channel_names = []
        self._n_channels = 0

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(_headers())
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)

        self.detail_box = QGroupBox("")
        self.detail_form = QFormLayout(self.detail_box)
        self.detail_labels = {}
        self.detail_row_labels = {}
        for title, _key, unit in DETAIL_FIELDS:
            value_label = QLabel("--")
            row_label = QLabel(f"{_(title)}:")
            self.detail_form.addRow(row_label, value_label)
            self.detail_labels[_key] = (value_label, unit)
            self.detail_row_labels[_key] = row_label

        layout = QVBoxLayout(self)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.detail_box)
        self.refresh_channels()

    def refresh_channels(self):
        """Rebuild the channel rows and the detail box title from the
current backend's capabilities."""
        caps = core.current_backend().capabilities
        self._channel_names = list(caps.channel_names)
        self._n_channels = len(self._channel_names)
        self.table.setRowCount(self._n_channels)
        for ch in range(self._n_channels):
            self.table.setItem(ch, 0, QTableWidgetItem(self._channel_names[ch]))
            self.table.setItem(ch, 1, QTableWidgetItem("--"))
            self.table.setItem(ch, 2, QTableWidgetItem("--"))
        self.detail_box.setTitle(
            _("{ch} details").format(ch=self._channel_names[0]))

    def retranslate_ui(self):
        """Re-apply the active language to all panel strings."""
        self.table.setHorizontalHeaderLabels(_headers())
        self.detail_box.setTitle(
            _("{ch} details").format(ch=self._channel_names[0]))
        for title, key, _unit in DETAIL_FIELDS:
            self.detail_row_labels[key].setText(f"{_(title)}:")
        if self._has_data:
            self._update_detail(self._last_result)

    def _update_row(self, ch, result):
        if result is None:
            self.table.item(ch, 1).setText("--")
            self.table.item(ch, 2).setText("--")
        else:
            self.table.item(ch, 1).setText(f"{result['freq']:.1f}")
            self.table.item(ch, 2).setText(f"{result['duty']:.1f}")

    def _update_detail(self, result):
        self._last_result = result
        if result is None:
            for _key, (label, _unit) in self.detail_labels.items():
                label.setText(_("insufficient signal"))
            return
        for _title, key, _unit in DETAIL_FIELDS:
            label, unit = self.detail_labels[key]
            if key == "cycles":
                label.setText(str(result[key]))
            elif unit == "ms":
                label.setText(f"{result[key] * 1000:.3f}")
            elif unit == "%":
                label.setText(f"{result[key]:.1f}")
            else:
                label.setText(f"{result[key]:.1f}")

    def set_data(self, rate, samples):
        """Measure every backend channel separately and refresh the table
and the main channel's detail area."""
        self._has_data = True
        n = len(samples)
        for ch in range(self._n_channels):
            bits = [1 if (s >> ch) & 1 else 0 for s in samples]
            if n < 2:
                result = None
            else:
                result = core.measure(bits, rate)
            self._update_row(ch, result)
            if ch == 0:
                self._update_detail(result)
