from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.keycloak import require_admin
from src.crud import crud_locker_permission as crud
from src.database.session import get_db
from src.models.lockers import Lockers
from src.schemas.locker_permission import (
    LockerPermissionCreate,
    LockerPermissionResponse,
    LockerPermissionUpdate,
)

# On applique require_admin à l'ensemble du routeur !
router = APIRouter(
    prefix="/lockers",
    tags=["Locker Permissions"],
    dependencies=[Depends(require_admin)],
)


@router.post("/{locker_id}/permissions", response_model=LockerPermissionResponse)
def create_permission(
    locker_id: int, permission: LockerPermissionCreate, db: Session = Depends(get_db)
):
    if not db.query(Lockers).filter(Lockers.id == locker_id).first():
        raise HTTPException(status_code=404, detail="Locker not found")
    if locker_id != permission.locker_id:
        raise HTTPException(
            status_code=400,
            detail="Locker ID dans l'URL et dans le body ne correspondent pas.",
        )
    try:
        return crud.create_locker_permission(db, permission)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{locker_id}/permissions", response_model=List[LockerPermissionResponse])
def get_permissions(locker_id: int, db: Session = Depends(get_db)):
    return crud.get_locker_permissions_by_locker(db, locker_id)


@router.put("/permissions/{permission_id}", response_model=LockerPermissionResponse)
def update_permission(
    permission_id: int,
    permission: LockerPermissionUpdate,
    db: Session = Depends(get_db),
):
    updated = crud.update_locker_permission(db, permission_id, permission)
    if not updated:
        raise HTTPException(status_code=404, detail="Permission introuvable")
    return updated


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(permission_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_locker_permission(db, permission_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Permission introuvable")
