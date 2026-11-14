# -*- coding: utf-8 -*-
"""Streaming analyzer screen: ASCII channel waveform, UART decode, measurement, CSV."""
import csv
import os
import time
from collections import deque

import core
from core.hal import BackendConnectionError
from core.i18n import _

from . import console

WINDOW        = 5000
TICKS_PER_BIT = 10
WAVE_LEN      = 100


def run():
    """Standalone analyzer screen: reads the serial port live and periodically
refreshes the waveform + serial parameters + UART decode + measurement +
CSV. The effective sample rate and channel names come from the current
backend session."""
    caps = core.current_backend().capabilities
    sample_rate = core.session.effective_sample_rate()
    dt = 1.0 / sample_rate

    port = console.choose_port()
    if port is None:
        return
    try:
        ser = console.open_serial(port)
    except BackendConnectionError as e:
        print(_("Failed to open the serial port (close the serial monitor and retry): {error}"
                ).format(error=e))
        return

    csv_path = os.path.join(os.getcwd(), "analyzer_log.csv")
    csv_file = open(csv_path, "w", newline="", encoding="utf-8-sig")
    writer = csv.writer(csv_file)
    # CSV header rows are data output and stay English in every language.
    writer.writerow(["Timestamp", "Baud bps", "Char period ms", "Packet length", "Decoded text"])

    raw = deque(maxlen=WINDOW)
    last_show = 0
    rows = 0
    print(_("\nConnected to {port}, analyzing standalone ... (Ctrl+C to exit)\n").format(port=port))

    try:
        while True:
            n = ser.in_waiting
            if n:
                raw.extend(ser.read_available())
            else:
                time.sleep(0.01)

            if time.time() - last_show >= 0.5 and len(raw) >= 100:
                last_show = time.time()
                bits = [(b >> 0) & 1 for b in raw]
                pkt = core.best_packet(bits)
                if pkt:
                    seg, decoded, g = pkt
                    wave = ''.join('\u2588' if x else '_' for x in seg[:WAVE_LEN])
                    gaps = [g[i + 1][0] - g[i][0] for i in range(len(g) - 1)]
                    char_period = (sum(gaps) / len(gaps)) * dt if gaps else 0.0
                    baud = sample_rate / TICKS_PER_BIT
                    nchar = len(g)
                else:
                    seg = None; decoded = ""
                    wave = ''.join('\u2588' if x else '_' for x in bits[-WAVE_LEN:])
                    char_period = 0.0; baud = 0.0; nchar = 0

                console.clear_screen()
                print(_("===== Standalone analyzer terminal (no PulseView needed) ====="))
                print(_("Sample rate: {rate} Hz   Window: {n} points\n").format(
                    rate=sample_rate, n=len(raw)))

                print(_("-- Terminal waveform {ch} (first 100 points of the packet = 10 ms) --"
                        ).format(ch=caps.channel_names[0]))
                print(_("  high=\u2588  low=_"))
                print("  " + wave + "\n")

                print(_("-- Serial parameter measurement --"))
                if nchar:
                    print(_("  Baud {baud:.0f} bps | Char period {period:.3f} ms | "
                            "Packet length {nchar} chars | Frame format 8N1").format(
                                baud=baud, period=char_period*1000, nchar=nchar))
                else:
                    print(_("  No complete packet detected in this window"))

                print(_("\n-- Built-in UART decode --"))
                if decoded:
                    print(_("  Received: {text}").format(text=repr(decoded)))
                else:
                    print(_("  Received: (no complete frame decoded in this window)"))

                print(_("\n-- {ch} live measurement --").format(ch=caps.channel_names[0]))
                m = core.measure(bits, sample_rate)
                if m:
                    print(_("  Frequency {freq:.1f} Hz | Period {period:.3f} ms | "
                            "Duty {duty:.1f}%").format(
                                freq=m['freq'], period=m['period']*1000, duty=m['duty']))
                else:
                    print(_("  Signal insufficient"))

                # Write CSV
                if nchar:
                    writer.writerow([f"{time.time():.1f}", f"{baud:.0f}",
                        f"{char_period*1000:.3f}", f"{nchar}", decoded])
                    csv_file.flush()
                    rows += 1
                print(_("\n-- Data log --  {rows} rows written -> {path}").format(
                    rows=rows, path=csv_path))
    except KeyboardInterrupt:
        pass
    finally:
        csv_file.close()
        ser.close()
        print(_("\nExited, CSV saved: {path}").format(path=csv_path))
