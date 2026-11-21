# -*- coding: utf-8 -*-
"""Tests for the pattern editor pure logic (no Qt widgets, no hardware)."""
import unittest

from gui import pattern_panel


class MaskTest(unittest.TestCase):
    def test_mask_cell_keeps_only_six_gpo_bits(self):
        self.assertEqual(pattern_panel.mask_cell(0x3F), 0x3F)
        self.assertEqual(pattern_panel.mask_cell(0xFF), 0x3F)
        self.assertEqual(pattern_panel.mask_cell(0xC0), 0x00)
        self.assertEqual(pattern_panel.mask_cell(0x41), 0x01)

    def test_masked_cells_applies_to_the_whole_sequence(self):
        self.assertEqual(pattern_panel.masked_cells([0xFF, 0x01, 0x80]),
                         [0x3F, 0x01, 0x00])


class BitEditTest(unittest.TestCase):
    def test_get_bit_reads_one_gpo_bit(self):
        cells = [0b101010]  # bits 1, 3, 5 high
        self.assertFalse(pattern_panel.get_bit(cells, 0, 0))
        self.assertTrue(pattern_panel.get_bit(cells, 0, 1))
        self.assertTrue(pattern_panel.get_bit(cells, 0, 5))

    def test_set_bit_preserves_the_other_bits(self):
        cells = [0b101010]
        raised = pattern_panel.set_bit(cells, 0, 0, True)
        self.assertEqual(raised, [0b101011])
        lowered = pattern_panel.set_bit(cells, 0, 1, False)
        self.assertEqual(lowered, [0b101000])
        self.assertEqual(cells, [0b101010])  # original untouched

    def test_toggle_bit_flips_only_the_requested_bit(self):
        cells = [0x00, 0x3F]
        self.assertEqual(pattern_panel.toggle_bit(cells, 0, 2),
                         [0x04, 0x3F])
        self.assertEqual(pattern_panel.toggle_bit(cells, 1, 5),
                         [0x00, 0x1F])


class ResizeTest(unittest.TestCase):
    def test_growing_keeps_data_and_pads_with_zero(self):
        self.assertEqual(pattern_panel.resize_cells([1, 2, 3], 5),
                         [1, 2, 3, 0, 0])

    def test_shrinking_drops_the_tail(self):
        self.assertEqual(pattern_panel.resize_cells([1, 2, 3], 2), [1, 2])

    def test_out_of_range_lengths_rejected(self):
        with self.assertRaises(ValueError):
            pattern_panel.resize_cells([0], 0)
        with self.assertRaises(ValueError):
            pattern_panel.resize_cells([0], pattern_panel.MAX_CELLS + 1)


class TemplateTest(unittest.TestCase):
    def test_template_masks_every_byte(self):
        cells = pattern_panel.template_cells([0xFF, 0x3F, 0xC0])
        self.assertEqual(cells, [0x3F, 0x3F, 0x00])

    def test_over_long_template_rejected(self):
        too_long = [0x01] * (pattern_panel.MAX_CELLS + 1)
        with self.assertRaises(ValueError):
            pattern_panel.template_cells(too_long)

    def test_empty_template_rejected(self):
        with self.assertRaises(ValueError):
            pattern_panel.template_cells([])


class FactsTest(unittest.TestCase):
    def test_six_gpo_rows_and_fixed_cell_duration(self):
        self.assertEqual(len(pattern_panel.GPO_ROWS), 6)
        self.assertEqual(pattern_panel.duration_us([0] * 100), 10000)
        self.assertEqual(pattern_panel.duration_us([0] * 8000), 800000)


if __name__ == "__main__":
    unittest.main()
