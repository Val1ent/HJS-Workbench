# -*- coding: utf-8 -*-
"""Unified command-line front-end package.

All capture, decoding, measurement, and file logic lives in the `core`
package; this package only adds the menu-driven terminal UI on top of it.
"""
from .version import __version__

__all__ = ["__version__"]
