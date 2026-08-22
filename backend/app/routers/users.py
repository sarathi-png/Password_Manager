from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import security
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import AuditLog, User
from ..schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    user = User(
        username=body.username,
        password_hash=security.hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.flush()
    db.add(AuditLog(user_id=admin.id, action="user.create", target=user.username, detail=f"role={user.role}"))
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id and (body.role == "employee" or body.is_active is False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot demote or disable yourself")
    if body.password:
        user.password_hash = security.hash_password(body.password)
    if body.role:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    db.add(AuditLog(user_id=admin.id, action="user.update", target=user.username,
                    detail=f"role={user.role} active={user.is_active}"))
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    db.delete(user)
    db.add(AuditLog(user_id=admin.id, action="user.delete", target=user.username))
    db.commit()