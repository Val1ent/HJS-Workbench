# -*- coding: utf-8 -*-
"""CH32 backend: the real multi-rate, multi-mode, HS-capable board.

Moves the existing, verified serial behavior behind the uniform backend
interface. Every hardware value below (baud rates, channel count, sample
rates, capture modes, burst capacity, unit size, control lines,
troubleshooting text) is a declared capability of the real CH32 board
and nothing else in the repository hard-codes it.

Connection flow is identical to the previous ``open_serial``:
open at the data baud, assert DTR/RTS, wait 0.5 s, flush the input
buffer. The one-shot acquire polls non-blocking until enough bytes
arrive or the timeout, closes the port on exit, and raises the same
troubleshooting text on timeout.

Command channel: the accepted High-Speed firmware listens for ASCII
commands on the USB CDC serial port of the USB3 Type-A connector
(VID/PID 1A86:FE0C). Command replies are printed on the separate debug
UART, never echoed back on the CDC data port, so the wrappers below
only write bytes and never wait for a CDC text acknowledgement. The
multi-rate and burst features require the High-Speed firmware, the
USB3 Type-A port, and a data-capable USB3 cable; 10 kHz realtime on
the USB-C Full-Speed port stays a supported baseline.
"""
import time

from ..i18n import _
from .base import (
    BackendConnectionError,
    DeviceBackend,
    DeviceCapabilities,
    DeviceConnection,
)
from .serial_link import SerialLink, list_serial_ports

CH32_CAPABILITIES = DeviceCapabilities(
    backend_id="ch32",
    display_name="CH32 board (USB3 Type-A HS data port; USB-C Full-Speed fallback)",
    channel_count=8,
    channel_names=["D0", "D1", "D2", "D3", "D4", "D5", "D6", "D7"],
    sample_rate=10000,
    supported_rates=[10000, 100000, 500000, 1000000],
    unit_size=1,
    supported_unit_sizes=[1],
    data_baud=115200,
    signal_baud=921600,
    assert_control_lines=True,
    supported_modes=["realtime", "burst"],
    default_mode="realtime",
    burst_capacity=712704,
    data_port_name="USB3 Type-A HS data port (USB-C OTG Full-Speed fallback)",
    high_speed_required=True,
)

_TIMEOUT_MESSAGE = (
    "Capture timed out: got {got} points, need {need} points.\n"
    "Check: is the USB3 Type-A HS data port selected (not the debug "
    "port), is the board connected with a data-capable USB3 cable, "
    "is A15 looped back to D0, is the port free of other programs. "
    "The multi-rate and burst features require the High-Speed "
    "firmware; retry after these checks."
)

_MODE_COMMANDS = {"realtime": b"M0\n", "burst": b"M1\n"}


def _check_rate(caps, rate):
    """Reject a sample rate outside the board's supported rates."""
    if rate is not None and rate not in caps.supported_rates:
        raise ValueError(
            _("Unsupported sample rate {rate} Hz for the {name} backend; "
              "supported rates: {rates} Hz").format(
                rate=rate, name=caps.display_name,
                rates=", ".join(str(r) for r in caps.supported_rates)))


def _check_mode(caps, mode):
    """Reject a capture mode outside the board's supported modes."""
    if mode is not None and mode not in caps.supported_modes:
        raise ValueError(
            _("Unsupported capture mode {mode} for the {name} backend; "
              "supported modes: {modes}").format(
                mode=mode, name=caps.display_name,
                modes=", ".join(str(m) for m in caps.supported_modes)))
    if mode == "burst" and caps.burst_capacity <= 0:
        raise ValueError(
            _("The {name} backend does not support burst capture."
              ).format(name=caps.display_name))


class CH32Connection(DeviceConnection):
    """A live connection to a CH32 board (data port or signal port).

    The command methods below only write the correct ASCII bytes and
    return; the firmware applies them at the line ending (or immediately
    for the single-letter commands) and never echoes an acknowledgement
    back on this CDC data port, so none of them reads or waits.
    """

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

    def read_blocking(self, count, timeout):
        """Blocking read of up to ``count`` bytes within ``timeout``
        seconds; delegates to the wrapped serial link."""
        return self._link.read_blocking(count, timeout)

    def write(self, data):
        self._link.write(data)

    def reset_input(self):
        self._link.reset_input_buffer()

    def set_sample_rate(self, rate):
        """Send ``R<rate>LF``; the firmware applies it at the line ending.

        An unsupported rate raises a clear error and sends nothing; the
        firmware would otherwise leave the active rate unchanged.
        """
        _check_rate(CH32_CAPABILITIES, rate)
        self.write(b"R" + str(rate).encode("ascii") + b"\n")

    def set_mode(self, mode):
        """Send ``M0`` (realtime) or ``M1`` (burst) plus LF.

        An unsupported mode raises a clear error and sends nothing.
        """
        _check_mode(CH32_CAPABILITIES, mode)
        self.write(_MODE_COMMANDS[mode])

    def start_burst(self):
        """Send ``G``: start burst recording (applied immediately)."""
        self.write(b"G")

    def request_burst_upload(self):
        """Send ``T``: upload the full burst buffer (applied immediately)."""
        self.write(b"T")

    def cancel_burst(self):
        """Send ``C``: cancel or reset the burst (applied immediately)."""
        self.write(b"C")

    def query_status(self):
        """Send ``?``; the answer is printed on the debug UART, not on
        this CDC data connection."""
        self.write(b"?")

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
                        channels=None, mode=None):
        caps = self.capabilities
        _check_rate(caps, sample_rate)
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
        _check_mode(caps, mode)
