# -*- coding: utf-8 -*-
"""Tests for single-channel measurement."""
import unittest

from core.measurement import measure

RATE = 10000


def square_wave(cycles, period, high_len):
    """Build a repeating square wave with a known period and high length."""
    bits = [0] * (cycles * period)
    for cyc in range(cycles):
        base = cyc * period
        for i in range(base, base + high_len):
            bits[i] = 1
    return bits


class MeasureTest(unittest.TestCase):
    def test_50_percent_duty_wave(self):
        bits = square_wave(cycles=5, period=100, high_len=50)
        m = measure(bits, RATE)
        self.assertIsNotNone(m)
        self.assertAlmostEqual(m["freq"], 100.0)
        self.assertAlmostEqual(m["duty"], 50.0)
        self.assertAlmostEqual(m["period"], 100 / RATE)
        self.assertEqual(m["cycles"], 3)

    def test_25_percent_duty_wave(self):
        bits = square_wave(cycles=5, period=100, high_len=25)
        m = measure(bits, RATE)
        self.assertIsNotNone(m)
        self.assertAlmostEqual(m["duty"], 25.0)
        self.assertAlmostEqual(m["freq"], 100.0)

    def test_insufficient_signal_returns_none(self):
        self.assertIsNone(measure([0, 0, 1, 1], RATE))
        self.assertIsNone(measure([1, 1, 1], RATE))


if __name__ == "__main__":
    unittest.main()
