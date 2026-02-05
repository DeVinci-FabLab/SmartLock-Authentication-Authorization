from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.models.lockers import Lockers
from src.schemas.lockers import LockerCreate, LockerUpdate 
from src.utils.logger import logger

def create_locker(db: Session, locker: LockerCreate) -> Lockers:
    """Create a new locker in the database."""
    logger.info(f"Creating locker with name/code: {locker.locker_type}") 
    try:
        db_locker = Lockers(**locker.model_dump())
        db.add(db_locker)
        db.commit()
        db.refresh(db_locker)
        logger.success(f"Locker created successfully with ID: {db_locker.id}")
        return db_locker
    except SQLAlchemyError as e:
        logger.error(f"Failed to create locker: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while creating locker: {e}")
        db.rollback()
        raise

def get_lockers(db: Session, skip: int = 0, limit: int = 100) -> list[Lockers]:
    """Retrieve a list of lockers from the database."""
    logger.debug(f"Fetching lockers with skip={skip} and limit={limit}")
    try:
        lockers = db.query(Lockers).offset(skip).limit(limit).all()
        logger.info(f"Fetched {len(lockers)} lockers successfully")
        return lockers
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch lockers: {e}")
        raise

def get_locker(db: Session, locker_id: int) -> Lockers | None:
    """Retrieve a single locker by its ID."""
    logger.debug(f"Fetching locker with ID: {locker_id}")
    try:
        locker = db.query(Lockers).filter(Lockers.id == locker_id).first()
        logger.info(f"Locker with ID {locker_id} fetched successfully")
        return locker
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch locker with ID {locker_id}: {e}")
        raise

def update_locker(db: Session, locker_id: int, locker_update: LockerUpdate) -> Lockers | None:
    """Update an existing locker in the database."""
    logger.info(f"Updating locker with ID: {locker_id}")
    try:
        db_locker = db.query(Lockers).filter(Lockers.id == locker_id).first()
        if not db_locker:
            logger.warning(f"Locker with ID {locker_id} not found. Cannot update.")
            return None
        
        update_data = locker_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_locker, key, value)
            
        db.commit()
        db.refresh(db_locker)
        logger.success(f"Locker with ID {locker_id} updated successfully")
        return db_locker
    except SQLAlchemyError as e:
        logger.error(f"Failed to update locker with ID {locker_id}: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while updating locker with ID {locker_id}: {e}")
        db.rollback()
        raise

def delete_locker(db: Session, locker_id: int) -> Lockers | None:
    """Delete a locker from the database."""
    logger.warning(f"Attempting to delete locker with ID: {locker_id}")
    try:
        db_locker = db.query(Lockers).filter(Lockers.id == locker_id).first()
        if not db_locker:
            logger.warning(f"Locker with ID {locker_id} not found. Cannot delete.")
            return None
        
        db.delete(db_locker)
        db.commit()
        logger.success(f"Locker with ID {locker_id} deleted successfully")
        return db_locker
    except SQLAlchemyError as e:
        logger.error(f"Failed to delete locker with ID {locker_id}: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while deleting locker with ID {locker_id}: {e}")
        db.rollback()
        raise