# -*- coding: utf-8 -*-
"""Hardware abstraction layer: abstract interfaces and capability data.

This module defines the contracts every device backend must follow:

- ``DeviceCapabilities`` declares the real, measured properties of a board
  (baud rates, channel count and names, sample rate, byte mode, control
  lines). The upper layers must read every hardware value from here and
  never hard-code board parameters.
- ``DeviceConnection`` is a live connection to a real board.
- ``DeviceBackend`` is one real board: port enumeration, connection, and
  configuration validation.

Hard rule: only real devices exist. There is no simulated, virtual, or
generated data source anywhere in this layer; connections only carry data
that a real board actually sent.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class BackendConnectionError(Exception):
    """A readable error raised when a real device cannot be opened or used.

    Backends translate their low-level port errors into this type so that
    the upper layers never need to know the underlying serial library.
    """


@dataclass(frozen=True)
class DeviceCapabilities:
    """The real capabilities of one device backend.

    All fields are hardware facts of the real board; the upper layers
    derive menus, defaults, and file metadata strictly from this object.
    """

    backend_id: str
    display_name: str
    channel_count: int
    channel_names: list = field(default_factory=list)
    sample_rate: int = 0
    supported_rates: list = field(default_factory=list)
    unit_size: int = 1
    supported_unit_sizes: list = field(default_factory=list)
    data_baud: int = 0
    signal_baud: int = 0
    assert_control_lines: bool = False


class DeviceConnection(ABC):
    """An open connection to a real device.

    Live loops keep their current shape through the ``in_waiting``
    property and the non-blocking ``read_available`` call.
    """

    @property
    @abstractmethod
    def in_waiting(self):
        """Number of bytes currently waiting in the input buffer."""

    @abstractmethod
    def read_available(self):
        """Non-blocking read of the currently waiting bytes; return bytes."""

    @abstractmethod
    def write(self, data):
        """Write ``data`` to the device; return None."""

    @abstractmethod
    def reset_input(self):
        """Discard everything currently in the input buffer."""

    @abstractmethod
    def acquire(self, n_points, timeout):
        """One-shot capture: wait until exactly ``n_points`` bytes arrive
        or ``timeout`` seconds pass; return list[int]. The connection is
        closed when the capture ends."""

    @abstractmethod
    def close(self):
        """Close the connection and release the device."""


class DeviceBackend(ABC):
    """One real development board behind a uniform interface."""

    @property
    @abstractmethod
    def id(self):
        """Stable backend id used in the configuration."""

    @property
    @abstractmethod
    def display_name(self):
        """Human-readable board name for pickers (untranslated data)."""

    @property
    @abstractmethod
    def capabilities(self):
        """The :class:`DeviceCapabilities` of this board."""

    @abstractmethod
    def list_ports(self):
        """Enumerate the real system serial ports.

        Return a list of ``(device, description)`` pairs.
        """

    @abstractmethod
    def connect(self, port, baud=None):
        """Open a connection to the real device on ``port``.

        ``baud`` defaults to the backend's data baud; a backend may accept
        its other declared rates (for example the signal baud).
        """

    @abstractmethod
    def validate_config(self, sample_rate=None, unit_size=None,
                        channels=None):
        """Verify that the requested values are within the real board's
        capabilities.

        Any value outside the capabilities raises a clear error. Values
        are never silently substituted and no data is ever fabricated.
        """
