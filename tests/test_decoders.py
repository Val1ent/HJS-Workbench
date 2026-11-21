# -*- coding: utf-8 -*-
"""Content-correctness tests for every registered decoder.

Each decoder builds its own known test waveform and decodes it; the
assertions check specific decoded values rather than merely that some
event was produced.
"""
import unittest

import core.decoders  # noqa: F401  registers every decoder
from core.decoders import manchester
from core.model import channel_bits
from core.registry import DECKS

RATE = 10000

EXPECT = {
    "manchester": [("MAN_BYTE", "0x55")],
    "dht11": [("DHT11", "humidity=45.0%"), ("DHT11", "temperature=25.0C")],
    "nec": [("NEC", "addr=0x00"), ("NEC", "cmd=0x45")],
    "onewire": [("TEMP", "temp=25.0C"), ("TEMP", "CRC OK")],
    "rc5": [("RC5", "addr=5"), ("RC5", "cmd=33")],
    "sirc": [("SIRC", "dev=1"), ("SIRC", "cmd=22")],
    "modbus": [("MODBUS", "addr=1"), ("MODBUS", "CRC OK")],
    "nmea": [("NMEA", "checksum OK")],
    "fan": [("FAN", "3000RPM")],
    "servo": [("SERVO", "pulse=1000us angle=0.0"),
              ("SERVO", "pulse=1500us angle=90.0"),
              ("SERVO", "pulse=2000us angle=180.0")],
    "ds1302": [("TIME", "13:30:45")],
    "i2c": [("ADDR", "0x48 W ACK"), ("DATA", "0x55 ACK")],
    "encoder": [("ENCODER_SUM", "total 120 edges")],
    "hd44780": [("CMD", "0x28"), ("CHAR", "0x48 'H'")],
    "spi": [("SPI", "MOSI=0x3C"), ("SPI", "MISO=0x11")],
    "stepper": [("STEP_SUM", "total 40 steps")],
    "swd": [("SWD_WRITE", "parity OK"), ("SWD_READ", "parity OK")],
    "ultrasonic": [("DISTANCE", "distance=17.0cm")],
    "wiegand": [("WIEGAND_FRAME", "parity OK")],
}


class DecoderCorrectnessTest(unittest.TestCase):
    def test_all_decoders_are_covered(self):
        self.assertEqual(set(EXPECT), set(DECKS))

    def test_each_decoder_produces_expected_values(self):
        for name, checks in EXPECT.items():
            with self.subTest(decoder=name):
                deck = DECKS[name]
                samples = deck["make"](RATE)
                events = deck["decode"](samples, RATE)
                pairs = [(e["type"], e["text"]) for e in events]
                for etype, sub in checks:
                    self.assertTrue(
                        any(t == etype and sub in txt for t, txt in pairs),
                        "missing %s containing %r; got %s" %
                        (etype, sub, pairs))


class ManchesterHeadGlitchTest(unittest.TestCase):
    """A spurious head transition must not break the start alignment.

    The real pattern playback path can prepend one extra level blip
    before the actual Manchester signal; the old fixed first-transition
    anchor then decoded less than one byte. The multi-start scan must
    still decode the full preamble and the "Hi" text.
    """

    def test_glitch_prefix_still_decodes_all_bytes(self):
        deck = DECKS["manchester"]
        clean = deck["make"](RATE)
        prefix = [1] * 20 + [0] * 4 + [1] * 8
        samples = prefix + list(clean)
        events = deck["decode"](samples, RATE)
        texts = [e["text"] for e in events if e["type"] == "MAN_BYTE"]
        joined = " ".join(texts)
        for expected in ("0x55", "0x48", "0x69"):
            self.assertIn(expected, joined, texts)

        # The same input must defeat the old fixed trans[0] anchor, which
        # is what proves the scan really fixed the alignment.
        bits = channel_bits(samples, 0)
        trans = [i for i in range(1, len(bits))
                 if bits[i - 1] != bits[i]]
        gaps = [trans[k + 1] - trans[k] for k in range(len(trans) - 1)]
        min_gap = min(gaps)
        candidates = sorted({min_gap, 2 * min_gap})
        if min_gap % 2 == 0:
            candidates.insert(0, min_gap // 2)
        old_data = []
        for half in candidates:
            if half < 2:
                continue
            data = manchester._walk(bits, trans, half)
            if len(data) > len(old_data):
                old_data = data
        self.assertLess(len(old_data), 8, old_data)


if __name__ == "__main__":
    unittest.main()
