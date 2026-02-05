from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.models.items import Items
from src.schemas.items import ItemCreate, ItemUpdate
from src.utils.logger import logger

def create_item(db: Session, item: ItemCreate) -> Items:
    """Create a new item in the database."""
    
    logger.info(f"Creating item with name: {item.name}")
    
    try:
        db_item = Items(**item.model_dump())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
    
        logger.success(f"Item created successfully with ID: {db_item.id}")
        return db_item
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to create item: {e}")
        db.rollback()
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error while creating item: {e}")
        db.rollback()
        raise

def get_items(db: Session, skip: int = 0, limit: int = 100) -> list[Items]:
    """Retrieve a list of items from the database."""
    logger.debug(f"Fetching items with skip={skip} and limit={limit}")
    
    try:
        items = db.query(Items).offset(skip).limit(limit).all()
        logger.info(f"Fetched {len(items)} items successfully")
        return items
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch items: {e}")
        raise

def get_item(db: Session, item_id: int) -> Items | None:
    """Retrieve a single item by its ID."""
    logger.debug(f"Fetching item with ID: {item_id}")
    
    try:
        item = db.query(Items).filter(Items.id == item_id).first()
        logger.info(f"Item with ID {item_id} fetched successfully")
        return item
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch item with ID {item_id}: {e}")
        raise

def update_item(db: Session, item_id: int, item_update: ItemUpdate) -> Items | None:
    """Update an existing item in the database."""
    logger.info(f"Updating item with ID: {item_id}")
    
    try:
        db_item = db.query(Items).filter(Items.id == item_id).first()
        if not db_item:
            logger.warning(f"Item with ID {item_id} not found. Cannot update.")
            return None
        
        update_data = item_update.model_dump(exclude_unset=True)
        logger.debug(f"Update data for item ID {item_id}: {update_data}")
        
        for key, value in update_data.items():
            setattr(db_item, key, value)
            
        db.commit()
        db.refresh(db_item)
        logger.success(f"Item with ID {item_id} updated successfully")
        return db_item
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to update item with ID {item_id}: {e}")
        db.rollback()
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error while updating item with ID {item_id}: {e}")
        db.rollback()
        raise

def delete_item(db: Session, item_id: int) -> Items | None:
    """Delete an item from the database."""
    logger.warning(f"Attempting to delete item with ID: {item_id}")
    
    try:
        db_item = db.query(Items).filter(Items.id == item_id).first()
        if not db_item:
            logger.warning(f"Item with ID {item_id} not found. Cannot delete.")
            return None
        
        db.delete(db_item)
        db.commit()
        logger.success(f"Item with ID {item_id} deleted successfully")
        return db_item
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to delete item with ID {item_id}: {e}")
        db.rollback()
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error while deleting item with ID {item_id}: {e}")
        db.rollback()
        raise