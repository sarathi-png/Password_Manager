from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import AuditLog, User
from ..schemas import AuditOut

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(
    limit: int = Query(default=200, le=1000),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()