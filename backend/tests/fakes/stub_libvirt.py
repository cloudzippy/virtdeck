"""Minimal stand-in for the `libvirt` C-extension package.

Loaded only when the real `libvirt-python` bindings aren't installed (e.g. a
plain container without `libvirt-dev` headers). Its only job is to let
`app.libvirt.*` modules import successfully so unit tests can monkeypatch
their functions directly, per the "mock the libvirt layer" testing rule in
AGENTS.md. It implements no real virtualization behavior.

On a real dev machine or CI runner with libvirt-dev installed, the real
`libvirt-python` package takes precedence and this stub is never loaded (see
`tests/conftest.py`). Integration tests that need real libvirt behavior skip
themselves when this stub is in use.
"""

VIR_DOMAIN_NOSTATE = 0
VIR_DOMAIN_RUNNING = 1
VIR_DOMAIN_BLOCKED = 2
VIR_DOMAIN_PAUSED = 3
VIR_DOMAIN_SHUTDOWN = 4
VIR_DOMAIN_SHUTOFF = 5
VIR_DOMAIN_CRASHED = 6
VIR_DOMAIN_PMSUSPENDED = 7


class libvirtError(Exception):
    pass


class virDomain:  # pragma: no cover - structural stand-in only
    pass


class virConnect:  # pragma: no cover - structural stand-in only
    pass


def open(uri: str) -> virConnect:  # noqa: A001 - matches libvirt's real API name
    raise libvirtError(
        f"stub libvirt module cannot open real connections (uri={uri!r}); "
        "install libvirt-dev and libvirt-python to run integration tests"
    )
