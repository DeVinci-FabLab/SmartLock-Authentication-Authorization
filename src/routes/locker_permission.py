from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.crud import crud_locker_permission
from src.schemas.locker_permission import (
    LockerPermissionCreate, 
    LockerPermissionUpdate, 
    LockerPermissionResponse
)
from src.utils.logger import logger

# Note: Prefix est "/permissions" mais on gère aussi des routes imbriquées plus bas
router = APIRouter(prefix="/permissions", tags=["Locker Permissions"])

@router.get("/", response_model=List[LockerPermissionResponse])
def read_locker_permission(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db)
):
    """Retrieve a list of all locker permissions."""
    logger.debug(f"GET /permissions called with skip={skip} and limit={limit}")
    
    try:
        lockers_permissions = crud_locker_permission.get_locker_permissions(db, skip=skip, limit=limit)
        logger.info(f"Successfully retrieved {len(lockers_permissions)} permissions")
        return lockers_permissions
    
    except Exception as e:
        logger.exception(f"Error retrieving permissions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve permissions")

@router.get("/{permission_id}", response_model=LockerPermissionResponse)
def read_locker_permission(
    permission_id: int = Path(..., gt=0), 
    db: Session = Depends(get_db)
):
    """Retrieve a single locker permission by its ID."""
    logger.debug(f"GET /permissions/{permission_id} called")
    
    try:
        permission = crud_locker_permission.get_locker_permission(db, permission_id=permission_id)
        if permission is None:
            logger.warning(f"Permission with ID {permission_id} not found")
            raise HTTPException(status_code=404, detail="Permission not found")
        
        logger.info(f"Successfully retrieved permission with ID {permission_id}")
        return permission
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving permission with ID {permission_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve permission")

@router.post("/", response_model=LockerPermissionResponse, status_code=201)
def create_locker_permission(
    permission: LockerPermissionCreate, 
    db: Session = Depends(get_db)
):
    """Create a new locker permission."""
    logger.info(f"POST /permissions called for role '{permission.role_name}' and locker '{permission.locker_id}'")
    
    try:
        new_permission = crud_locker_permission.create_locker_permission(db, permission=permission)
        logger.success(f"Successfully created permission with ID {new_permission.id}")
        return new_permission
    
    except ValueError as ve:
        # Gère l'erreur d'unicité (rôle/locker) remontée par le CRUD
        logger.warning(f"Validation error creating permission: {ve}")
        raise HTTPException(status_code=409, detail=str(ve)) # 409 Conflict
    except Exception as e:
        logger.exception(f"Error creating permission: {e}")
        raise HTTPException(status_code=500, detail="Failed to create permission")

@router.put("/{permission_id}", response_model=LockerPermissionResponse)
def update_locker_permission(
    permission_update: LockerPermissionUpdate,
    permission_id: int = Path(..., gt=0),
    db: Session = Depends(get_db)
):
    """Update an existing locker permission."""
    logger.info(f"PUT /permissions/{permission_id} called")
    
    try:
        permission = crud_locker_permission.update_locker_permission(
            db, permission_id=permission_id, permission_update=permission_update
        )
        if permission is None:
            logger.warning(f"Permission with ID {permission_id} not found for update")
            raise HTTPException(status_code=404, detail="Permission not found")
        
        logger.success(f"Successfully updated permission with ID {permission_id}")
        return permission

    except ValueError as ve:
        logger.warning(f"Validation error updating permission: {ve}")
        raise HTTPException(status_code=409, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating permission with ID {permission_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update permission")
  
@router.delete("/{permission_id}", response_model=LockerPermissionResponse)
def delete_locker_permission_endpoint(
    permission_id: int = Path(..., gt=0), 
    db: Session = Depends(get_db)
):
    """Delete a locker permission."""
    logger.info(f"DELETE /permissions/{permission_id} called")
    
    try:
        permission = crud_locker_permission.delete_locker_permission(db, permission_id=permission_id)
        if permission is None:
            logger.warning(f"Permission with ID {permission_id} not found for deletion")
            raise HTTPException(status_code=404, detail="Permission not found")
        
        logger.success(f"Successfully deleted permission with ID {permission_id}")
        return permission
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting permission with ID {permission_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete permission")


# --- ROUTES SPECIFIQUES (Liaison avec les armoires) ---

@router.get("/locker/{locker_id}", response_model=List[LockerPermissionResponse])
def get_permissions_by_locker(
    locker_id: str = Path(..., description="The ID (string) of the locker"),
    db: Session = Depends(get_db)
):
    """Retrieve all permissions associated with a specific locker."""
    logger.debug(f"GET /permissions/locker/{locker_id} called")
    
    try:
        permissions = crud_locker_permission.get_locker_permissions_by_locker(db, locker_id=locker_id)
        # On ne lève pas de 404 si la liste est vide, on renvoie juste []
        logger.info(f"Successfully retrieved {len(permissions)} permissions for locker '{locker_id}'")
        return permissions
    
    except Exception as e:
        logger.exception(f"Error retrieving permissions for locker '{locker_id}': {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve permissions for this locker")

@router.get("/locker/{locker_id}/role/{role_name}", response_model=LockerPermissionResponse)
def get_permission_by_role_and_locker(
    locker_id: str = Path(...),
    role_name: str = Path(...),
    db: Session = Depends(get_db)
):
    """Retrieve a specific permission by role name and locker ID."""
    logger.debug(f"GET /permissions/locker/{locker_id}/role/{role_name} called")
    
    try:
        permission = crud_locker_permission.get_permission_by_role_and_locker(
            db, role_name=role_name, locker_id=locker_id
        )
        if permission is None:
            logger.warning(f"No permission found for role '{role_name}' on locker '{locker_id}'")
            raise HTTPException(status_code=404, detail="Permission not found for this role and locker")
        
        logger.info(f"Successfully retrieved permission for role '{role_name}' on locker '{locker_id}'")
        return permission
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving permission for role '{role_name}' and locker '{locker_id}': {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve permission")