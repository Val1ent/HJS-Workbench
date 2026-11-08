# -*- coding: utf-8 -*-
"""Protocol decoder collection.

Importing this subpackage imports all nineteen protocol modules in
registration order and thereby populates the DECKS registry.
"""
from . import (  # noqa: F401
    nec, servo, i2c, spi, stepper, encoder, rc5, ultrasonic, fan,
    dht11, onewire, swd, modbus, wiegand, hd44780, sirc, ds1302,
    manchester, nmea,
)

__all__ = [
    "nec", "servo", "i2c", "spi", "stepper", "encoder", "rc5",
    "ultrasonic", "fan", "dht11", "onewire", "swd", "modbus",
    "wiegand", "hd44780", "sirc", "ds1302", "manchester", "nmea",
]
