from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.models.categories import Categories
from src.schemas.categories import CategoryCreate, CategoryUpdate
from src.utils.logger import logger

def create_categories(db:Session, categories: CategoryCreate) -> Categories:
    """Create a new category in the database."""
    
    logger.info(f"Creating category with name: {categories.name}")
    
    try: 
        db_category = Categories(**categories.model_dump())
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        
        logger.success(f"Category created successfully with ID: {db_category.id}")
        return db_category
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to create category: {e}")
        db.rollback()
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error while creating category: {e}")
        db.rollback()
        raise

def get_categories(db:Session, skip:int=0, limit:int=100) -> list[Categories]:
    """Retrieve a list of categories from the database."""
    logger.debug(f"Fetching categories with skip={skip} and limit={limit}")
    
    try:
        categories = db.query(Categories).offset(skip).limit(limit).all()
        logger.info(f"Fetched {len(categories)} categories successfully")
        return categories
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch categories: {e}")
        raise

def get_category(db:Session, category_id:int) -> Categories | None:
    """Retrieve a single category by its ID."""
    logger.debug(f"Fetching category with ID: {category_id}")
    
    try:
        category = db.query(Categories).filter(Categories.id == category_id).first()
        logger.info(f"Category with ID {category_id} fetched successfully")
        return category
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch category with ID {category_id}: {e}")
        raise

def update_category(db:Session, category_id:int, category_update: CategoryUpdate) -> Categories | None:
    """Update an existing category in the database."""
    logger.info(f"Updating category with ID: {category_id}")
    try: 
        db_category = db.query(Categories).filter(Categories.id == category_id).first()
        
        if not db_category:
            logger.warning(f"Category with ID {category_id} not found. Cannot update.")
            return None
        
        update_data = category_update.model_dump(exclude_unset=True)
        logger.debug(f"Update data for category ID {category_id}: {update_data}")
        
        for key, value in category_update.model_dump(exclude_unset=True).items():
            setattr(db_category, key, value)
            
        db.commit()
        db.refresh(db_category)
        
        logger.success(f"Category with ID {category_id} updated successfully")
        return db_category
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to update category with ID {category_id}: {e}")
        db.rollback()
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error while updating category with ID {category_id}: {e}")
        db.rollback()
        raise

def delete_category(db:Session, category_id:int) -> Categories | None:
    """Delete a category from the database."""
    logger.warning(f"Attempting to delete category with ID: {category_id}")
    
    try:
        db_category = db.query(Categories).filter(Categories.id == category_id).first()
        
        if not db_category:
            logger.warning(f"Category with ID {category_id} not found. Cannot delete.")
            return None
        
        db.delete(db_category)
        db.commit()
        
        logger.success(f"Category with ID {category_id} deleted successfully")
        return db_category
    
    except SQLAlchemyError as e:
        logger.error(f"Failed to delete category with ID {category_id}: {e}")
        db.rollback()
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error while deleting category with ID {category_id}: {e}")
        db.rollback()
        raise