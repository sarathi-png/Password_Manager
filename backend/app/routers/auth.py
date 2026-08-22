from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .. import security
from ..database import get_db
from ..deps import get_current_user
from ..models import AuditLog, User
from ..schemas import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "unknown"
    if not security.login_limiter.allow("login", ip):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many login attempts")
    user = db.query(User).filter(User.username == body.username).first()
    if user is None or not security.verify_password(body.password, user.password_hash):
        db.add(AuditLog(user_id=None, action="login.failed", target=body.username, detail="Invalid credentials", ip=ip))
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    db.add(AuditLog(user_id=user.id, action="login.success", target=user.username, ip=ip))
    db.commit()
    return TokenResponse(access_token=security.create_access_token(user.id, user.role, user.username))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user