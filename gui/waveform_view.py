# -*- coding: utf-8 -*-
"""Multi-channel digital waveform widget (based on pyqtgraph).

Each channel is drawn as a standard digital square wave: horizontal
segments show the level, and level changes are vertical transition
edges. The channel count and names come from the current device
backend; the first channel is at the top and the last at the bottom,
with channel labels on the left. Each channel waveform is first
compressed by level runs (RLE), then drawn with a connect='pairs'
PlotCurveItem, avoiding per-point addItem so that thousands to 20000
points still zoom smoothly.
"""
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QVBoxLayout, QWidget

from core.hal import current_backend
from core.i18n import _

CH_COLORS = [
    "#e6194b", "#3cb44b", "#4363d8", "#f58231",
    "#911eb4", "#42d4f4", "#f032e6", "#bfef45",
]
BASE = 1.0        # Baseline spacing between adjacent channels
HEIGHT = 0.7      # Height of the high level above the baseline


class WaveformView(QWidget):
    """Digital waveform plot for the current backend's channels. Call
set_data(rate, samples) to update the display."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plot = pg.PlotWidget()
        layout.addWidget(self.plot)

        self.plot.showGrid(x=True, y=True, alpha=0.3)
        self.plot.setLabel("bottom", _("Time"), units="s")
        self.plot.setLabel("left", _("Channel"))
        self.plot.setMouseEnabled(x=True, y=False)
        self.plot.getViewBox().setMouseMode(pg.ViewBox.PanMode)

        self._curves = []
        self._channel_names = []
        self._n_channels = 0
        self.refresh_channels()

    def refresh_channels(self):
        """Rebuild the channel curves and labels from the current backend."""
        caps = current_backend().capabilities
        self._channel_names = list(caps.channel_names)
        self._n_channels = len(self._channel_names)
        for curve in self._curves:
            self.plot.removeItem(curve)
        self._curves = []
        n = self._n_channels
        for ch in range(n):
            curve = self.plot.plot(
                [], [],
                pen=pg.mkPen(CH_COLORS[ch % len(CH_COLORS)], width=1.2),
                connect="pairs",
            )
            curve.setClipToView(True)
            self._curves.append(curve)

        # Left y-axis ticks: channel names from top to bottom, at the
        # midpoint of each channel's level band
        ticks = [
            (BASE * (n - 1 - ch) + HEIGHT / 2.0, self._channel_names[ch])
            for ch in range(n)
        ]
        self.plot.getAxis("left").setTicks([ticks])
        self.plot.setYRange(-0.2, BASE * (n - 1) + HEIGHT + 0.2)

    def retranslate_ui(self):
        """Re-apply the active language to the axis labels."""
        self.plot.setLabel("bottom", _("Time"), units="s")
        self.plot.setLabel("left", _("Channel"))

    @staticmethod
    def _square_points(x, levels):
        """Convert a 0/1 level sequence into square-wave polyline vertices
        with vertical transition edges.

        Returns (px, py): adjacent points are connected; the polyline
        alternates horizontal and vertical segments, drawn as point pairs
        by connect='pairs'.
        """
        n = len(levels)
        if n == 0:
            return np.zeros(0), np.zeros(0)
        dt = x[1] - x[0] if n > 1 else 0.0
        changed = np.empty(n, dtype=bool)
        changed[0] = True
        changed[1:] = levels[1:] != levels[:-1]
        idx = np.nonzero(changed)[0]          # Start of each level run
        run_end = np.empty(len(idx), dtype=np.float64)
        if len(idx) > 1:
            run_end[:-1] = x[idx[1:] - 1] + dt
        run_end[-1] = x[-1] + dt
        run_lvl = levels[idx]

        # Vertex sequence: each run contributes (start, level) and
        # (end, level); adjacent runs touch end to start, and the segment
        # between the two points is the vertical transition edge.
        vx = np.empty(2 * len(idx), dtype=np.float64)
        vy = np.empty(2 * len(idx), dtype=np.float64)
        vx[0::2] = x[idx]
        vx[1::2] = run_end
        vy[0::2] = run_lvl
        vy[1::2] = run_lvl
        # Duplicate the middle vertices once so adjacent point pairs form
        # exactly the segments
        px = np.repeat(vx, 2)[1:-1]
        py = np.repeat(vy, 2)[1:-1]
        return px, py

    def set_data(self, rate, samples):
        """Redraw the waveform for every backend channel from (rate, samples)
and zoom to all the data."""
        n = len(samples)
        nch = self._n_channels
        if n == 0 or rate <= 0 or nch == 0:
            for curve in self._curves:
                curve.setData([], [])
            self.plot.setXRange(0, 1)
            return
        x = np.arange(n, dtype=np.float64) / rate
        arr = np.asarray(samples, dtype=np.uint8)
        for ch in range(nch):
            levels = ((arr >> ch) & 1).astype(np.float64)
            px, py = self._square_points(x, levels)
            y_base = BASE * (nch - 1 - ch)
            self._curves[ch].setData(px, py * HEIGHT + y_base)
        self.plot.setXRange(0, n / rate, padding=0)
