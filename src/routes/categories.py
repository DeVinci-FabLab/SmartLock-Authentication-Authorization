from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database.session import get_db
from src.crud import crud_categories
from src.schemas.categories import CategoryCreate, CategoryUpdate, CategoryResponse
from src.utils.logger import logger

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("/", response_model=List[CategoryResponse])
def read_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db)
):
    """Retrieve a list of categories."""
    logger.debug(f"GET /categories called with skip={skip} and limit={limit}")
    
    try:
        categories = crud_categories.get_categories(db, skip=skip, limit=limit)
        logger.info(f"Successfully retrieved {len(categories)} categories")
        return categories
    
    except Exception as e:
        logger.exception(f"Error retrieving categories: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve categories")

@router.get("/{category_id}", response_model=CategoryResponse)
def read_category(category_id: int, db: Session = Depends(get_db)):
    """Retrieve a single category by its ID."""
    
    logger.debug(f"GET /categories/{category_id} called")
    
    try:
        category = crud_categories.get_category(db, category_id=category_id)
        if category is None:
            logger.warning(f"Category with ID {category_id} not found")
            raise HTTPException(status_code=404, detail="Category not found")
        
        logger.info(f"Successfully retrieved category with ID {category_id}")
        return category
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving category with ID {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve category")

@router.post("/", response_model=CategoryResponse, status_code=201)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new category."""
    
    logger.info(f"POST /categories called with category name: {category.name}")
    
    try:
        new_category = crud_categories.create_categories(db, categories=category)
        logger.success(f"Successfully created category with ID {new_category.id}")
        
        return new_category
    
    except Exception as e:
        logger.exception(f"Error creating category: {e}")
        raise HTTPException(status_code=500, detail="Failed to create category")

@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: Session = Depends(get_db)
):
    """Update an existing category."""
    
    logger.info(f"PUT /categories/{category_id} called")
    try:
        category = crud_categories.update_category(
            
        db, category_id=category_id, category_update=category_update
        )
        if category is None:
            logger.warning(f"Category with ID {category_id} not found for update")
            raise HTTPException(status_code=404, detail="Category not found")
        
        logger.success(f"Successfully updated category with ID {category_id}")
        return category

    except HTTPException:
        raise
    
    except Exception as e:
        logger.exception(f"Error updating category with ID {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update category")

@router.delete("/{category_id}", response_model=CategoryResponse)
def delete_category_endpoint(category_id: int, db: Session = Depends(get_db)):
    """Delete a category."""
    
    logger.info(f"DELETE /categories/{category_id} called")
    try:
        category = crud_categories.delete_category(db, category_id=category_id)
        
        if category is None:
            logger.warning(f"Category with ID {category_id} not found for deletion")
            raise HTTPException(status_code=404, detail="Category not found")
        
        logger.success(f"Successfully deleted category with ID {category_id}")
        return category
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.exception(f"Error deleting category with ID {category_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete category")