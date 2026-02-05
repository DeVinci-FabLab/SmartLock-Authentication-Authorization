from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.models.stock import Stock
from src.schemas.stock import StockCreate, StockUpdate
from src.utils.logger import logger

def create_stock(db: Session, stock: StockCreate) -> Stock:
    """Create a new stock entry in the database."""
    logger.info(f"Creating stock entry for item_id: {stock.item_id}")
    try:
        db_stock = Stock(**stock.model_dump())
        db.add(db_stock)
        db.commit()
        db.refresh(db_stock)
        logger.success(f"Stock created successfully with ID: {db_stock.id}")
        return db_stock
    except SQLAlchemyError as e:
        logger.error(f"Failed to create stock: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while creating stock: {e}")
        db.rollback()
        raise

def get_stocks(db: Session, skip: int = 0, limit: int = 100) -> list[Stock]:
    """Retrieve a list of stock entries from the database."""
    logger.debug(f"Fetching stocks with skip={skip} and limit={limit}")
    try:
        stocks = db.query(Stock).offset(skip).limit(limit).all()
        logger.info(f"Fetched {len(stocks)} stock entries successfully")
        return stocks
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch stocks: {e}")
        raise

def get_stock(db: Session, stock_id: int) -> Stock | None:
    """Retrieve a single stock entry by its ID."""
    logger.debug(f"Fetching stock with ID: {stock_id}")
    try:
        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        logger.info(f"Stock with ID {stock_id} fetched successfully")
        return stock
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch stock with ID {stock_id}: {e}")
        raise

def update_stock(db: Session, stock_id: int, stock_update: StockUpdate) -> Stock | None:
    """Update an existing stock entry in the database."""
    logger.info(f"Updating stock with ID: {stock_id}")
    try:
        db_stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if not db_stock:
            logger.warning(f"Stock with ID {stock_id} not found. Cannot update.")
            return None
        
        update_data = stock_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_stock, key, value)
            
        db.commit()
        db.refresh(db_stock)
        logger.success(f"Stock with ID {stock_id} updated successfully")
        return db_stock
    except SQLAlchemyError as e:
        logger.error(f"Failed to update stock with ID {stock_id}: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while updating stock with ID {stock_id}: {e}")
        db.rollback()
        raise

def delete_stock(db: Session, stock_id: int) -> Stock | None:
    """Delete a stock entry from the database."""
    logger.warning(f"Attempting to delete stock with ID: {stock_id}")
    try:
        db_stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if not db_stock:
            logger.warning(f"Stock with ID {stock_id} not found. Cannot delete.")
            return None
        
        db.delete(db_stock)
        db.commit()
        logger.success(f"Stock with ID {stock_id} deleted successfully")
        return db_stock
    except SQLAlchemyError as e:
        logger.error(f"Failed to delete stock with ID {stock_id}: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while deleting stock with ID {stock_id}: {e}")
        db.rollback()
        raise