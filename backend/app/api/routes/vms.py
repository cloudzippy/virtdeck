from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, get_current_user, get_db, require_role
from app.models.user import Role
from app.schemas.vm import VMSummary
from app.services import vm_service
from app.services.exceptions import VMNotFoundError, VMOperationError

router = APIRouter(prefix="/api/vms", tags=["vms"])

_CAN_OPERATE = require_role(Role.ADMIN, Role.OPERATOR)
_CAN_DELETE = require_role(Role.ADMIN)


@router.get("", response_model=list[VMSummary])
async def list_vms(_user: CurrentUser = Depends(get_current_user)) -> list[VMSummary]:
    try:
        summaries = await vm_service.list_vms()
    except VMOperationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return [VMSummary(**s.__dict__) for s in summaries]


@router.get("/{uuid}", response_model=VMSummary)
async def get_vm(uuid: str, _user: CurrentUser = Depends(get_current_user)) -> VMSummary:
    try:
        summary = await vm_service.get_vm(uuid)
    except VMNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except VMOperationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return VMSummary(**summary.__dict__)


@router.post("/{uuid}/start", response_model=VMSummary)
async def start_vm(
    uuid: str, user: CurrentUser = Depends(_CAN_OPERATE), db: Session = Depends(get_db)
) -> VMSummary:
    try:
        summary = await vm_service.start_vm(db, user.id, uuid)
    except VMNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except VMOperationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return VMSummary(**summary.__dict__)


@router.post("/{uuid}/shutdown", response_model=VMSummary)
async def shutdown_vm(
    uuid: str, user: CurrentUser = Depends(_CAN_OPERATE), db: Session = Depends(get_db)
) -> VMSummary:
    try:
        summary = await vm_service.shutdown_vm(db, user.id, uuid)
    except VMNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except VMOperationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return VMSummary(**summary.__dict__)


@router.post("/{uuid}/force-stop", response_model=VMSummary)
async def force_stop_vm(
    uuid: str, user: CurrentUser = Depends(_CAN_OPERATE), db: Session = Depends(get_db)
) -> VMSummary:
    try:
        summary = await vm_service.force_stop_vm(db, user.id, uuid)
    except VMNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except VMOperationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return VMSummary(**summary.__dict__)


@router.post("/{uuid}/reboot", response_model=VMSummary)
async def reboot_vm(
    uuid: str, user: CurrentUser = Depends(_CAN_OPERATE), db: Session = Depends(get_db)
) -> VMSummary:
    try:
        summary = await vm_service.reboot_vm(db, user.id, uuid)
    except VMNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except VMOperationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return VMSummary(**summary.__dict__)


@router.delete("/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vm(
    uuid: str, user: CurrentUser = Depends(_CAN_DELETE), db: Session = Depends(get_db)
) -> None:
    try:
        await vm_service.delete_vm(db, user.id, uuid)
    except VMOperationError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
