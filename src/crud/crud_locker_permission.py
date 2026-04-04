from typing import List

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.models.locker_permission import Locker_Permission
from src.schemas.locker_permission import LockerPermissionCreate, LockerPermissionUpdate
from src.utils.logger import logger


def create_locker_permission(
    db: Session, permission: LockerPermissionCreate
) -> Locker_Permission:
    target = (
        permission.user_id
        if permission.subject_type == "user"
        else permission.role_name
    )
    logger.info(
        f"Creating permission for {permission.subject_type} "
        f"'{target}' on locker ID {permission.locker_id}"
    )
    try:
        db_permission = Locker_Permission(**permission.model_dump())
        db.add(db_permission)
        db.commit()
        db.refresh(db_permission)

        logger.success(f"Permission created successfully with ID: {db_permission.id}")
        return db_permission

    except IntegrityError:
        logger.warning("Permission already exists for this target/locker combination.")
        db.rollback()
        raise ValueError("A permission for this target and locker already exists.")

    except SQLAlchemyError as e:
        logger.error(f"Failed to create locker permission: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while creating locker permission: {e}")
        db.rollback()
        raise


def get_locker_permissions_by_locker(
    db: Session, locker_id: int
) -> List[Locker_Permission]:
    """Retrieve all permissions associated with a specific locker."""
    logger.debug(f"Fetching permissions for locker ID: '{locker_id}'")
    try:
        permissions = (
            db.query(Locker_Permission)
            .filter(Locker_Permission.locker_id == locker_id)
            .all()
        )
        logger.info(
            f"Fetched {len(permissions)} permissions for locker ID '{locker_id}'"
        )
        return permissions
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch permissions for locker ID '{locker_id}': {e}")
        raise


def update_locker_permission(
    db: Session, permission_id: int, permission_update: LockerPermissionUpdate
) -> Locker_Permission | None:
    """Update an existing locker permission in the database."""
    logger.info(f"Updating locker permission with ID: {permission_id}")
    try:
        db_permission = (
            db.query(Locker_Permission)
            .filter(Locker_Permission.id == permission_id)
            .first()
        )
        if not db_permission:
            logger.warning(
                f"Locker permission with ID {permission_id} not found. Cannot update."
            )
            return None

        update_data = permission_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_permission, key, value)

        db.commit()
        db.refresh(db_permission)
        logger.success(
            f"Locker permission with ID {permission_id} updated successfully"
        )
        return db_permission
    except SQLAlchemyError as e:
        logger.error(f"Failed to update locker permission with ID {permission_id}: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating permission {permission_id}: {e}")
        db.rollback()
        raise


def delete_locker_permission(
    db: Session, permission_id: int
) -> Locker_Permission | None:
    """Delete a locker permission from the database."""
    logger.warning(f"Attempting to delete locker permission with ID: {permission_id}")
    try:
        db_permission = (
            db.query(Locker_Permission)
            .filter(Locker_Permission.id == permission_id)
            .first()
        )
        if not db_permission:
            logger.warning(
                f"Locker permission with ID {permission_id} not found. Cannot delete."
            )
            return None

        db.delete(db_permission)
        db.commit()
        logger.success(
            f"Locker permission with ID {permission_id} deleted successfully"
        )
        return db_permission
    except SQLAlchemyError as e:
        logger.error(f"Failed to delete locker permission with ID {permission_id}: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error deleting permission {permission_id}: {e}")
        db.rollback()
        raise
