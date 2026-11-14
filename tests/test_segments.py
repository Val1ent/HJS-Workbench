# -*- coding: utf-8 -*-
"""Tests for edge detection and pulse segmentation."""
import unittest

from core.segments import build_wave, edges_of, pulse_widths

RATE = 10000


class EdgesOfTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(edges_of([]), [])

    def test_initial_level_and_transitions(self):
        bits = [1, 1, 0, 0, 1]
        self.assertEqual(edges_of(bits),
                         [(0, 1), (2, 0), (4, 1)])

    def test_constant_has_only_initial(self):
        self.assertEqual(edges_of([0, 0, 0]), [(0, 0)])


class PulseWidthsTest(unittest.TestCase):
    def test_segment_widths(self):
        bits = [1, 1, 0, 0, 0]
        segs = pulse_widths(bits, RATE)
        self.assertEqual((segs[0][0], segs[0][1]), (0, 1))
        self.assertAlmostEqual(segs[0][2], 2 / RATE)
        self.assertEqual((segs[1][0], segs[1][1]), (2, 0))
        self.assertAlmostEqual(segs[1][2], 3 / RATE)

    def test_widths_cover_all_samples(self):
        bits = [1, 0, 1, 0, 1, 0]
        segs = pulse_widths(bits, RATE)
        total = sum(round(w * RATE) for _, _, w in segs)
        self.assertEqual(total, len(bits))


class BuildWaveTest(unittest.TestCase):
    def test_idle_filled(self):
        samples = build_wave(0, [], RATE, 100, idle=1)
        self.assertEqual(len(samples), 100)
        self.assertTrue(all((b & 0x01) == 1 for b in samples))

    def test_pulse_overrides_idle(self):
        pulses = [(0.002, 0, 0.003)]
        samples = build_wave(0, pulses, RATE, 100, idle=1)
        bits = [b & 0x01 for b in samples]
        # pulse spans samples 20..49 (2 ms to 5 ms)
        self.assertEqual(bits[20:50], [0] * 30)
        self.assertEqual(bits[19], 1)
        self.assertEqual(bits[50], 1)


if __name__ == "__main__":
    unittest.main()
