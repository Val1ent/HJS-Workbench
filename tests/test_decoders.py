# -*- coding: utf-8 -*-
"""Content-correctness tests for every registered decoder.

Each decoder builds its own known test waveform and decodes it; the
assertions check specific decoded values rather than merely that some
event was produced.
"""
import unittest

import core.decoders  # noqa: F401  registers every decoder
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


if __name__ == "__main__":
    unittest.main()
