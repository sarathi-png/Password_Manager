from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..crypto import decrypt, encrypt
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import AuditLog, Block, District, PasswordEntry, User, UserEntryMeta, UserEntryTag
from ..schemas import EntryIn, EntryOut, EntrySummary, UserMetaIn, UserTagIn

router = APIRouter(prefix="/api/entries", tags=["entries"])


def _scope_filter(query, user: User):
    """Row-level scope: district sees district+blocks (any entry with district_id == user.district_id or legacy null+block null);
       block sees only its block (plus legacy unassigned for backward compat); admin sees all."""
    if user.role == "admin":
        return query
    # Block employee: only its block
    if user.block_id is not None:
        # include legacy unassigned so existing data not hidden before admin assigns
        return query.filter(
            or_(
                PasswordEntry.block_id == user.block_id,
                and_(PasswordEntry.district_id.is_(None), PasswordEntry.block_id.is_(None)),
            )
        )
    # District employee: any entry in their district (any block within district) + legacy
    if user.district_id is not None:
        return query.filter(
            or_(
                PasswordEntry.district_id == user.district_id,
                and_(PasswordEntry.district_id.is_(None), PasswordEntry.block_id.is_(None)),
            )
        )
    # No scope assigned → see all (backward compat)
    return query


def _enrich_entries(entries: list[PasswordEntry], user: User, db: Session):
    """Bulk load district/block names + private tags/meta for current user."""
    if not entries:
        return [], {}, {}
    # district/block name maps
    d_ids = {e.district_id for e in entries if e.district_id}
    b_ids = {e.block_id for e in entries if e.block_id}
    d_map = {d.id: d.name for d in db.query(District).filter(District.id.in_(d_ids)).all()} if d_ids else {}
    b_map = {b.id: b.name for b in db.query(Block).filter(Block.id.in_(b_ids)).all()} if b_ids else {}
    e_ids = [e.id for e in entries]
    tags_rows = db.query(UserEntryTag).filter(UserEntryTag.user_id == user.id, UserEntryTag.entry_id.in_(e_ids)).all()
    tag_map: dict[int, list[str]] = {}
    for r in tags_rows:
        tag_map.setdefault(r.entry_id, []).append(r.tag)
    meta_rows = db.query(UserEntryMeta).filter(UserEntryMeta.user_id == user.id, UserEntryMeta.entry_id.in_(e_ids)).all()
    meta_map: dict[int, UserEntryMeta] = {r.entry_id: r for r in meta_rows}
    return d_map, b_map, tag_map, meta_map


def _to_summary(e: PasswordEntry, d_map, b_map, tag_map, meta_map) -> EntrySummary:
    meta = meta_map.get(e.id)
    return EntrySummary(
        id=e.id,
        title=e.title,
        url=e.url,
        category=e.category,
        district_id=e.district_id,
        block_id=e.block_id,
        district_name=d_map.get(e.district_id) if e.district_id else None,
        block_name=b_map.get(e.block_id) if e.block_id else None,
        is_duplicate=e.is_duplicate,
        tags=tag_map.get(e.id, []),
        is_favorite=meta.is_favorite if meta else False,
        is_pinned=meta.is_pinned if meta else False,
        updated_at=e.updated_at,
    )


def _to_out(e: PasswordEntry, db: Session, user: User) -> EntryOut:
    d_name = db.get(District, e.district_id).name if e.district_id else None
    b_name = db.get(Block, e.block_id).name if e.block_id else None
    tags = [r.tag for r in db.query(UserEntryTag).filter(UserEntryTag.user_id == user.id, UserEntryTag.entry_id == e.id).all()]
    meta = db.query(UserEntryMeta).filter(UserEntryMeta.user_id == user.id, UserEntryMeta.entry_id == e.id).first()
    return EntryOut(
        id=e.id,
        title=e.title,
        url=e.url,
        username=decrypt(e.username_cipher),
        password=decrypt(e.password_cipher),
        notes=decrypt(e.notes_cipher),
        category=e.category,
        district_id=e.district_id,
        block_id=e.block_id,
        district_name=d_name,
        block_name=b_name,
        is_duplicate=e.is_duplicate,
        created_at=e.created_at,
        updated_at=e.updated_at,
        tags=tags,
        is_favorite=meta.is_favorite if meta else False,
        is_pinned=meta.is_pinned if meta else False,
    )


