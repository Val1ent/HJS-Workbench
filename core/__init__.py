# -*- coding: utf-8 -*-
"""Pocket Debug Kit core package.

Importing this package registers all nine protocol decoders and re-exports
the public API used by CLI and GUI front-ends:

    DECKS, channel_bits, read_sr, read_bin, write_sr, acquire_file,
    scan_frames, best_packet, uart_decode, measure,
    list_serial_ports, acquire_serial
"""
from . import decoders  # noqa: F401
from .capture import acquire_serial, list_serial_ports
from .files import acquire_file, read_bin, read_sr, write_sr
from .measurement import measure
from .model import channel_bits
from .registry import DECKS
from .uart import best_packet, scan_frames, uart_decode

__all__ = [
    "DECKS",
    "channel_bits",
    "read_sr",
    "read_bin",
    "write_sr",
    "acquire_file",
    "scan_frames",
    "best_packet",
    "uart_decode",
    "measure",
    "list_serial_ports",
    "acquire_serial",
]
