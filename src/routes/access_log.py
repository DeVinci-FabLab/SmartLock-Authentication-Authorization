from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.keycloak import require_admin
from src.crud.crud_access_log import get_access_logs
from src.database.session import get_db
from src.schemas.access_log import AccessLogResponse

router = APIRouter(
    prefix="/logs", tags=["Audit Logs"], dependencies=[Depends(require_admin)]
)


@router.get("/", response_model=List[AccessLogResponse])
def read_logs(
    skip: int = 0,
    limit: int = 100,
    locker_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return get_access_logs(db, skip=skip, limit=limit, locker_id=locker_id)
