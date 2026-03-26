from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.models.access_log import AccessLog
from src.schemas.access_log import AccessLogCreate
from src.utils.logger import logger


def create_access_log(db: Session, log: AccessLogCreate) -> AccessLog:
    """Create a new access log entry in the database."""
    logger.debug(f"Creating access log for card '{log.card_id}', result: {log.result}")
    try:
        db_log = AccessLog(**log.model_dump())
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log
    except SQLAlchemyError as e:
        logger.error(f"Failed to create access log: {e}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error while creating access log: {e}")
        db.rollback()
        raise


def get_access_logs(
    db: Session, skip: int = 0, limit: int = 100, locker_id: Optional[int] = None
) -> List[AccessLog]:
    """Retrieve access logs, optionally filtered by locker_id, ordered by most recent."""
    logger.debug(
        f"Fetching access logs (locker_id={locker_id}, skip={skip}, limit={limit})"
    )
    try:
        query = db.query(AccessLog)

        if locker_id is not None:
            query = query.filter(AccessLog.locker_id == locker_id)

        logs = (
            query.order_by(AccessLog.timestamp.desc()).offset(skip).limit(limit).all()
        )
        return logs
    except SQLAlchemyError as e:
        logger.error(f"Failed to fetch access logs: {e}")
        raise
