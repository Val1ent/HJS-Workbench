# -*- coding: utf-8 -*-
"""
Unified protocol analysis flow (matches proto_view.py):
  1) Live serial: capture from the device data port and decode live
     (works with real or self-test signals)
  2) Offline demo: use each decoder's built-in test waveform, no
     hardware required

The sample rate for the test waveforms comes from the current backend.
"""
import time
from collections import deque

import core
from core.hal import BackendConnectionError
from core.i18n import _
from core.registry import print_events
from . import console

WINDOW = 3000


def offline_demo(name):
    rate = core.current_backend().capabilities.sample_rate
    print(_("\n===== Offline demo: {name} (built-in test waveform, no hardware) ====="
            ).format(name=name))
    samples = core.DECKS[name]["make"](rate)
    events = core.DECKS[name]["decode"](samples, rate)
    print_events(events)
    print(_("\n({n} sample points, {m} events)").format(n=len(samples), m=len(events)))


def live_mode(name):
    rate = core.current_backend().capabilities.sample_rate
    port = console.choose_port()
    if port is None:
        return
    try:
        ser = console.open_serial(port)
    except BackendConnectionError as e:
        print(_("Failed to open the serial port (close the serial monitor and retry): {error}"
                ).format(error=e))
        return

    raw = deque(maxlen=WINDOW)
    shown = set()           # Deduplicate printed events
    last = 0
    print(_("\nConnected to {port}, decoding [{name}] live ... (Ctrl+C to exit)\n").format(
        port=port, name=name))
    try:
        while True:
            n = ser.in_waiting
            if n:
                raw.extend(ser.read_available())
            else:
                time.sleep(0.01)
            if time.time() - last >= 0.5 and len(raw) >= 50:
                last = time.time()
                samples = list(raw)
                events = core.DECKS[name]["decode"](samples, rate)
                for e in events:
                    key = (e["type"], e["text"], int(e["t"] * 10))
                    if key not in shown:
                        shown.add(key)
                        print(f"  {e['t']*1000:9.3f} ms  D{e['ch']}  "
                              f"{e['type']:<10} {e['text']}")
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print(_("\nExited."))


def run():
    if not core.DECKS:
        print(_("No registered decoders; check that the decoder modules in the core package are loaded."))
        return
    print(_("===== HJS-Workbench - Unified protocol analysis ====="))
    print(_("  [1] Live serial decode (needs hardware)"))
    print(_("  [2] Offline demo (built-in test waveform, no hardware)"))
    mode = input(_("Choose mode: ")).strip()
    name = console.choose_decoder()
    if name is None:
        return
    if mode == "1":
        live_mode(name)
    else:
        offline_demo(name)
