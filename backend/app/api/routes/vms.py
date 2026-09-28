from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db, require_role
from app.models.user import Role
from app.schemas.vm import VMOwnerUpdate, VMSummary
from app.services import vm_service
from app.services.exceptions import (
    InvalidOwnerError,
    VMNotFoundError,
    VMOperationError,
    VMStateConflictError,
)

router = APIRouter(prefix="/api/vms", tags=["vms"])

_CAN_OPERATE = require_role(Role.ADMIN, Role.OPERATOR)
_ADMIN_ONLY = require_role(Role.ADMIN)


@contextmanager
def _service_errors_as_http() -> Iterator[None]:
    try:
        yield
    except VMNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except VMStateConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except InvalidOwnerError as exc:
        # Literal 422: Starlette renamed this constant, and both names aren't in every version.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except VMOperationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


def _to_schema(view: vm_service.VMView) -> VMSummary:
    return VMSummary(**view.summary.__dict__, owner_id=view.owner_id)


@router.get("", response_model=list[VMSummary])
async def list_vms(
    user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[VMSummary]:
    with _service_errors_as_http():
        views = await vm_service.list_vms(db, user)
    return [_to_schema(v) for v in views]


@router.get("/{uuid}", response_model=VMSummary)
async def get_vm(
    uuid: UUID, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> VMSummary:
    with _service_errors_as_http():
        return _to_schema(await vm_service.get_vm(db, user, str(uuid)))


@router.post("/{uuid}/start", response_model=VMSummary)
async def start_vm(
    uuid: UUID, user: CurrentUser = Depends(_CAN_OPERATE), db: Session = Depends(get_db)
) -> VMSummary:
    with _service_errors_as_http():
        return _to_schema(await vm_service.start_vm(db, user, str(uuid)))


@router.post("/{uuid}/shutdown", response_model=VMSummary)
async def shutdown_vm(
    uuid: UUID, user: CurrentUser = Depends(_CAN_OPERATE), db: Session = Depends(get_db)
) -> VMSummary:
    with _service_errors_as_http():
        return _to_schema(await vm_service.shutdown_vm(db, user, str(uuid)))


@router.post("/{uuid}/force-stop", response_model=VMSummary)
async def force_stop_vm(
    uuid: UUID, user: CurrentUser = Depends(_CAN_OPERATE), db: Session = Depends(get_db)
) -> VMSummary:
    with _service_errors_as_http():
        return _to_schema(await vm_service.force_stop_vm(db, user, str(uuid)))


@router.post("/{uuid}/reboot", response_model=VMSummary)
async def reboot_vm(
    uuid: UUID, user: CurrentUser = Depends(_CAN_OPERATE), db: Session = Depends(get_db)
) -> VMSummary:
    with _service_errors_as_http():
        return _to_schema(await vm_service.reboot_vm(db, user, str(uuid)))


@router.post("/{uuid}/pause", response_model=VMSummary)
async def pause_vm(
    uuid: UUID, user: CurrentUser = Depends(_CAN_OPERATE), db: Session = Depends(get_db)
) -> VMSummary:
    with _service_errors_as_http():
        return _to_schema(await vm_service.pause_vm(db, user, str(uuid)))


@router.post("/{uuid}/resume", response_model=VMSummary)
async def resume_vm(
    uuid: UUID, user: CurrentUser = Depends(_CAN_OPERATE), db: Session = Depends(get_db)
) -> VMSummary:
    with _service_errors_as_http():
        return _to_schema(await vm_service.resume_vm(db, user, str(uuid)))


@router.put("/{uuid}/owner", response_model=VMSummary)
async def assign_owner(
    uuid: UUID,
    payload: VMOwnerUpdate,
    user: CurrentUser = Depends(_ADMIN_ONLY),
    db: Session = Depends(get_db),
) -> VMSummary:
    owner_id = str(payload.owner_id) if payload.owner_id is not None else None
    with _service_errors_as_http():
        return _to_schema(await vm_service.assign_owner(db, user, str(uuid), owner_id))


@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vm(
    uuid: UUID, user: CurrentUser = Depends(_ADMIN_ONLY), db: Session = Depends(get_db)
) -> None:
    with _service_errors_as_http():
        await vm_service.delete_vm(db, user, str(uuid))
