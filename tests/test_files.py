# -*- coding: utf-8 -*-
"""Tests for .sr/.bin capture file support."""
import os
import tempfile
import unittest

from core.files import (
    acquire_file,
    format_rate,
    parse_rate_str,
    read_bin,
    read_sr,
    write_sr,
)


class RateFormatTest(unittest.TestCase):
    def test_format_rate_units(self):
        self.assertEqual(format_rate(10000), "10 kHz")
        self.assertEqual(format_rate(1000000), "1 MHz")
        self.assertEqual(format_rate(500000), "500 kHz")

    def test_parse_rate_str(self):
        self.assertEqual(parse_rate_str("10 kHz"), 10000)
        self.assertEqual(parse_rate_str("1 MHz"), 1000000)
        self.assertEqual(parse_rate_str("1000"), 1000)

    def test_format_parse_round_trip(self):
        for rate in (10000, 100000, 500000, 1000000):
            self.assertEqual(parse_rate_str(format_rate(rate)), rate)


class SrFileTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "capture.sr")

    def tearDown(self):
        self.tmp.cleanup()

    def test_write_read_round_trip(self):
        data = [0x00, 0x01, 0x02, 0xFF, 0x10]
        write_sr(self.path, data, rate=10000)
        rate, samples = read_sr(self.path)
        self.assertEqual(rate, 10000)
        self.assertEqual(samples, data)

    def test_bin_round_trip(self):
        bin_path = os.path.join(self.tmp.name, "capture.bin")
        data = [0x05, 0x06, 0x07]
        with open(bin_path, "wb") as f:
            f.write(bytes(data))
        rate, samples = read_bin(bin_path, 10000)
        self.assertEqual(rate, 10000)
        self.assertEqual(samples, data)

    def test_acquire_rejects_unknown_extension(self):
        bad = os.path.join(self.tmp.name, "capture.txt")
        with open(bad, "w") as f:
            f.write("x")
        with self.assertRaises(ValueError):
            acquire_file(bad)


if __name__ == "__main__":
    unittest.main()
