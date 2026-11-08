# -*- coding: utf-8 -*-
"""Streaming measurement screen: per-channel freq/duty, first-channel details, edge counts."""
import time
from collections import deque

import core
from core.hal import BackendConnectionError
from core.i18n import _
from . import console

WINDOW = 3000


def run():
    """Three-in-one live measurement: per-channel frequency/duty + main
channel detail metrics + edge-triggered counters. Channel count, names,
and sample rate come from the current backend."""
    caps = core.current_backend().capabilities
    sample_rate = caps.sample_rate
    nch = caps.channel_count

    port = console.choose_port()
    if port is None:
        return
    try:
        ser = console.open_serial(port)
    except BackendConnectionError as e:
        print(_("Failed to open the serial port (close the serial monitor and retry): {error}"
                ).format(error=e))
        return

    raw = deque(maxlen=WINDOW)          # Raw bytes (one snapshot per byte)
    rise_cnt = [0] * nch                # Edge-triggered cumulative counts
    fall_cnt = [0] * nch
    prev = None
    last_show = 0
    print(_("\nConnected to {port}, measuring live ... (Ctrl+C to exit)\n").format(port=port))

    try:
        while True:
            n = ser.in_waiting
            if n:
                chunk = ser.read_available()
                for b in chunk:
                    # Edge trigger: compare with the previous byte channel by channel
                    if prev is not None:
                        for ch in range(nch):
                            p = (prev >> ch) & 1
                            c = (b >> ch) & 1
                            if p == 0 and c == 1: rise_cnt[ch] += 1
                            if p == 1 and c == 0: fall_cnt[ch] += 1
                    prev = b
                    raw.append(b)
            else:
                time.sleep(0.01)

            if time.time() - last_show >= 0.5 and len(raw) >= 100:
                last_show = time.time()
                console.clear_screen()
                print(_("===== HJS-Workbench - Three-in-one live measurement ====="))
                print(_("Sample rate: {rate} Hz   Window: {n} points\n").format(
                    rate=sample_rate, n=len(raw)))

                # 1) Multi-channel frequency
                print(_("-- Multi-channel frequency --"))
                results = []
                for ch in range(nch):
                    bits = [(b >> ch) & 1 for b in raw]
                    results.append(core.measure(bits, sample_rate))
                    if results[ch]:
                        print(_("  {ch}: {freq:8.1f} Hz   Duty {duty:5.1f}%").format(
                            ch=caps.channel_names[ch], freq=results[ch]['freq'],
                            duty=results[ch]['duty']))
                    else:
                        print(f"  {caps.channel_names[ch]}:       --  " + _("(no periodic signal)"))

                # 2) Main channel detailed measurement
                m = results[0]
                print(_("\n-- {ch} detailed measurement --").format(ch=caps.channel_names[0]))
                if m:
                    print(_("  Frequency      : {freq:.1f} Hz").format(freq=m['freq']))
                    print(_("  Period         : {period:.3f} ms  (min {pmin:.3f} / max {pmax:.3f})").format(
                        period=m['period']*1000, pmin=m['pmin']*1000, pmax=m['pmax']*1000))
                    print(_("  High pulse     : {high:.3f} ms").format(high=m['high']*1000))
                    print(_("  Low pulse      : {low:.3f} ms").format(low=m['low']*1000))
                    print(_("  Duty           : {duty:.1f} %   ({cycles} cycles averaged)").format(
                        duty=m['duty'], cycles=m['cycles']))
                else:
                    print(_("  Signal insufficient"))

                # 3) Edge-triggered counters
                print(_("\n-- Edge-triggered totals --"))
                print(_("  Channel   Rising   Falling"))
                for ch in range(nch):
                    print(f"   {caps.channel_names[ch]}   {rise_cnt[ch]:6d}   {fall_cnt[ch]:6d}")
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
        print(_("\nExited"))
