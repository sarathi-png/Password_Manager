from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..crypto import decrypt, encrypt
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import AuditLog, PasswordEntry, User
from ..schemas import EntryIn, EntryOut, EntrySummary

router = APIRouter(prefix="/api/entries", tags=["entries"])


def _to_out(e: PasswordEntry) -> EntryOut:
    return EntryOut(
        id=e.id,
        title=e.title,
        url=e.url,
        username=decrypt(e.username_cipher),
        password=decrypt(e.password_cipher),
        notes=decrypt(e.notes_cipher),
        category=e.category,
        created_at=e.created_at,
        updated_at=e.updated_at,
    )


def _log(db: Session, user: User, action: str, target: str, detail: str = "") -> None:
    db.add(AuditLog(user_id=user.id, action=action, target=target, detail=detail))


@router.get("", response_model=list[EntrySummary])
def list_entries(
    q: str = Query(default="", max_length=255),
    category: str = Query(default=""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(PasswordEntry)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(PasswordEntry.title.ilike(like), PasswordEntry.url.ilike(like)))
    if category:
        query = query.filter(PasswordEntry.category == category)
    return query.order_by(PasswordEntry.title).limit(10000).all()


@router.get("/{entry_id}", response_model=EntryOut)
def get_entry(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = db.get(PasswordEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return _to_out(entry)


@router.post("", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def create_entry(body: EntryIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    entry = PasswordEntry(
        title=body.title,
        url=body.url,
        username_cipher=encrypt(body.username),
        password_cipher=encrypt(body.password),
        notes_cipher=encrypt(body.notes),
        category=body.category,
        owner_id=admin.id,
    )
    db.add(entry)
    db.flush()
    _log(db, admin, "entry.create", entry.title)
    db.commit()
    db.refresh(entry)
    return _to_out(entry)


@router.put("/{entry_id}", response_model=EntryOut)
def update_entry(
    entry_id: int,
    body: EntryIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    entry = db.get(PasswordEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    entry.title = body.title
    entry.url = body.url
    entry.username_cipher = encrypt(body.username)
    entry.password_cipher = encrypt(body.password)
    entry.notes_cipher = encrypt(body.notes)
    entry.category = body.category
    _log(db, admin, "entry.update", entry.title)
    db.commit()
    db.refresh(entry)
    return _to_out(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    entry = db.get(PasswordEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    _log(db, admin, "entry.delete", entry.title)
    db.delete(entry)
    db.commit()