from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import security
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import AuditLog, Block, District, User
from ..schemas import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


def _to_out(u: User, db: Session) -> UserOut:
    # enrich with names
    out = UserOut.model_validate(u)
    if u.district_id:
        d = db.get(District, u.district_id)
        out.district_name = d.name if d else None
    if u.block_id:
        b = db.get(Block, u.block_id)
        out.block_name = b.name if b else None
    return out


@router.get("", response_model=list[UserOut])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id).all()
    return [_to_out(u, db) for u in users]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    # validate district/block
    if body.district_id is not None and not db.get(District, body.district_id):
        raise HTTPException(status_code=400, detail="District not found")
    if body.block_id is not None and not db.get(Block, body.block_id):
        raise HTTPException(status_code=400, detail="Block not found")
    # block must belong to district if both provided, else infer district from block
    if body.block_id is not None and body.district_id is not None:
        b = db.get(Block, body.block_id)
        if b.district_id != body.district_id:
            raise HTTPException(status_code=400, detail="Block does not belong to district")
    if body.block_id is not None and body.district_id is None:
        b = db.get(Block, body.block_id)
        body.district_id = b.district_id
    user = User(
        username=body.username,
        password_hash=security.hash_password(body.password),
        role=body.role,
        district_id=body.district_id,
        block_id=body.block_id,
    )
    db.add(user)
    db.flush()
    db.add(AuditLog(user_id=admin.id, action="user.create", target=user.username, detail=f"role={user.role} district={body.district_id} block={body.block_id}"))
    db.commit()
    db.refresh(user)
    return _to_out(user, db)


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
    # district/block update - same validation as create
    if body.district_id is not None or body.block_id is not None:
        new_district = body.district_id if body.district_id is not None else user.district_id
        new_block = body.block_id if body.block_id is not None else user.block_id
        # if clearing? allow explicit None via payload: but schema uses Optional, so None means not provided; we need explicit check for hasattr
        # For simplicity treat None as "no change" unless both provided as null? Use body.model_fields_set
        if "district_id" in body.model_fields_set:
            new_district = body.district_id
        if "block_id" in body.model_fields_set:
            new_block = body.block_id
        if new_district is not None and not db.get(District, new_district):
            raise HTTPException(status_code=400, detail="District not found")
        if new_block is not None and not db.get(Block, new_block):
            raise HTTPException(status_code=400, detail="Block not found")
        if new_block is not None and new_district is not None:
            b = db.get(Block, new_block)
            if b.district_id != new_district:
                raise HTTPException(status_code=400, detail="Block does not belong to district")
        if new_block is not None and new_district is None:
            b = db.get(Block, new_block)
            new_district = b.district_id
        user.district_id = new_district
        user.block_id = new_block
    db.add(AuditLog(user_id=admin.id, action="user.update", target=user.username,
                    detail=f"role={user.role} active={user.is_active} district={user.district_id} block={user.block_id}"))
    db.commit()
    db.refresh(user)
    return _to_out(user, db)


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