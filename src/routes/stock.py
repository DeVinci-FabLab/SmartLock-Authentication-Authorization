from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.crud import crud_stock
from src.schemas.stock import StockCreate, StockUpdate, StockResponse
from src.utils.logger import logger

router = APIRouter(prefix="/stock", tags=["Stock"])

@router.get("/", response_model=List[StockResponse])
def read_stocks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db)
):
    """Retrieve a list of stock entries."""
    logger.debug(f"GET /stock called with skip={skip} and limit={limit}")
    
    try:
        stocks = crud_stock.get_stocks(db, skip=skip, limit=limit)
        logger.info(f"Successfully retrieved {len(stocks)} stock entries")
        return stocks
    
    except Exception as e:
        logger.exception(f"Error retrieving stock entries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve stock entries")

@router.get("/{stock_id}", response_model=StockResponse)
def read_stock(stock_id: int, db: Session = Depends(get_db)):
    """Retrieve a single stock entry by its ID."""
    logger.debug(f"GET /stock/{stock_id} called")
    
    try:
        stock = crud_stock.get_stock(db, stock_id=stock_id)
        if stock is None:
            logger.warning(f"Stock entry with ID {stock_id} not found")
            raise HTTPException(status_code=404, detail="Stock entry not found")
        
        logger.info(f"Successfully retrieved stock entry with ID {stock_id}")
        return stock
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving stock entry with ID {stock_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve stock entry")

@router.post("/", response_model=StockResponse, status_code=201)
def create_stock(stock: StockCreate, db: Session = Depends(get_db)):
    """Create a new stock entry."""
    logger.info(f"POST /stock called for item_id: {stock.item_id}")
    
    try:
        new_stock = crud_stock.create_stock(db, stock=stock)
        logger.success(f"Successfully created stock entry with ID {new_stock.id}")
        return new_stock
    
    except Exception as e:
        logger.exception(f"Error creating stock entry: {e}")
        raise HTTPException(status_code=500, detail="Failed to create stock entry")

@router.put("/{stock_id}", response_model=StockResponse)
def update_stock(
    stock_id: int,
    stock_update: StockUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing stock entry."""
    logger.info(f"PUT /stock/{stock_id} called")
    
    try:
        stock = crud_stock.update_stock(db, stock_id=stock_id, stock_update=stock_update)
        if stock is None:
            logger.warning(f"Stock entry with ID {stock_id} not found for update")
            raise HTTPException(status_code=404, detail="Stock entry not found")
        
        logger.success(f"Successfully updated stock entry with ID {stock_id}")
        return stock

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating stock entry with ID {stock_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update stock entry")

@router.delete("/{stock_id}", response_model=StockResponse)
def delete_stock_endpoint(stock_id: int, db: Session = Depends(get_db)):
    """Delete a stock entry."""
    logger.info(f"DELETE /stock/{stock_id} called")
    
    try:
        stock = crud_stock.delete_stock(db, stock_id=stock_id)
        if stock is None:
            logger.warning(f"Stock entry with ID {stock_id} not found for deletion")
            raise HTTPException(status_code=404, detail="Stock entry not found")
        
        logger.success(f"Successfully deleted stock entry with ID {stock_id}")
        return stock
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting stock entry with ID {stock_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete stock entry")