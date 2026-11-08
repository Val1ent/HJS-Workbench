# -*- coding: utf-8 -*-
"""
Signal generator console: send commands to the device over USB CDC
  Enter a frequency number (e.g. 1000) -> the device outputs a square
  wave at that frequency (range 1-5000 Hz)
  Enter u                          -> switch back to software UART
                                       (sends Hello CH32)
  Enter q                          -> quit

The port is opened at the current backend's declared signal baud rate.
"""
import core
from core.hal import BackendConnectionError
from core.i18n import _
from . import console


def run():
    port = console.choose_port()
    if port is None:
        return
    caps = core.current_backend().capabilities
    try:
        ser = console.open_serial(port, baud=caps.signal_baud)
    except BackendConnectionError as e:
        print(_("Failed to open the serial port (close the serial monitor and retry): {error}"
                ).format(error=e))
        return
    print(_("Connected to {port}").format(port=port))
    print(_("Enter a frequency (1-5000) for a square wave; u = switch to UART; q = quit\n"))

    while True:
        try:
            cmd = input("signal> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not cmd:
            continue
        if cmd.lower() == 'q':
            break
        if cmd.lower() == 'u':
            ser.write(b"U\n")
            print(_("-> switched to UART mode"))
        elif cmd.isdigit():
            ser.write(("S" + cmd + "\n").encode())
            print(_("-> square wave {hz} Hz").format(hz=cmd))
        else:
            print(_("Enter a numeric frequency, or u / q"))

    ser.close()
    print(_("Exited"))
