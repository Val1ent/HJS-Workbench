# -*- coding: utf-8 -*-
"""Tests for the sample data model helpers."""
import unittest

from core.model import channel_bits, set_channel


class ChannelBitsTest(unittest.TestCase):
    def test_channel_bits_reads_mask(self):
        samples = [0x00, 0x01, 0x02, 0x03]
        self.assertEqual(channel_bits(samples, 0), [0, 1, 0, 1])
        self.assertEqual(channel_bits(samples, 1), [0, 0, 1, 1])

    def test_set_channel_high_and_low(self):
        samples = [0x00]
        set_channel(samples, 0, 3, 1)
        self.assertEqual(samples[0], 0x08)
        set_channel(samples, 0, 3, 0)
        self.assertEqual(samples[0], 0x00)

    def test_set_channel_round_trips_for_every_channel(self):
        for ch in range(8):
            samples = [0x00]
            set_channel(samples, 0, ch, 1)
            self.assertEqual(channel_bits(samples, ch), [1])
            set_channel(samples, 0, ch, 0)
            self.assertEqual(channel_bits(samples, ch), [0])

    def test_set_channel_keeps_other_channels(self):
        samples = [0x00]
        set_channel(samples, 0, 2, 1)
        set_channel(samples, 0, 5, 1)
        self.assertEqual(samples[0], 0x24)
        set_channel(samples, 0, 2, 0)
        self.assertEqual(samples[0], 0x20)

    def test_set_channel_stays_within_one_byte(self):
        samples = [0xFF]
        set_channel(samples, 0, 0, 0)
        self.assertEqual(samples[0], 0xFE)
        self.assertLessEqual(samples[0], 0xFF)


if __name__ == "__main__":
    unittest.main()
