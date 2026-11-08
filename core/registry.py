# -*- coding: utf-8 -*-
"""Decoder registry and self-test helpers."""
from .i18n import _

# ----------------------------------------------------------------------
# Registry and self-test
# ----------------------------------------------------------------------
DECKS = {}   # name -> {"decode": fn, "make": fn, "desc": str}


def register(name, decode_fn, make_fn, desc=""):
    DECKS[name] = {"decode": decode_fn, "make": make_fn, "desc": desc}


def print_events(events, ch_name=None):
    """Print events to the terminal."""
    if not events:
        print("  " + _("(no events decoded)"))
    for e in events:
        c = ch_name if ch_name is not None else e["ch"]
        print(f"  {e['t']*1000:9.3f} ms  D{c}  {e['type']:<10} {e['text']}")


def selftest(name):
    """Run a decoder's built-in test waveform; return (events, samples).

    The test waveforms use the current device backend's sample rate.
    """
    from .hal import current_backend
    rate = current_backend().capabilities.sample_rate
    deck = DECKS[name]
    samples = deck["make"](rate)
    events = deck["decode"](samples, rate)
    return events, samples
