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

The plot colors (background, foreground, axis pens, grid, and the
per-channel palette) come from the theme tokens in ``core.theme``;
``apply_theme`` re-colors an already visible plot at runtime.
"""
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from core.hal import current_backend
from core.i18n import _
from core.theme import get_theme, tokens

BASE = 1.0        # Baseline spacing between adjacent channels
HEIGHT = 0.7      # Height of the high level above the baseline

ZOOM_IN_FACTOR = 0.8    # Zoom in multiplies the x range by this factor
ZOOM_OUT_FACTOR = 1.25  # Zoom out multiplies the x range by this factor


class WaveformView(QWidget):
    """Digital waveform plot for the current backend's channels. Call
set_data(rate, samples) to update the display."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._x_full = (0.0, 1.0)

        self.zoom_in_button = QPushButton(_("Zoom in"))
        self.zoom_in_button.setToolTip(_("Zoom in on the time axis"))
        self.zoom_out_button = QPushButton(_("Zoom out"))
        self.zoom_out_button.setToolTip(_("Zoom out on the time axis"))
        self.fit_button = QPushButton(_("Fit"))
        self.fit_button.setToolTip(_("Fit to all data"))
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.fit_button.clicked.connect(self.fit_all)

        strip = QHBoxLayout()
        strip.setContentsMargins(0, 0, 0, 0)
        strip.addWidget(self.zoom_in_button)
        strip.addWidget(self.zoom_out_button)
        strip.addWidget(self.fit_button)
        strip.addStretch(1)

        self.plot = pg.PlotWidget()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(strip)
        layout.addWidget(self.plot)

        self.plot.setLabel("bottom", _("Time"), units="s")
        self.plot.setLabel("left", _("Channel"))
        self.plot.setMouseEnabled(x=True, y=False)
        self.plot.getViewBox().setMouseMode(pg.ViewBox.PanMode)

        self._curves = []
        self._channel_names = []
        self._n_channels = 0
        self._ch_colors = list(tokens()["channels"])
        self.apply_theme(get_theme())
        self.refresh_channels()

    # ------------------------------------------------------------------
    # Zoom controls
    # ------------------------------------------------------------------
    def zoom_in(self):
        """Magnify the time axis around the current view center; the
        channel axis stays unchanged."""
        self.plot.getViewBox().scaleBy((ZOOM_IN_FACTOR, 1.0))

    def zoom_out(self):
        """Widen the time axis around the current view center; the
        channel axis stays unchanged."""
        self.plot.getViewBox().scaleBy((ZOOM_OUT_FACTOR, 1.0))

    def fit_all(self):
        """Restore the full captured time range (a valid empty view when
        no data has been loaded)."""
        self.plot.setXRange(self._x_full[0], self._x_full[1], padding=0)

    def apply_theme(self, theme_id):
        """Re-color the plot for a theme: background, foreground, axis
        pens, grid, and the per-channel curve colors."""
        tok = tokens(theme_id)
        self._ch_colors = list(tok["channels"])

        self.plot.setBackground(tok["plot_background"])
        self.plot.plotItem.vb.setBackgroundColor(tok["plot_background"])
        for name in ("left", "bottom", "top", "right"):
            axis = self.plot.getAxis(name)
            axis.setPen(pg.mkPen(tok["plot_foreground"]))
            axis.setTextPen(pg.mkPen(tok["plot_foreground"]))
            axis.setTickPen(pg.mkPen(tok["grid"]))
        self.plot.showGrid(x=True, y=True, alpha=tok["grid_alpha"])

        for ch, curve in enumerate(self._curves):
            color = self._ch_colors[ch % len(self._ch_colors)]
            curve.setPen(pg.mkPen(color, width=1.2))

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
            color = self._ch_colors[ch % len(self._ch_colors)]
            curve = self.plot.plot(
                [], [],
                pen=pg.mkPen(color, width=1.2),
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
        """Re-apply the active language to the axis labels and the zoom
        buttons."""
        self.plot.setLabel("bottom", _("Time"), units="s")
        self.plot.setLabel("left", _("Channel"))
        self.zoom_in_button.setText(_("Zoom in"))
        self.zoom_in_button.setToolTip(_("Zoom in on the time axis"))
        self.zoom_out_button.setText(_("Zoom out"))
        self.zoom_out_button.setToolTip(_("Zoom out on the time axis"))
        self.fit_button.setText(_("Fit"))
        self.fit_button.setToolTip(_("Fit to all data"))

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
            self._x_full = (0.0, 1.0)
            self.plot.setXRange(0, 1)
            return
        x = np.arange(n, dtype=np.float64) / rate
        arr = np.asarray(samples, dtype=np.uint8)
        for ch in range(nch):
            levels = ((arr >> ch) & 1).astype(np.float64)
            px, py = self._square_points(x, levels)
            y_base = BASE * (nch - 1 - ch)
            self._curves[ch].setData(px, py * HEIGHT + y_base)
        self._x_full = (0.0, n / rate)
        self.plot.setXRange(0, n / rate, padding=0)
