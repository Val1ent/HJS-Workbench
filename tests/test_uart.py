# -*- coding: utf-8 -*-
"""Tests for software UART decoding."""
import unittest

from core.uart import TICKS_PER_BIT, best_packet, scan_frames, uart_decode


def encode_frame(char, ticks=TICKS_PER_BIT):
    """Build one 8N1 frame (idle high, LSB first) as a bit list."""
    bits = [1] * ticks  # idle before start
    bits += [0] * ticks  # start bit
    value = ord(char)
    for k in range(8):  # data bits, LSB first
        level = (value >> k) & 1
        bits += [level] * ticks
    bits += [1] * ticks  # stop bit
    return bits


class UartDecodeTest(unittest.TestCase):
    def test_single_char(self):
        bits = encode_frame("A")
        self.assertEqual(uart_decode(bits), "A")

    def test_multiple_chars(self):
        bits = []
        for ch in "Hi":
            bits += encode_frame(ch)
        self.assertEqual(uart_decode(bits), "Hi")

    def test_idle_only_decodes_nothing(self):
        self.assertEqual(uart_decode([1] * 100), "")

    def test_scan_frames_reports_char(self):
        bits = encode_frame("Z")
        frames = scan_frames(bits)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0][1], "Z")

    def test_best_packet_joins_continuous_frames(self):
        bits = []
        for ch in "AB":
            bits += encode_frame(ch)
        result = best_packet(bits)
        self.assertIsNotNone(result)
        self.assertEqual(result[1], "AB")

    def test_best_packet_none_for_single_frame(self):
        self.assertIsNone(best_packet(encode_frame("A")))


if __name__ == "__main__":
    unittest.main()
