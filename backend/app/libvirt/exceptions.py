class LibvirtLayerError(Exception):
    """Base class for errors raised by the libvirt access layer."""


class ConnectionUnavailableError(LibvirtLayerError):
    """Raised when a libvirt connection cannot be established or has dropped."""


class DomainNotFoundError(LibvirtLayerError):
    """Raised when a requested domain (VM) does not exist."""

    def __init__(self, identifier: str) -> None:
        super().__init__(f"domain not found: {identifier}")
        self.identifier = identifier


class InvalidDomainStateError(LibvirtLayerError):
    """Raised when an operation is not valid for the domain's current state."""

    def __init__(self, identifier: str, state: str, operation: str) -> None:
        super().__init__(f"cannot {operation} domain {identifier} while it is {state}")
        self.identifier = identifier
        self.state = state
        self.operation = operation
