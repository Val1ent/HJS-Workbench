# -*- coding: utf-8 -*-
"""Tests for the pattern playback session: masked bytes, ordered writes,
non-blocking polling, and a closed connection on every path.

The fake connection only records writes and serves preset bytes; it is
never registered in ``core.hal.BACKENDS`` and never opens a real port.
"""
import unittest
from unittest import mock

from core import capture
from core.hal import pattern


class FakeConnection:
    """Record writes and serve preset read bytes (no real port)."""

    def __init__(self, read_chunks=(), read_error=None, write_error=None,
                 stop_error=False):
        self.writes = []
        self.closed = False
        self.reset_count = 0
        self._chunks = list(read_chunks)
        self._read_error = read_error
        self._write_error = write_error
        self._stop_error = stop_error

    def write(self, data):
        if self._write_error is not None:
            raise self._write_error
        if self._stop_error and bytes(data) == b"L":
            raise OSError("stop failed")
        self.writes.append(bytes(data))

    def read_available(self):
        if self._read_error is not None:
            raise self._read_error
        if self._chunks:
            return self._chunks.pop(0)
        return b""

    def reset_input(self):
        self.reset_count += 1

    def close(self):
        self.closed = True


class FakeBackend:
    """Stand-in backend that returns one prepared connection."""

    def __init__(self, conn):
        self._conn = conn
        self.capabilities = type("Caps", (), {"signal_baud": 921600})()

    def connect(self, port, baud=None):
        self.last_port = port
        self.last_baud = baud
        return self._conn


class PlaybackPatternTest(unittest.TestCase):
    def setUp(self):
        self.conn = FakeConnection()
        self.backend = FakeBackend(self.conn)
        patcher = mock.patch.object(
            capture, "current_backend", return_value=self.backend)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.sleep_patcher = mock.patch("time.sleep")
        self.sleep_patcher.start()
        self.addCleanup(self.sleep_patcher.stop)

    def test_cells_are_masked_to_six_bits(self):
        cells = [0xFF, 0xC1, 0x80, 0x3F, 0x01]
        need = len(cells) + 2 * capture.PATTERN_CAPTURE_BLOCK
        self.conn._chunks = [bytes([0x03]) * need]
        rate, samples = capture.playback_pattern("COM9", cells, timeout=0.5)
        self.assertEqual(rate, capture.PATTERN_PLAYBACK_RATE)
        self.assertEqual(len(samples), need)
        self.assertEqual(self.conn.writes[1],
                         bytes([0x3F, 0x01, 0x00, 0x3F, 0x01]))

    def test_length_bounds_rejected_without_connecting(self):
        for bad in ([], [0] * (pattern.PATTERN_MAX + 1)):
            with self.assertRaises(ValueError):
                capture.playback_pattern("COM9", bad)
        self.assertFalse(hasattr(self.backend, "last_port"))

    def test_writes_are_ordered_and_input_is_flushed(self):
        cells = [0x01, 0x02]
        window = len(cells) + 2 * capture.PATTERN_CAPTURE_BLOCK
        self.conn._chunks = [bytes([0x03]) * window]
        capture.playback_pattern("COM9", cells, timeout=0.5)
        self.assertEqual(self.conn.writes[0], b"W2\n")
        self.assertEqual(self.conn.writes[1], b"\x01\x02")
        self.assertEqual(self.conn.writes[2], b"K")
        self.assertEqual(self.conn.writes[3], b"L")
        self.assertEqual(self.conn.reset_count, 1)
        self.assertTrue(self.conn.closed)

    def test_connection_uses_the_signal_baud(self):
        window = 1 + 2 * capture.PATTERN_CAPTURE_BLOCK
        self.conn._chunks = [bytes([0x00]) * window]
        capture.playback_pattern("COM7", [0x00], timeout=0.5)
        self.assertEqual(self.backend.last_port, "COM7")
        self.assertEqual(self.backend.last_baud, 921600)

    def test_returns_real_captured_bytes(self):
        need = 3 + 2 * capture.PATTERN_CAPTURE_BLOCK
        captured = (bytes([0x43, 0xC5, 0x00]) * (need // 3 + 1))[:need]
        self.conn._chunks = [captured, b"extra-never-read"]
        rate, samples = capture.playback_pattern(
            "COM9", [0x01, 0x02, 0x03], timeout=0.5)
        self.assertEqual(rate, 10000)
        self.assertEqual(samples, list(captured))
        self.assertEqual(self.conn._chunks, [b"extra-never-read"])

    def test_short_read_is_returned_not_fabricated(self):
        self.conn._chunks = [bytes([0xC1]) * 10]
        rate, samples = capture.playback_pattern(
            "COM9", [0x01] * 5, timeout=0.1)
        self.assertEqual(rate, 10000)
        self.assertEqual(len(samples), 10)
        self.assertEqual(self.conn.writes[-1], b"L")
        self.assertTrue(self.conn.closed)

    def test_read_error_still_stops_and_closes(self):
        self.conn._read_error = RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            capture.playback_pattern("COM9", [0x01], timeout=0.5)
        self.assertEqual(self.conn.writes[-1], b"L")
        self.assertTrue(self.conn.closed)

    def test_write_error_still_closes(self):
        self.conn._write_error = OSError("port gone")
        with self.assertRaises(OSError):
            capture.playback_pattern("COM9", [0x01], timeout=0.5)
        self.assertTrue(self.conn.closed)

    def test_failed_stop_raises_the_original_error_and_closes(self):
        window = 1 + 2 * capture.PATTERN_CAPTURE_BLOCK
        self.conn._chunks = [bytes([0x03]) * window]
        self.conn._stop_error = True
        with self.assertRaises(OSError):
            capture.playback_pattern("COM9", [0x01], timeout=0.5)
        self.assertTrue(self.conn.closed)

    def test_default_margin_covers_one_capture_block(self):
        """The default read window keeps one whole capture block of
        margin on each side, so the real waveform survives a worst-case
        K position inside the previous DMA block."""
        self.assertEqual(capture.PATTERN_CAPTURE_BLOCK, 1000)
        cells = [0x01, 0x02, 0x03]
        window = len(cells) + 2 * capture.PATTERN_CAPTURE_BLOCK
        self.conn._chunks = [bytes([0x03]) * window]
        rate, samples = capture.playback_pattern("COM9", cells, timeout=0.5)
        self.assertEqual(rate, 10000)
        self.assertEqual(len(samples), window)
        self.assertEqual(self.conn.writes[-1], b"L")
        self.assertTrue(self.conn.closed)


if __name__ == "__main__":
    unittest.main()
