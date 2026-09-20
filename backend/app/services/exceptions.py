class ServiceError(Exception):
    """Base class for domain-specific errors raised by the service layer."""


class InvalidCredentialsError(ServiceError):
    pass


class VMNotFoundError(ServiceError):
    def __init__(self, uuid: str) -> None:
        super().__init__(f"VM not found: {uuid}")
        self.uuid = uuid


class VMOperationError(ServiceError):
    pass
