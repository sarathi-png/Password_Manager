from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import Block, District, PasswordEntry, User
from ..schemas import BlockCreate, BlockOut, DistrictCreate, DistrictOut

router = APIRouter(prefix="/api", tags=["districts"])


@router.get("/districts", response_model=list[DistrictOut])
def list_districts(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(District).order_by(District.name).all()


@router.post("/districts", response_model=DistrictOut, status_code=201)
def create_district(body: DistrictCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(District).filter(District.name == body.name.strip()).first():
        raise HTTPException(status_code=409, detail="District already exists")
    d = District(name=body.name.strip())
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.delete("/districts/{district_id}", status_code=204)
def delete_district(district_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    d = db.get(District, district_id)
    if not d:
        raise HTTPException(status_code=404, detail="District not found")
    # block deletion
    if db.query(Block).filter(Block.district_id == district_id).first():
        raise HTTPException(status_code=400, detail="District has blocks; delete blocks first")
    if db.query(PasswordEntry).filter(PasswordEntry.district_id == district_id).first() or db.query(User).filter(User.district_id == district_id).first():
        raise HTTPException(status_code=400, detail="District in use by entries/users")
    db.delete(d)
    db.commit()


@router.get("/blocks", response_model=list[BlockOut])
def list_blocks(district_id: int | None = None, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    q = db.query(Block)
    if district_id is not None:
        q = q.filter(Block.district_id == district_id)
    return q.order_by(Block.name).all()


@router.post("/blocks", response_model=BlockOut, status_code=201)
def create_block(body: BlockCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not db.get(District, body.district_id):
        raise HTTPException(status_code=404, detail="District not found")
    if db.query(Block).filter(Block.district_id == body.district_id, Block.name == body.name.strip()).first():
        raise HTTPException(status_code=409, detail="Block already exists in this district")
    b = Block(name=body.name.strip(), district_id=body.district_id)
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.delete("/blocks/{block_id}", status_code=204)
def delete_block(block_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    b = db.get(Block, block_id)
    if not b:
        raise HTTPException(status_code=404, detail="Block not found")
    if db.query(PasswordEntry).filter(PasswordEntry.block_id == block_id).first() or db.query(User).filter(User.block_id == block_id).first():
        raise HTTPException(status_code=400, detail="Block in use by entries/users")
    db.delete(b)
    db.commit()
