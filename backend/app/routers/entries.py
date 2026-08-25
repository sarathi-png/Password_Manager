from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session
from collections import defaultdict
from typing import Literal

from ..crypto import decrypt, encrypt, build_search_vector
from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import AuditLog, Block, Category, District, PasswordEntry, User, UserCategoryOverride, UserEntryMeta, UserEntryTag
from ..schemas import EntryIn, EntryOut, EntrySummary, UserCategoryIn, UserMetaIn, UserTagIn
from ..services.smart_categorizer import display_name_for_domain, extract_host, registrable_domain, host_group_key_for

router = APIRouter(prefix="/api/entries", tags=["entries"])


def _scope_filter(query, user: User):
    if user.role == "admin":
        return query
    if user.block_id is not None:
        return query.filter(
            or_(
                PasswordEntry.block_id == user.block_id,
                and_(PasswordEntry.district_id.is_(None), PasswordEntry.block_id.is_(None)),
            )
        )
    if user.district_id is not None:
        return query.filter(
            or_(
                PasswordEntry.district_id == user.district_id,
                and_(PasswordEntry.district_id.is_(None), PasswordEntry.block_id.is_(None)),
            )
        )
    return query


def _effective_category(e: PasswordEntry, user: User, db: Session):
    # user private override takes precedence
    ov = db.query(UserCategoryOverride).filter(UserCategoryOverride.user_id == user.id, UserCategoryOverride.entry_id == e.id).first()
    if ov and ov.category_id:
        cat = db.get(Category, ov.category_id)
        if cat:
            # check subcategory
            sub = db.get(Category, ov.subcategory_id) if ov.subcategory_id else None
            return (cat.name, sub.name if sub else None)
    if e.smart_category_id:
        cat = db.get(Category, e.smart_category_id)
        if cat:
            sub = db.get(Category, e.smart_subcategory_id) if e.smart_subcategory_id else None
            return (cat.name, sub.name if sub else None)
    return (e.category, None)


def _enrich_entries(entries: list[PasswordEntry], user: User, db: Session):
    if not entries:
        return {}, {}, {}, {}, {}
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
    # effective category cache
    cat_map: dict[int, tuple[str, str | None]] = {}
    ov_rows = db.query(UserCategoryOverride).filter(UserCategoryOverride.user_id == user.id, UserCategoryOverride.entry_id.in_(e_ids)).all()
    ov_map = {r.entry_id: r for r in ov_rows}
    # smart category names
    sc_ids = {e.smart_category_id for e in entries if e.smart_category_id}
    sc_ids |= {e.smart_subcategory_id for e in entries if e.smart_subcategory_id}
    sc_map = {c.id: c.name for c in db.query(Category).filter(Category.id.in_(sc_ids)).all()} if sc_ids else {}
    for e in entries:
        ov = ov_map.get(e.id)
        if ov and ov.category_id:
            cat_name = sc_map.get(ov.category_id) or db.get(Category, ov.category_id).name if db.get(Category, ov.category_id) else e.category
            sub_name = sc_map.get(ov.subcategory_id) if ov.subcategory_id else None
            cat_map[e.id] = (cat_name, sub_name)
        elif e.smart_category_id:
            cat_name = sc_map.get(e.smart_category_id, e.category)
            sub_name = sc_map.get(e.smart_subcategory_id) if e.smart_subcategory_id else None
            cat_map[e.id] = (cat_name, sub_name)
        else:
            cat_map[e.id] = (e.category, None)
    return d_map, b_map, tag_map, meta_map, cat_map