def _log(db: Session, user: User, action: str, target: str, detail: str = "") -> None:
    db.add(AuditLog(user_id=user.id, action=action, target=target, detail=detail))


@router.get("", response_model=list[EntrySummary])
def list_entries(
    q: str = Query(default="", max_length=255),
    category: str = Query(default=""),
    district_id: int | None = None,
    block_id: int | None = None,
    is_duplicate: bool | None = None,
    tag: str | None = None,
    is_favorite: bool | None = None,
    is_pinned: bool | None = None,
    sort: str = Query(default="title", pattern=r"^(title|updated|recent|favorite)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(PasswordEntry)
    # scope
    query = _scope_filter(query, user)
    if q:
        like = f"%{q}%"
        query = query.filter(or_(PasswordEntry.title.ilike(like), PasswordEntry.url.ilike(like)))
    if category:
        query = query.filter(PasswordEntry.category == category)
    if district_id is not None:
        query = query.filter(PasswordEntry.district_id == district_id)
    if block_id is not None:
        query = query.filter(PasswordEntry.block_id == block_id)
    if is_duplicate is not None:
        query = query.filter(PasswordEntry.is_duplicate == is_duplicate)
    # tag / favorite/pinned are per-user; filter via subquery
    if tag:
        sub = db.query(UserEntryTag.entry_id).filter(UserEntryTag.user_id == user.id, UserEntryTag.tag == tag).subquery()
        query = query.filter(PasswordEntry.id.in_(sub))
    if is_favorite is not None:
        sub = db.query(UserEntryMeta.entry_id).filter(UserEntryMeta.user_id == user.id, UserEntryMeta.is_favorite == is_favorite).subquery()
        query = query.filter(PasswordEntry.id.in_(sub)) if is_favorite else query.filter(~PasswordEntry.id.in_(sub))
    if is_pinned is not None:
        sub = db.query(UserEntryMeta.entry_id).filter(UserEntryMeta.user_id == user.id, UserEntryMeta.is_pinned == is_pinned).subquery()
        query = query.filter(PasswordEntry.id.in_(sub)) if is_pinned else query.filter(~PasswordEntry.id.in_(sub))

    if sort == "updated" or sort == "recent":
        query = query.order_by(PasswordEntry.updated_at.desc())
    elif sort == "favorite":
        # pins first, then favorites
        entries = query.limit(10000).all()
        # sort pins/favs to top in python
        d_map, b_map, tag_map, meta_map = _enrich_entries(entries, user, db)
        def _key(e):
            m = meta_map.get(e.id)
            return (0 if m and m.is_pinned else 1, 0 if m and m.is_favorite else 1, e.title.lower())
        entries.sort(key=_key)
        return [_to_summary(e, d_map, b_map, tag_map, meta_map) for e in entries]
    else:
        query = query.order_by(PasswordEntry.title)

    entries = query.limit(10000).all()
    d_map, b_map, tag_map, meta_map = _enrich_entries(entries, user, db)
    return [_to_summary(e, d_map, b_map, tag_map, meta_map) for e in entries]


@router.get("/{entry_id}", response_model=EntryOut)
def get_entry(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = db.get(PasswordEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    # scope check
    scoped_q = _scope_filter(db.query(PasswordEntry).filter(PasswordEntry.id == entry_id), user)
    if scoped_q.first() is None and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not in your district/block scope")
    return _to_out(entry, db, user)


@router.post("", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def create_entry(body: EntryIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    # validate district/block if provided
    if body.district_id is not None and db.get(District, body.district_id) is None:
        raise HTTPException(status_code=400, detail="District not found")
    if body.block_id is not None and db.get(Block, body.block_id) is None:
        raise HTTPException(status_code=400, detail="Block not found")
    entry = PasswordEntry(
        title=body.title,
        url=body.url,
        username_cipher=encrypt(body.username),
        password_cipher=encrypt(body.password),
        notes_cipher=encrypt(body.notes),
        category=body.category,
        owner_id=admin.id,
        district_id=body.district_id,
        block_id=body.block_id,
    )
    db.add(entry)
    db.flush()
    _log(db, admin, "entry.create", entry.title)
    db.commit()
    db.refresh(entry)
    return _to_out(entry, db, admin)


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
    if body.district_id is not None and db.get(District, body.district_id) is None:
        raise HTTPException(status_code=400, detail="District not found")
    if body.block_id is not None and db.get(Block, body.block_id) is None:
        raise HTTPException(status_code=400, detail="Block not found")
    entry.title = body.title
    entry.url = body.url
    entry.username_cipher = encrypt(body.username)
    entry.password_cipher = encrypt(body.password)
    entry.notes_cipher = encrypt(body.notes)
    entry.category = body.category
    entry.district_id = body.district_id
    entry.block_id = body.block_id
    _log(db, admin, "entry.update", entry.title)
    db.commit()
    db.refresh(entry)
    return _to_out(entry, db, admin)


@router.post("/bulk-assign", response_model=dict)
def bulk_assign(
    entry_ids: list[int],
    district_id: int | None = None,
    block_id: int | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if district_id is not None and db.get(District, district_id) is None:
        raise HTTPException(status_code=400, detail="District not found")
    if block_id is not None and db.get(Block, block_id) is None:
        raise HTTPException(status_code=400, detail="Block not found")
    q = db.query(PasswordEntry).filter(PasswordEntry.id.in_(entry_ids))
    updated = 0
    for e in q.all():
        e.district_id = district_id
        e.block_id = block_id
        updated += 1
    db.commit()
    _log(db, admin, "entry.bulk_assign", f"{updated} entries", f"district={district_id} block={block_id}")
    return {"updated": updated}


# ---- Private per-user tags & pins (works for any logged-in user, read-only entries) ----

@router.get("/{entry_id}/tags", response_model=list[str])
def list_tags(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(PasswordEntry, entry_id) is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    # scope check for non-admin
    if _scope_filter(db.query(PasswordEntry).filter(PasswordEntry.id == entry_id), user).first() is None and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not in scope")
    return [r.tag for r in db.query(UserEntryTag).filter(UserEntryTag.user_id == user.id, UserEntryTag.entry_id == entry_id).all()]


@router.post("/{entry_id}/tags", response_model=list[str])
def add_tag(entry_id: int, body: UserTagIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(PasswordEntry, entry_id) is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    if _scope_filter(db.query(PasswordEntry).filter(PasswordEntry.id == entry_id), user).first() is None and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not in scope")
    tag = body.tag.strip()
    exists = db.query(UserEntryTag).filter(UserEntryTag.user_id == user.id, UserEntryTag.entry_id == entry_id, UserEntryTag.tag == tag).first()
    if not exists:
        db.add(UserEntryTag(user_id=user.id, entry_id=entry_id, tag=tag))
        db.commit()
    return [r.tag for r in db.query(UserEntryTag).filter(UserEntryTag.user_id == user.id, UserEntryTag.entry_id == entry_id).all()]


@router.delete("/{entry_id}/tags/{tag}", response_model=list[str])
def remove_tag(entry_id: int, tag: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(UserEntryTag).filter(UserEntryTag.user_id == user.id, UserEntryTag.entry_id == entry_id, UserEntryTag.tag == tag)
    q.delete()
    db.commit()
    return [r.tag for r in db.query(UserEntryTag).filter(UserEntryTag.user_id == user.id, UserEntryTag.entry_id == entry_id).all()]


@router.put("/{entry_id}/meta", response_model=dict)
def update_meta(entry_id: int, body: UserMetaIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(PasswordEntry, entry_id) is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    if _scope_filter(db.query(PasswordEntry).filter(PasswordEntry.id == entry_id), user).first() is None and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not in scope")
    meta = db.query(UserEntryMeta).filter(UserEntryMeta.user_id == user.id, UserEntryMeta.entry_id == entry_id).first()
    if meta is None:
        meta = UserEntryMeta(user_id=user.id, entry_id=entry_id)
        db.add(meta)
    if body.is_favorite is not None:
        meta.is_favorite = body.is_favorite
    if body.is_pinned is not None:
        meta.is_pinned = body.is_pinned
    db.commit()
    return {"is_favorite": meta.is_favorite, "is_pinned": meta.is_pinned}


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    entry = db.get(PasswordEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    _log(db, admin, "entry.delete", entry.title)
    db.delete(entry)
    db.commit()