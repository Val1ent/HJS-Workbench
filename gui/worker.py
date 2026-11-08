# -*- coding: utf-8 -*-
"""Background acquisition threads: run blocking serial capture / file
reads in worker threads to keep the UI responsive.

``AcquireWorker`` runs one one-shot capture callable. ``ContinuousWorker``
keeps one HAL connection open and streams throttled snapshots of the
incoming data until it is asked to stop; it contains no serial code of
its own and only talks to the current backend's DeviceConnection.
"""
from collections import deque
import time

from PySide6.QtCore import QThread, Signal

from core.hal import current_backend
from core.i18n import _


def readable_error(exc):
    """Turn an exception into one user-facing line (no stack trace)."""
    text = str(exc).strip()
    if text:
        return text
    return _("{type} (no details)").format(type=type(exc).__name__)


class AcquireWorker(QThread):
    """Run a callable in a background thread and report the result via
    signals.

    On success emits succeeded(int, list) with (rate, samples);
    on failure emits failed(str) with a readable error message.
    """

    succeeded = Signal(int, list)
    failed = Signal(str)

    def __init__(self, fn, args=(), parent=None):
        super().__init__(parent)
        self._fn = fn
        self._args = args

    def run(self):
        try:
            rate, samples = self._fn(*self._args)
        except Exception as exc:
            self.failed.emit(readable_error(exc))
        else:
            self.succeeded.emit(rate, samples)


# Throttle interval for continuous snapshots: the waveform refreshes
# roughly every 150 ms, well inside the required 100-200 ms window.
SNAPSHOT_INTERVAL = 0.15
# The rolling window holds at most one second of 10 kHz data; the
# capacity is raised by the GUI to its configured sample point count.
CONTINUOUS_CAPACITY = 20000


class ContinuousWorker(QThread):
    """Stream capture from a real device into a rolling deque.

    The worker opens the current backend's connection exactly once, then
    repeatedly calls ``read_available()`` and appends the bytes to a
    fixed-capacity rolling deque. About every ``SNAPSHOT_INTERVAL``
    seconds it emits ``snapshot(int, list)`` with the backend's declared
    sample rate and a copy of the current window. Calling ``stop()``
    ends the loop; the worker closes the connection (releasing the port)
    before the thread finishes.
    """

    snapshot = Signal(int, list)
    failed = Signal(str)

    def __init__(self, port, capacity=CONTINUOUS_CAPACITY, parent=None):
        super().__init__(parent)
        self._port = port
        self._capacity = max(1, int(capacity))
        self._stop_flag = False
        self._conn = None

    def stop(self):
        """Ask the worker to stop; the thread exits within one poll tick
        and closes the connection itself."""
        self._stop_flag = True

    def run(self):
        backend = current_backend()
        try:
            conn = backend.connect(self._port)
        except Exception as exc:
            self.failed.emit(readable_error(exc))
            return
        self._conn = conn
        rate = backend.capabilities.sample_rate
        window = deque(maxlen=self._capacity)
        last = 0.0
        try:
            while not self._stop_flag:
                try:
                    chunk = conn.read_available()
                except Exception as exc:  # noqa: BLE001 - readable report
                    self.failed.emit(readable_error(exc))
                    break
                if chunk:
                    window.extend(chunk)
                now = time.monotonic()
                if window and now - last >= SNAPSHOT_INTERVAL:
                    last = now
                    self.snapshot.emit(rate, list(window))
                time.sleep(0.01)
        finally:
            try:
                conn.close()
            except Exception:
                pass
            self._conn = None
