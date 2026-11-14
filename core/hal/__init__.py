# -*- coding: utf-8 -*-
"""Hardware abstraction layer: public API and backend registry.

Importing this package registers the real CH32 backend and makes it the
default. The upper layers obtain the currently selected backend with
:func:`current_backend` and read every hardware value from its
:class:`~core.hal.base.DeviceCapabilities`.

Adding a new real board later means adding one backend module, importing
it here, and calling :func:`register_backend`; the pickers in the CLI
and the GUI list it automatically.
"""
from ..config import get as config_get
from ..config import set as config_set
from ..i18n import _
from .base import (
    BackendConnectionError,
    DeviceBackend,
    DeviceCapabilities,
    DeviceConnection,
)

BACKENDS = {}          # backend id -> DeviceBackend instance
DEVICE_KEY = "device_backend"
DEFAULT_BACKEND_ID = "ch32"


def register_backend(backend):
    """Register one real device backend under its id."""
    BACKENDS[backend.id] = backend


def list_backends():
    """Return the registered backends in registration order."""
    return list(BACKENDS.values())


def get_backend(backend_id):
    """Return the registered backend for ``backend_id``.

    An unknown id raises a clear error.
    """
    try:
        return BACKENDS[backend_id]
    except KeyError:
        raise ValueError(
            _("Unknown device backend: {id}. Available backends: {ids}"
              ).format(id=backend_id,
                       ids=", ".join(sorted(BACKENDS)))) from None


def current_backend():
    """Return the currently selected backend.

    Reads the ``device_backend`` config key and falls back to the default
    when the key is missing or unknown.
    """
    backend_id = config_get(DEVICE_KEY, DEFAULT_BACKEND_ID)
    if backend_id not in BACKENDS:
        backend_id = DEFAULT_BACKEND_ID
    return BACKENDS[backend_id]


def select_backend(backend_id):
    """Persist the selected backend and return it.

    An unknown id raises a clear error and changes nothing.
    """
    backend = get_backend(backend_id)
    config_set(DEVICE_KEY, backend_id)
    return backend


from .ch32 import CH32Backend  # noqa: E402

register_backend(CH32Backend())

__all__ = [
    "BACKENDS",
    "DEFAULT_BACKEND_ID",
    "DEVICE_KEY",
    "BackendConnectionError",
    "DeviceBackend",
    "DeviceCapabilities",
    "DeviceConnection",
    "current_backend",
    "get_backend",
    "list_backends",
    "register_backend",
    "select_backend",
]
