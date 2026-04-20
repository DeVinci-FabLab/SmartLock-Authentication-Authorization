from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.keycloak import require_admin, validate_jwt
from src.crud import crud_items
from src.database.session import get_db
from src.models.categories import Categories
from src.schemas.items import ItemCreate, ItemResponse, ItemUpdate
from src.utils.logger import logger

router = APIRouter(prefix="/items", tags=["Items"])


@router.get(
    "/",
    response_model=list[ItemResponse],
    dependencies=[Depends(validate_jwt)],
)
def read_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
):
    """Retrieve a list of items."""
    logger.debug(f"GET /items called with skip={skip} and limit={limit}")

    try:
        items = crud_items.get_items(db, skip=skip, limit=limit)
        logger.info(f"Successfully retrieved {len(items)} items")
        return items

    except Exception as e:
        logger.exception(f"Error retrieving items: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve items")


@router.get(
    "/{item_id}",
    response_model=ItemResponse,
    dependencies=[Depends(validate_jwt)],
)
def read_item(item_id: int, db: Session = Depends(get_db)):
    """Retrieve a single item by its ID."""
    logger.debug(f"GET /items/{item_id} called")

    try:
        item = crud_items.get_item(db, item_id=item_id)
        if item is None:
            logger.warning(f"Item with ID {item_id} not found")
            raise HTTPException(status_code=404, detail="Item not found")

        logger.info(f"Successfully retrieved item with ID {item_id}")
        return item

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving item with ID {item_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve item")


@router.post(
    "/",
    response_model=ItemResponse,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """Create a new item."""
    logger.info(f"POST /items called with item name: {item.name}")

    if not db.query(Categories).filter(Categories.id == item.category_id).first():
        raise HTTPException(status_code=404, detail="Category not found")

    try:
        new_item = crud_items.create_item(db, item=item)
        logger.success(f"Successfully created item with ID {new_item.id}")
        return new_item

    except Exception as e:
        logger.exception(f"Error creating item: {e}")
        raise HTTPException(status_code=500, detail="Failed to create item")


@router.put(
    "/{item_id}",
    response_model=ItemResponse,
    dependencies=[Depends(require_admin)],
)
def update_item(
    item_id: int,
    item_update: ItemUpdate,
    db: Session = Depends(get_db),
):
    """Update an existing item."""
    logger.info(f"PUT /items/{item_id} called")

    try:
        item = crud_items.update_item(db, item_id=item_id, item_update=item_update)
        if item is None:
            logger.warning(f"Item with ID {item_id} not found for update")
            raise HTTPException(status_code=404, detail="Item not found")

        logger.success(f"Successfully updated item with ID {item_id}")
        return item

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error updating item with ID {item_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update item")


@router.delete(
    "/{item_id}",
    response_model=ItemResponse,
    dependencies=[Depends(require_admin)],
)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Delete an item."""
    logger.info(f"DELETE /items/{item_id} called")

    try:
        item = crud_items.delete_item(db, item_id=item_id)
        if item is None:
            logger.warning(f"Item with ID {item_id} not found for deletion")
            raise HTTPException(status_code=404, detail="Item not found")

        logger.success(f"Successfully deleted item with ID {item_id}")
        return item

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting item with ID {item_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete item")
