from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin, get_current_user
from ..models import Category, User
from ..schemas import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/api/categories", tags=["categories"])


def _to_tree(cats: list[Category]) -> list[CategoryOut]:
    # build tree via parent_id
    mp = {c.id: CategoryOut.model_validate(c) for c in cats}
    roots = []
    for c in cats:
        if c.parent_id and c.parent_id in mp:
            mp[c.parent_id].children.append(mp[c.id])
        else:
            roots.append(mp[c.id])
    return roots


def _entry_counts(db: Session) -> dict[int, int]:
    from ..models import PasswordEntry
    counts: dict[int, int] = {}
    rows = db.query(PasswordEntry.smart_category_id, PasswordEntry.smart_subcategory_id).all()
    for cat_id, sub_id in rows:
        if cat_id:
            counts[cat_id] = counts.get(cat_id, 0) + 1
        if sub_id:
            counts[sub_id] = counts.get(sub_id, 0) + 1
    return counts


def _fill_counts(nodes: list[CategoryOut], counts: dict[int, int]) -> None:
    for n in nodes:
        n.entry_count = counts.get(n.id, 0)
        _fill_counts(n.children, counts)


@router.get("", response_model=list[CategoryOut])
def list_categories(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cats = db.query(Category).order_by(Category.name).all()
    tree = _to_tree(cats)
    _fill_counts(tree, _entry_counts(db))
    return tree


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if body.parent_id and not db.get(Category, body.parent_id):
        raise HTTPException(status_code=404, detail="Parent not found")
    # unique per parent
    q = db.query(Category).filter(Category.name == body.name.strip(), Category.parent_id == body.parent_id).first()
    if q:
        raise HTTPException(status_code=409, detail="Category already exists under this parent")
    cat = Category(name=body.name.strip(), slug=body.name.strip().lower().replace(" ", "-"), parent_id=body.parent_id, is_system=False)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return CategoryOut.model_validate(cat)


@router.put("/{cat_id}", response_model=CategoryOut)
def rename_category(cat_id: int, body: CategoryUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    cat = db.get(Category, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Not found")
    name = body.name.strip()
    q = db.query(Category).filter(Category.name == name, Category.parent_id == cat.parent_id, Category.id != cat_id).first()
    if q:
        raise HTTPException(status_code=409, detail="Category already exists under this parent")
    cat.name = name
    cat.slug = name.lower().replace(" ", "-")
    db.commit()
    db.refresh(cat)
    return CategoryOut.model_validate(cat)


@router.delete("/{cat_id}", status_code=204)
def delete_category(cat_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    cat = db.get(Category, cat_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Not found")
    if cat.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system category")
    if db.query(Category).filter(Category.parent_id == cat_id).first():
        raise HTTPException(status_code=400, detail="Category has subcategories")
    # check if in use
    from ..models import PasswordEntry, UserCategoryOverride
    if db.query(PasswordEntry).filter((PasswordEntry.smart_category_id == cat_id) | (PasswordEntry.smart_subcategory_id == cat_id)).first():
        raise HTTPException(status_code=400, detail="Category in use by entries")
    if db.query(UserCategoryOverride).filter((UserCategoryOverride.category_id == cat_id) | (UserCategoryOverride.subcategory_id == cat_id)).first():
        raise HTTPException(status_code=400, detail="Category in use by user overrides")
    db.delete(cat)
    db.commit()
