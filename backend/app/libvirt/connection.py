"""Central libvirt connection management.

Rule: this is the only place `libvirt.open`/`libvirt.close` may be called from.
Everything else in this package (and every caller outside it) goes through
`get_connection()`. Calls here are blocking — callers must run them off the
event loop (e.g. via `asyncio.to_thread`).
"""

import contextlib
import threading

import libvirt

from app.core.config import get_settings
from app.libvirt.exceptions import ConnectionUnavailableError

_lock = threading.Lock()
_connection: libvirt.virConnect | None = None


def _open_connection() -> libvirt.virConnect:
    settings = get_settings()
    try:
        conn = libvirt.open(settings.libvirt_uri)
    except libvirt.libvirtError as exc:
        raise ConnectionUnavailableError(
            f"could not connect to libvirt at {settings.libvirt_uri!r}: {exc}"
        ) from exc
    if conn is None:
        raise ConnectionUnavailableError(
            f"libvirt.open returned no connection for {settings.libvirt_uri!r}"
        )
    return conn


def get_connection() -> libvirt.virConnect:
    """Return the shared libvirt connection, (re)opening it if needed."""
    global _connection
    with _lock:
        if _connection is not None:
            try:
                if _connection.isAlive():
                    return _connection
            except libvirt.libvirtError:
                pass
            _connection = None
        _connection = _open_connection()
        return _connection


def close_connection() -> None:
    """Close the shared connection, if open. Intended for shutdown/test teardown."""
    global _connection
    with _lock:
        if _connection is not None:
            with contextlib.suppress(libvirt.libvirtError):
                _connection.close()
            _connection = None
