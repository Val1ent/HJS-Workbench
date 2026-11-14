# -*- coding: utf-8 -*-
"""Protocol decoder collection.

Importing this subpackage imports all nineteen protocol modules in
registration order and thereby populates the DECKS registry.
"""
from . import (
    dht11,
    ds1302,
    encoder,
    fan,
    hd44780,
    i2c,
    manchester,
    modbus,
    nec,
    nmea,
    onewire,
    rc5,
    servo,
    sirc,
    spi,
    stepper,
    swd,
    ultrasonic,
    wiegand,
)

__all__ = [
    "dht11",
    "ds1302",
    "encoder",
    "fan",
    "hd44780",
    "i2c",
    "manchester",
    "modbus",
    "nec",
    "nmea",
    "onewire",
    "rc5",
    "servo",
    "sirc",
    "spi",
    "stepper",
    "swd",
    "ultrasonic",
    "wiegand",
]
