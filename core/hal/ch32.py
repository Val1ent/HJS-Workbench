# -*- coding: utf-8 -*-
"""CH32 backend: the first real device backend.

Moves the existing, verified serial behavior behind the uniform backend
interface. Every hardware value below (baud rates, channel count, sample
rate, unit size, control lines, troubleshooting text) is a declared
capability of the real CH32 board and nothing else in the repository
hard-codes it.

Connection flow is identical to the previous ``open_serial``:
open at the data baud, assert DTR/RTS, wait 0.5 s, flush the input
buffer. The one-shot acquire polls non-blocking until enough bytes
arrive or the timeout, closes the port on exit, and raises the same
troubleshooting text on timeout.
"""
import time

from .base import (
    BackendConnectionError,
    DeviceBackend,
    DeviceCapabilities,
    DeviceConnection,
)
from .serial_link import SerialLink, list_serial_ports
from ..i18n import _

CH32_CAPABILITIES = DeviceCapabilities(
    backend_id="ch32",
    display_name="CH32 development board (USB-FS data port)",
    channel_count=8,
    channel_names=["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7"],
    sample_rate=10000,
    supported_rates=[10000],
    unit_size=1,
    supported_unit_sizes=[1],
    data_baud=115200,
    signal_baud=921600,
    assert_control_lines=True,
)

_TIMEOUT_MESSAGE = (
    "Capture timed out: got {got} points, need {need} points.\n"
    "Check: is the CH32 data port selected (bottom USB-FS port, "
    "not the debug port), is A15 looped back to D0, is the port "
    "free of other programs; then retry."
)


class CH32Connection(DeviceConnection):
    """A live connection to a CH32 board (data port or signal port)."""

    def __init__(self, link):
        self._link = link

    @property
    def in_waiting(self):
        return self._link.in_waiting

    def read_available(self):
        """Non-blocking read of the currently waiting bytes."""
        pending = self._link.in_waiting
        if not pending:
            return b""
        return self._link.read(pending)

    def write(self, data):
        self._link.write(data)

    def reset_input(self):
        self._link.reset_input_buffer()

    def acquire(self, n_points, timeout):
        """One-shot capture of exactly ``n_points`` bytes.

        Poll non-blocking until the bytes arrive or the timeout expires,
        close the port on exit, and raise the troubleshooting text when
        the timeout expired first.
        """
        data = bytearray()
        deadline = time.monotonic() + timeout
        try:
            while len(data) < n_points and time.monotonic() < deadline:
                chunk = self.read_available()
                if chunk:
                    data.extend(chunk[:n_points - len(data)])
                else:
                    time.sleep(0.01)
        finally:
            self.close()
        if len(data) < n_points:
            raise RuntimeError(
                _(_TIMEOUT_MESSAGE).format(got=len(data), need=n_points)
            )
        return list(data)

    def close(self):
        self._link.close()


class CH32Backend(DeviceBackend):
    """The real CH32 development board."""

    @property
    def id(self):
        return CH32_CAPABILITIES.backend_id

    @property
    def display_name(self):
        return CH32_CAPABILITIES.display_name

    @property
    def capabilities(self):
        return CH32_CAPABILITIES

    def list_ports(self):
        return list_serial_ports()

    def connect(self, port, baud=None):
        caps = self.capabilities
        if baud is None:
            baud = caps.data_baud
        link = SerialLink(port, baud)
        try:
            if caps.assert_control_lines:
                link.set_dtr(True)
                link.set_rts(True)
            time.sleep(0.5)
            link.reset_input_buffer()
        except BackendConnectionError:
            link.close()
            raise
        return CH32Connection(link)

    def validate_config(self, sample_rate=None, unit_size=None,
                        channels=None):
        caps = self.capabilities
        if sample_rate is not None and sample_rate not in caps.supported_rates:
            raise ValueError(
                _("Unsupported sample rate {rate} Hz for the {name} backend; "
                  "supported rates: {rates} Hz").format(
                    rate=sample_rate, name=caps.display_name,
                    rates=", ".join(str(r) for r in caps.supported_rates)))
        if unit_size is not None and unit_size not in caps.supported_unit_sizes:
            raise ValueError(
                _("Unsupported byte mode {unit} byte(s) per sample for the "
                  "{name} backend; supported byte modes: {units}").format(
                    unit=unit_size, name=caps.display_name,
                    units=", ".join(str(u) for u in caps.supported_unit_sizes)))
        if channels is not None:
            count = channels if isinstance(channels, int) else len(channels)
            if count != caps.channel_count:
                raise ValueError(
                    _("Unsupported channel count {count} for the {name} "
                      "backend; supported channel count: {supported}"
                      ).format(count=count, name=caps.display_name,
                               supported=caps.channel_count))
