# -*- coding: utf-8 -*-
"""
HJS-Workbench - shared multi-protocol decoding framework
=========================================================
Pure standard library (no third-party dependencies); never touches the
firmware and never flashes the device.

[Sample data format (must follow)]
  samples : list[int], each int is one sampling-instant snapshot of every
            channel (1 byte per sample; unit size 1)
            bit0 = D0(PD0), bit1 = D1(PD1), ..., bit7 = D7(PD7)
            channel level = (sample >> ch) & 1
  rate    : int, sample rate in Hz (from the current backend's capabilities)

[Unified event format Event]
  dict: {"t": float(seconds), "ch": int(channel), "type": str(type),
         "text": str(human-readable text)}
  Decoders must return list[Event] sorted by ascending t.

[Decoder conventions]
  Every decoder provides two functions:
    decode_XXX(samples, rate, **channel args) -> list[Event]
    make_XXX_test(rate) -> list[int]  # generate 8-channel test samples
                                      # with known content
  and registers itself in DECKS (see the example at the end of this file).
"""

from .hal import current_backend


def default_rate():
    """Default sample rate in Hz, from the current device backend."""
    return current_backend().capabilities.sample_rate


def default_channel_count():
    """Default channel count, from the current device backend."""
    return current_backend().capabilities.channel_count


def default_channel_names():
    """Default channel names, from the current device backend."""
    return list(current_backend().capabilities.channel_names)


def channel_bits(samples, ch):
    """Expand multi-channel snapshot samples into the 0/1 sequence of one channel."""
    mask = 1 << ch
    return [1 if (b & mask) else 0 for b in samples]


def set_channel(samples, idx, ch, level):
    """Set one channel's level at samples[idx] (used to build test waveforms)."""
    if level:
        samples[idx] |= (1 << ch)
    else:
        samples[idx] &= ~(1 << ch) & 0xFF
