from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.crud import crud_lockers
from src.schemas.lockers import LockerCreate, LockerUpdate, LockerResponse
from src.schemas.stock import StockResponse
from src.utils.logger import logger

router = APIRouter(prefix="/lockers", tags=["Lockers"])

@router.get("/", response_model=List[LockerResponse])
def read_lockers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db)
):
    """Retrieve a list of lockers."""
    logger.debug(f"GET /lockers called with skip={skip} and limit={limit}")
    
    try:
        lockers = crud_lockers.get_lockers(db, skip=skip, limit=limit)
        logger.info(f"Successfully retrieved {len(lockers)} lockers")
        return lockers
    
    except Exception as e:
        logger.exception(f"Error retrieving lockers: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve lockers")

@router.get("/{locker_id}", response_model=LockerResponse)
def read_locker(locker_id: int, db: Session = Depends(get_db)):
    """Retrieve a single locker by its ID."""
    logger.debug(f"GET /lockers/{locker_id} called")
    
    try:
        locker = crud_lockers.get_locker(db, locker_id=locker_id)
        if locker is None:
            logger.warning(f"Locker with ID {locker_id} not found")
            raise HTTPException(status_code=404, detail="Locker not found")
        
        logger.info(f"Successfully retrieved locker with ID {locker_id}")
        return locker
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving locker with ID {locker_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve locker")

@router.get("/{locker_id}/stock", response_model=List[StockResponse])
def get_locker_stock_endpoint(locker_id: int, db: Session = Depends(get_db)):
    """
    Retrieve all stock items in a specific locker.
    
    Returns a list of stock entries for the given locker.
    """
    logger.debug(f"GET /lockers/{locker_id}/stock called")
    
    try:
        stock = crud_lockers.get_locker_stock(db, locker_id=locker_id)
        
        if not stock:
            logger.info(f"No stock found for locker with ID {locker_id}")
            return []  
        
        logger.info(f"Successfully retrieved {len(stock)} stock items for locker {locker_id}")
        return stock
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving stock for locker with ID {locker_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve locker stock")

@router.post("/", response_model=LockerResponse, status_code=201)
def create_locker(locker: LockerCreate, db: Session = Depends(get_db)):
    """Create a new locker."""
    logger.info(f"POST /lockers called")
    
    try:
        new_locker = crud_lockers.create_locker(db, locker=locker)
        logger.success(f"Successfully created locker with ID {new_locker.id}")
        return new_locker
    
    except Exception as e:
        logger.exception(f"Error creating locker: {e}")
        raise HTTPException(status_code=500, detail="Failed to create locker")

@router.put("/{locker_id}", response_model=LockerResponse)
def update_locker(
    locker_id: int,
    locker_update: LockerUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing locker."""
    logger.info(f"PUT /lockers/{locker_id} called")
    
    try:
        locker = crud_lockers.update_locker(db, locker_id=locker_id, locker_update=locker_update)
        if locker is None:
            logger.warning(f"Locker with ID {locker_id} not found for update")
            raise HTTPException(status_code=404, detail="Locker not found")
        
        logger.success(f"Successfully updated locker with ID {locker_id}")
        return locker

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating locker with ID {locker_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update locker")
  
@router.delete("/{locker_id}", response_model=LockerResponse)
def delete_locker_endpoint(locker_id: int, db: Session = Depends(get_db)):
    """Delete a locker."""
    logger.info(f"DELETE /lockers/{locker_id} called")
    
    try:
        locker = crud_lockers.delete_locker(db, locker_id=locker_id)
        if locker is None:
            logger.warning(f"Locker with ID {locker_id} not found for deletion")
            raise HTTPException(status_code=404, detail="Locker not found")
        
        logger.success(f"Successfully deleted locker with ID {locker_id}")
        return locker
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting locker with ID {locker_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete locker")