# -*- coding: utf-8 -*-
"""Tests for the HAL hard rules: real backends only, invalid config rejected."""
import unittest

from core.hal import (
    BACKENDS,
    DEFAULT_BACKEND_ID,
    current_backend,
    list_backends,
)
from core.hal.ch32 import _check_mode


class BackendRegistryTest(unittest.TestCase):
    def test_default_backend_is_ch32(self):
        self.assertEqual(current_backend().id, "ch32")
        self.assertEqual(DEFAULT_BACKEND_ID, "ch32")

    def test_no_simulated_backend_exists(self):
        ids = list(BACKENDS)
        self.assertTrue(ids)
        for backend_id in ids:
            lowered = backend_id.lower()
            for forbidden in ("mock", "sim", "virtual", "dummy", "fake"):
                self.assertNotIn(forbidden, lowered)
        self.assertEqual([b.id for b in list_backends()], ["ch32"])

    def test_capabilities_are_real_measurements(self):
        caps = current_backend().capabilities
        self.assertEqual(caps.channel_count, 8)
        self.assertIn(1000000, caps.supported_rates)
        self.assertEqual(caps.burst_capacity, 712704)


class ValidateConfigTest(unittest.TestCase):
    def setUp(self):
        self.backend = current_backend()

    def test_valid_config_accepted(self):
        self.backend.validate_config(
            sample_rate=10000, unit_size=1, channels=8, mode="realtime")
        self.backend.validate_config(mode="burst")

    def test_invalid_rate_rejected(self):
        with self.assertRaises(ValueError):
            self.backend.validate_config(sample_rate=12345)

    def test_invalid_unit_size_rejected(self):
        with self.assertRaises(ValueError):
            self.backend.validate_config(unit_size=2)

    def test_invalid_channel_count_rejected(self):
        with self.assertRaises(ValueError):
            self.backend.validate_config(channels=7)

    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):
            self.backend.validate_config(mode="teleport")

    def test_burst_rejected_when_capacity_zero(self):
        class _Caps:
            burst_capacity = 0
            display_name = "test board"
            supported_modes = ["realtime", "burst"]

        with self.assertRaises(ValueError):
            _check_mode(_Caps(), "burst")


if __name__ == "__main__":
    unittest.main()
