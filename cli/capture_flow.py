# -*- coding: utf-8 -*-
"""One-shot serial capture and save flow (capture3.py behavior)."""
import os
import time
from collections import Counter

import core
from core.hal import BackendConnectionError
from core.i18n import _
from . import console

POINTS = 3000


def run():
    """Capture flow: pick a port -> capture POINTS points once -> save a
.sr file; q returns to the main menu."""
    while True:
        port = console.choose_port()
        if port is None:
            return
        print(_("Capture starts in 2 seconds; confirm A15 is connected to D0 ..."))
        time.sleep(2)
        print(_("Capturing {n} points from {port} ...").format(n=POINTS, port=port))
        t0 = time.time()
        try:
            _rate, data = core.acquire_serial(port, POINTS)
        except BackendConnectionError as e:
            print(_("Failed to open the serial port (close the serial monitor and retry): {error}"
                    ).format(error=e))
            continue
        except Exception as e:
            print(_("Not enough data."), e)
            print(_("- If in_waiting stays 0: the device is not sending on this port; check that you picked the USB-FS port, that A15->D0 is wired, and that the serial monitor is closed;"))
            print(_("- Try unplugging and replugging the bottom USB cable or pressing RESET, then pick the port again."))
        else:
            print(_("Received {n} bytes in {t:.1f} s").format(n=len(data), t=time.time()-t0))
            top = Counter(data).most_common(5)
            print(_("Most common bytes:"), [(hex(k), v) for k, v in top])
            fn = os.path.join(os.getcwd(), f"capture_{int(time.time())}.sr")
            core.write_sr(fn, data)
            print(_("Created:"), fn)
        if input(_("\nEnter to capture another screen, q to quit: ")).strip().lower() == "q":
            return