def _to_summary(e: PasswordEntry, d_map, b_map, tag_map, meta_map, cat_map) -> EntrySummary:
    meta = meta_map.get(e.id)
    eff_cat, eff_sub = cat_map.get(e.id, (e.category, None))
    return EntrySummary(
        id=e.id,
        title=e.title,
        url=e.url,
        username=decrypt(e.username_cipher) if e.username_cipher else "",
        category=e.category,
        host=e.host or "",
        registrable_domain=e.registrable_domain or "",
        smart_category_name=eff_cat,
        smart_subcategory_name=eff_sub,
        effective_category=eff_cat,
        effective_subcategory=eff_sub,
        district_id=e.district_id,
        block_id=e.block_id,
        district_name=d_map.get(e.district_id) if e.district_id else None,
        block_name=b_map.get(e.block_id) if e.block_id else None,
        is_duplicate=e.is_duplicate,
        profile_id=e.profile_id,
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
    eff_cat, eff_sub = _effective_category(e, user, db)
    sc_name = db.get(Category, e.smart_category_id).name if e.smart_category_id else None
    ssc_name = db.get(Category, e.smart_subcategory_id).name if e.smart_subcategory_id else None
    return EntryOut(
        id=e.id,
        title=e.title,
        url=e.url,
        username=decrypt(e.username_cipher),
        password=decrypt(e.password_cipher),
        notes=decrypt(e.notes_cipher),
        category=e.category,
        host=e.host or "",
        exact_host=e.exact_host or "",
        registrable_domain=e.registrable_domain or "",
        smart_category_id=e.smart_category_id,
        smart_subcategory_id=e.smart_subcategory_id,
        smart_category_name=sc_name,
        smart_subcategory_name=ssc_name,
        effective_category=eff_cat,
        effective_subcategory=eff_sub,
        district_id=e.district_id,
        block_id=e.block_id,
        district_name=d_name,
        block_name=b_name,
        is_duplicate=e.is_duplicate,
        profile_id=e.profile_id,
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
    host: str | None = None,
    registrable_domain: str | None = None,
    sort: str = Query(default="title", pattern=r"^(title|updated|recent|favorite)$"),
    search_mode: Literal["basic", "smart"] = Query(default="basic"),
    include_password: bool = Query(default=False),
    profile_id: int | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(PasswordEntry)
    query = _scope_filter(query, user)
    if profile_id is not None:
        query = query.filter(PasswordEntry.profile_id == profile_id)
    if q:
        if search_mode == "smart":
            # Use PostgreSQL full-text search
            # Determine if we should include password based on user setting
            user_include_password = include_password or user.search_include_password
            # websearch_to_tsquery supports natural language queries with operators
            tsquery = func.websearch_to_tsquery('english', q)
            query = query.filter(PasswordEntry.search_vector.op('@@')(tsquery))
        else:
            like = f"%{q}%"
            query = query.filter(or_(PasswordEntry.title.ilike(like), PasswordEntry.url.ilike(like), PasswordEntry.host.ilike(like), PasswordEntry.registrable_domain.ilike(like)))
    if category:
        # Check legacy category, smart category (via Category table), and user override
        smart_cat_ids = db.query(PasswordEntry.id).join(Category, PasswordEntry.smart_category_id == Category.id).filter(Category.name == category)
        override_cat_ids = db.query(UserCategoryOverride.entry_id).join(Category, UserCategoryOverride.category_id == Category.id).filter(
            UserCategoryOverride.user_id == user.id, Category.name == category
        )
        query = query.filter(or_(
            PasswordEntry.category == category,
            PasswordEntry.id.in_(smart_cat_ids),
            PasswordEntry.id.in_(override_cat_ids),
        ))
    if district_id is not None:
        query = query.filter(PasswordEntry.district_id == district_id)
    if block_id is not None:
        query = query.filter(PasswordEntry.block_id == block_id)
    if is_duplicate is not None:
        query = query.filter(PasswordEntry.is_duplicate == is_duplicate)
    if host:
        query = query.filter(PasswordEntry.host.ilike(f"%{host}%"))
    if registrable_domain:
        query = query.filter(PasswordEntry.registrable_domain == registrable_domain)
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
        entries = query.limit(10000).all()
        d_map, b_map, tag_map, meta_map, cat_map = _enrich_entries(entries, user, db)
        def _key(e):
            m = meta_map.get(e.id)
            return (0 if m and m.is_pinned else 1, 0 if m and m.is_favorite else 1, e.title.lower())
        entries.sort(key=_key)
        return [_to_summary(e, d_map, b_map, tag_map, meta_map, cat_map) for e in entries]
    else:
        query = query.order_by(PasswordEntry.title)

    entries = query.limit(10000).all()
    d_map, b_map, tag_map, meta_map, cat_map = _enrich_entries(entries, user, db)
    return [_to_summary(e, d_map, b_map, tag_map, meta_map, cat_map) for e in entries]


@router.get("/groups", response_model=list[dict])
def list_groups(
    q: str = Query(default=""),
    district_id: int | None = None,
    block_id: int | None = None,
    search_mode: Literal["basic", "smart"] = Query(default="basic"),
    profile_id: int | None = None,
    category: str = Query(default=""),
    is_duplicate: bool | None = None,
    tag: str | None = None,
    is_favorite: bool | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # collapsed by registrable_domain, respects scope and effective category
    query = db.query(PasswordEntry)
    query = _scope_filter(query, user)
    if profile_id is not None:
        query = query.filter(PasswordEntry.profile_id == profile_id)
    if q:
        if search_mode == "smart":
            tsquery = func.websearch_to_tsquery('english', q)
            query = query.filter(PasswordEntry.search_vector.op('@@')(tsquery))
        else:
            like = f"%{q}%"
            query = query.filter(or_(PasswordEntry.title.ilike(like), PasswordEntry.url.ilike(like), PasswordEntry.host.ilike(like), PasswordEntry.registrable_domain.ilike(like)))
    if category:
        smart_cat_ids = db.query(PasswordEntry.id).join(Category, PasswordEntry.smart_category_id == Category.id).filter(Category.name == category)
        override_cat_ids = db.query(UserCategoryOverride.entry_id).join(Category, UserCategoryOverride.category_id == Category.id).filter(
            UserCategoryOverride.user_id == user.id, Category.name == category
        )
        query = query.filter(or_(
            PasswordEntry.category == category,
            PasswordEntry.id.in_(smart_cat_ids),
            PasswordEntry.id.in_(override_cat_ids),
        ))
    if district_id is not None:
        query = query.filter(PasswordEntry.district_id == district_id)
    if block_id is not None:
        query = query.filter(PasswordEntry.block_id == block_id)
    if is_duplicate is not None:
        query = query.filter(PasswordEntry.is_duplicate == is_duplicate)
    if tag:
        sub = db.query(UserEntryTag.entry_id).filter(UserEntryTag.user_id == user.id, UserEntryTag.tag == tag).subquery()
        query = query.filter(PasswordEntry.id.in_(sub))
    if is_favorite is not None:
        sub = db.query(UserEntryMeta.entry_id).filter(UserEntryMeta.user_id == user.id, UserEntryMeta.is_favorite == is_favorite).subquery()
        query = query.filter(PasswordEntry.id.in_(sub)) if is_favorite else query.filter(~PasswordEntry.id.in_(sub))
    entries = query.limit(10000).all()
    # group
    groups: dict[str, dict] = {}
    # need effective categories for groups: use first entry's effective, or most common
    for e in entries:
        key = e.registrable_domain or e.host or "no-host"
        if not key:
            key = "other"
        g = groups.setdefault(key, {"registrable_domain": key, "count": 0, "exact_hosts": set(), "sample_titles": [], "smart_category": None, "entries": []})
        g["count"] += 1
        g["exact_hosts"].add(e.exact_host or e.host)
        if len(g["sample_titles"]) < 2:
            g["sample_titles"].append(e.title)
        # keep first smart category as group's category
        if not g["smart_category"] and e.smart_category_id:
            cat = db.get(Category, e.smart_category_id)
            g["smart_category"] = cat.name if cat else None
        g["entries"].append(e.id)
    out = []
    for key, g in groups.items():
        eff_cat = g["smart_category"] or "Other"
        # if no smart, fallback to most common category in group
        if not g["smart_category"]:
            # count categories in group
            cnt = defaultdict(int)
            for eid in g["entries"]:
                ent = next((x for x in entries if x.id == eid), None)
                if ent:
                    cat,_ = _effective_category(ent, user, db)
                    cnt[cat] += 1
            if cnt:
                eff_cat = max(cnt, key=cnt.get)
        out.append({
            "registrable_domain": key,
            "display_name": display_name_for_domain(key),
            "exact_hosts": sorted(g["exact_hosts"]),
            "count": g["count"],
            "sample_titles": g["sample_titles"],
            "effective_category": eff_cat,
            "entry_ids": g["entries"][:50],
        })
    out.sort(key=lambda x: x["count"], reverse=True)
    return out


@router.get("/{entry_id}", response_model=EntryOut)
def get_entry(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = db.get(PasswordEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    scoped_q = _scope_filter(db.query(PasswordEntry).filter(PasswordEntry.id == entry_id), user)
    if scoped_q.first() is None and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not in your district/block scope")
    return _to_out(entry, db, user)


@router.post("", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def create_entry(body: EntryIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if body.district_id is not None and db.get(District, body.district_id) is None:
        raise HTTPException(status_code=400, detail="District not found")
    if body.block_id is not None and db.get(Block, body.block_id) is None:
        raise HTTPException(status_code=400, detail="Block not found")
    if body.smart_category_id is not None and db.get(Category, body.smart_category_id) is None:
        raise HTTPException(status_code=400, detail="Category not found")
    if body.smart_subcategory_id is not None and db.get(Category, body.smart_subcategory_id) is None:
        raise HTTPException(status_code=400, detail="Subcategory not found")
    h = extract_host(body.url)
    reg = registrable_domain(h)
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
        host=h[:255],
        exact_host=h[:255],
        registrable_domain=reg[:255],
        host_group_key=(reg or h)[:255],
        smart_category_id=body.smart_category_id,
        smart_subcategory_id=body.smart_subcategory_id,
        profile_id=body.profile_id,
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
    if body.smart_category_id is not None and db.get(Category, body.smart_category_id) is None:
        raise HTTPException(status_code=400, detail="Category not found")
    if body.smart_subcategory_id is not None and db.get(Category, body.smart_subcategory_id) is None:
        raise HTTPException(status_code=400, detail="Subcategory not found")
    entry.title = body.title
    entry.url = body.url
    entry.username_cipher = encrypt(body.username)
    entry.password_cipher = encrypt(body.password)
    entry.notes_cipher = encrypt(body.notes)
    entry.category = body.category
    entry.district_id = body.district_id
    entry.block_id = body.block_id
    h = extract_host(body.url)
    reg = registrable_domain(h)
    entry.host = h[:255]
    entry.exact_host = h[:255]
    entry.registrable_domain = reg[:255]
    entry.host_group_key = (reg or h)[:255]
    entry.smart_category_id = body.smart_category_id
    entry.smart_subcategory_id = body.smart_subcategory_id
    entry.profile_id = body.profile_id
    _log(db, admin, "entry.update", entry.title)
    db.commit()
    db.refresh(entry)
    return _to_out(entry, db, admin)


@router.post("/bulk-assign", response_model=dict)
def bulk_assign(
    entry_ids: list[int],
    district_id: int | None = None,
    block_id: int | None = None,
    category_id: int | None = None,
    subcategory_id: int | None = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if district_id is not None and db.get(District, district_id) is None:
        raise HTTPException(status_code=400, detail="District not found")
    if block_id is not None and db.get(Block, block_id) is None:
        raise HTTPException(status_code=400, detail="Block not found")
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(status_code=400, detail="Category not found")
    if subcategory_id is not None and db.get(Category, subcategory_id) is None:
        raise HTTPException(status_code=400, detail="Subcategory not found")
    q = db.query(PasswordEntry).filter(PasswordEntry.id.in_(entry_ids))
    updated = 0
    for e in q.all():
        if district_id is not None:
            e.district_id = district_id
        if block_id is not None:
            e.block_id = block_id
        if category_id is not None:
            e.smart_category_id = category_id
        if subcategory_id is not None:
            e.smart_subcategory_id = subcategory_id
        updated += 1
    db.commit()
    _log(db, admin, "entry.bulk_assign", f"{updated} entries", f"district={district_id} block={block_id} cat={category_id}")
    return {"updated": updated}


@router.put("/{entry_id}/category", response_model=dict)
def set_global_category(
    entry_id: int,
    body: UserCategoryIn,
    apply_to_group: bool = False,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    entry = db.get(PasswordEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if body.category_id and not db.get(Category, body.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    if body.subcategory_id and not db.get(Category, body.subcategory_id):
        raise HTTPException(status_code=404, detail="Subcategory not found")
    targets = [entry]
    group_key = entry.host_group_key or entry.registrable_domain
    if apply_to_group and group_key:
        targets = db.query(PasswordEntry).filter(
            (PasswordEntry.host_group_key == group_key) | (PasswordEntry.registrable_domain == group_key)
        ).all()
    for e in targets:
        e.smart_category_id = body.category_id
        e.smart_subcategory_id = body.subcategory_id
    _log(db, admin, "entry.category.global", entry.title, f"cat={body.category_id} sub={body.subcategory_id} group={apply_to_group} n={len(targets)}")
    db.commit()
    return {"updated": len(targets), "entry": _to_out(entry, db, admin)}


@router.put("/{entry_id}/my-category", response_model=dict)
def set_my_category(entry_id: int, body: UserCategoryIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    entry = db.get(PasswordEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    if _scope_filter(db.query(PasswordEntry).filter(PasswordEntry.id == entry_id), user).first() is None and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not in scope")
    if body.category_id and not db.get(Category, body.category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    if body.subcategory_id and not db.get(Category, body.subcategory_id):
        raise HTTPException(status_code=404, detail="Subcategory not found")
    ov = db.query(UserCategoryOverride).filter(UserCategoryOverride.user_id == user.id, UserCategoryOverride.entry_id == entry_id).first()
    if not ov:
        ov = UserCategoryOverride(user_id=user.id, entry_id=entry_id, category_id=body.category_id, subcategory_id=body.subcategory_id)
        db.add(ov)
    else:
        ov.category_id = body.category_id
        ov.subcategory_id = body.subcategory_id
    db.commit()
    # return effective
    eff_cat, eff_sub = _effective_category(entry, user, db)
    return {"effective_category": eff_cat, "effective_subcategory": eff_sub}


# ---- Private per-user tags & pins ----

@router.get("/{entry_id}/tags", response_model=list[str])
def list_tags(entry_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(PasswordEntry, entry_id) is None:
        raise HTTPException(status_code=404, detail="Entry not found")
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
