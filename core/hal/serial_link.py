# -*- coding: utf-8 -*-
"""Thin generic wrapper around a pyserial port.

This is the ONLY module in the whole repository allowed to import
pyserial. It exposes plain port operations (``in_waiting``, ``read``,
``write``, ``reset_input_buffer``, ``close``, control lines, port
enumeration) with no board-specific text, so any future serial backend
can reuse it.

Every low-level port error is translated into the readable
:class:`core.hal.base.BackendConnectionError` used by the upper layers.
"""
import serial
from serial.tools import list_ports

from ..i18n import _
from .base import BackendConnectionError


def list_serial_ports():
    """Enumerate the real system serial ports.

    Return a list of ``(device, description)`` pairs.
    """
    return [(p.device, p.description) for p in list_ports.comports()]


class SerialLink:
    """A minimal, reusable wrapper around one pyserial port."""

    def __init__(self, port, baud, timeout=0):
        try:
            self._ser = serial.Serial(port, baud, timeout=timeout)
        except (serial.SerialException, OSError, ValueError) as exc:
            raise BackendConnectionError(
                _("Cannot open serial port {port}: {error}"
                  ).format(port=port, error=exc)) from exc

    @property
    def in_waiting(self):
        """Number of bytes currently waiting in the input buffer."""
        return self._ser.in_waiting

    def read(self, count):
        """Read up to ``count`` bytes from the port."""
        return self._ser.read(count)

    def read_blocking(self, count, timeout):
        """Read up to ``count`` bytes, blocking for at most ``timeout``
        seconds. The timeout is written to the port only when its value
        actually changes; repeated reads with the same value never
        reconfigure the driver. Reconfiguring the port timeout on every
        read drops bytes from a high-speed burst stream."""
        try:
            if self._ser.timeout != timeout:
                self._ser.timeout = timeout
            return self._ser.read(count)
        except (serial.SerialException, OSError) as exc:
            raise BackendConnectionError(
                _("Cannot read from the serial port: {error}"
                  ).format(error=exc)) from exc

    def write(self, data):
        """Write ``data`` to the port and return the byte count."""
        return self._ser.write(data)

    def reset_input_buffer(self):
        """Discard everything currently in the input buffer."""
        self._ser.reset_input_buffer()

    def set_dtr(self, level):
        """Assert or deassert the DTR control line."""
        try:
            self._ser.dtr = bool(level)
        except (serial.SerialException, OSError) as exc:
            raise BackendConnectionError(
                _("Cannot set the DTR control line: {error}"
                  ).format(error=exc)) from exc

    def set_rts(self, level):
        """Assert or deassert the RTS control line."""
        try:
            self._ser.rts = bool(level)
        except (serial.SerialException, OSError) as exc:
            raise BackendConnectionError(
                _("Cannot set the RTS control line: {error}"
                  ).format(error=exc)) from exc

    def close(self):
        """Close the port."""
        self._ser.close()
