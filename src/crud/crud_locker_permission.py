from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from src.models.locker_permission import Locker_Permission
from src.schemas.locker_permission import LockerPermissionCreate, LockerPermissionUpdate
from src.utils.logger import logger


def create_locker_permission(db: Session, perm: LockerPermissionCreate) -> Locker_Permission:
    logger.info(f"Creating permission for role '{perm.role_name}' on locker ID {perm.locker_id}")
    try:
        db_perm = Locker_Permission(
            locker_id=perm.locker_id,
            role_name=perm.role_name,
            permission_level=perm.permission_level,
            valid_until=perm.valid_until,
        )
        db.add(db_perm)
        db.commit()
        db.refresh(db_perm)
        logger.success(f"Permission created with ID: {db_perm.id}")
        return db_perm
    except IntegrityError:
        logger.warning("Permission already exists for this role/locker combination.")
        db.rollback()
        raise ValueError("A permission for this role and locker already exists.")
    except SQLAlchemyError as e:
        logger.error(f"Failed to create locker permission: {e}")
        db.rollback()
        raise


def get_locker_permissions_by_locker(db: Session, locker_id: int) -> list[Locker_Permission]:
    logger.debug(f"Fetching permissions for locker ID: '{locker_id}'")
    try:
        permissions = (
            db.query(Locker_Permission)
            .filter(Locker_Permission.locker_id == locker_id)
            .all()
        )
        logger.info(f"Fetched {len(permissions)} permissions for locker ID '{locker_id}'")
        return permissions
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch permissions for locker ID '{locker_id}': {e}")
        raise


def update_locker_permission(
    db: Session, permission_id: int, update: LockerPermissionUpdate
) -> Locker_Permission | None:
    logger.info(f"Updating locker permission with ID: {permission_id}")
    try:
        db_perm = db.query(Locker_Permission).filter(Locker_Permission.id == permission_id).first()
        if not db_perm:
            logger.warning(f"Locker permission with ID {permission_id} not found.")
            return None
        for key, val in update.model_dump(exclude_unset=True).items():
            setattr(db_perm, key, val)
        db.commit()
        db.refresh(db_perm)
        logger.success(f"Locker permission with ID {permission_id} updated successfully")
        return db_perm
    except SQLAlchemyError as e:
        logger.error(f"Failed to update locker permission with ID {permission_id}: {e}")
        db.rollback()
        raise


def delete_locker_permission(db: Session, permission_id: int) -> Locker_Permission | None:
    logger.warning(f"Attempting to delete locker permission with ID: {permission_id}")
    try:
        db_perm = db.query(Locker_Permission).filter(Locker_Permission.id == permission_id).first()
        if not db_perm:
            logger.warning(f"Locker permission with ID {permission_id} not found.")
            return None
        db.delete(db_perm)
        db.commit()
        logger.success(f"Locker permission with ID {permission_id} deleted successfully")
        return db_perm
    except SQLAlchemyError as e:
        logger.error(f"Failed to delete locker permission with ID {permission_id}: {e}")
        db.rollback()
        raise
