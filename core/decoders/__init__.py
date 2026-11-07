# -*- coding: utf-8 -*-
"""Protocol decoder collection.

Importing this subpackage imports all nine protocol modules in registration
order and thereby populates the DECKS registry.
"""
from . import nec, servo, i2c, spi, stepper, encoder, rc5, ultrasonic, fan  # noqa: F401

__all__ = ["nec", "servo", "i2c", "spi", "stepper", "encoder", "rc5",
           "ultrasonic", "fan"]
