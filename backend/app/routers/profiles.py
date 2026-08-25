from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import AuditLog, PasswordEntry, Profile, User, UserProfile
from ..schemas import (
    ProfileCreate,
    ProfileOut,
    ProfileOutWithPin,
    ProfileSelectRequest,
    ProfileUpdate,
    UserProfileCreate,
    UserProfileSetPin,
)
from ..security import hash_password, verify_password

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


AVATARS = [
    "https://api.dicebear.com/7.x/avataaars/svg?seed=cat",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=dog",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=bunny",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=panda",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=fox",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=owl",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=penguin",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=robot",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=alien",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=unicorn",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=dragon",
    "https://api.dicebear.com/7.x/avataaars/svg?seed=ghost",
]


@router.get("/avatars")
def list_avatars():
    return {"avatars": AVATARS}


@router.get("", response_model=list[ProfileOutWithPin])
def list_profiles(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List profiles the current user has access to."""
    user_profiles = (
        db.query(UserProfile, Profile)
        .join(Profile, UserProfile.profile_id == Profile.id)
        .filter(UserProfile.user_id == user.id)
        .all()
    )
    result = []
    for up, profile in user_profiles:
        out = ProfileOutWithPin.model_validate(profile)
        out.has_pin = up.pin_hash is not None
        out.user_count = db.query(UserProfile).filter(UserProfile.profile_id == profile.id).count()
        result.append(out)
    return result


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(body: ProfileCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new profile and auto-assign the creator."""
    profile = Profile(
        name=body.name,
        avatar_url=body.avatar_url or AVATARS[0],
        created_by_id=user.id,
    )
    db.add(profile)
    db.flush()
    # auto-assign creator
    db.add(UserProfile(user_id=user.id, profile_id=profile.id))
    db.add(AuditLog(user_id=user.id, action="profile.create", target=profile.name, detail=f"profile_id={profile.id}"))
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    # must have access
    up = db.query(UserProfile).filter(UserProfile.user_id == user.id, UserProfile.profile_id == profile_id).first()
    if not up:
        raise HTTPException(status_code=403, detail="No access to this profile")
    out = ProfileOut.model_validate(profile)
    out.user_count = db.query(UserProfile).filter(UserProfile.profile_id == profile_id).count()
    out.entry_count = db.query(PasswordEntry).filter(PasswordEntry.profile_id == profile_id).count()
    return out


@router.put("/{profile_id}", response_model=ProfileOut)
def update_profile(profile_id: int, body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    up = db.query(UserProfile).filter(UserProfile.user_id == user.id, UserProfile.profile_id == profile_id).first()
    if not up:
        raise HTTPException(status_code=403, detail="No access to this profile")
    if body.name is not None:
        profile.name = body.name
    if body.avatar_url is not None:
        profile.avatar_url = body.avatar_url
    db.add(AuditLog(user_id=user.id, action="profile.update", target=profile.name, detail=f"profile_id={profile_id}"))
    db.commit()
    db.refresh(profile)
    out = ProfileOut.model_validate(profile)
    out.user_count = db.query(UserProfile).filter(UserProfile.profile_id == profile_id).count()
    return out


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    # block if entries exist
    entry_count = db.query(PasswordEntry).filter(PasswordEntry.profile_id == profile_id).count()
    if entry_count > 0:
        raise HTTPException(status_code=409, detail=f"Cannot delete profile with {entry_count} entries. Move or delete them first.")
    db.add(AuditLog(user_id=user.id, action="profile.delete", target=profile.name, detail=f"profile_id={profile_id}"))
    db.delete(profile)
    db.commit()


@router.post("/{profile_id}/users", status_code=status.HTTP_201_CREATED)
def add_user_to_profile(profile_id: int, body: UserProfileCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Assign a user to a profile."""
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    target_user = db.get(User, body.user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(UserProfile).filter(UserProfile.user_id == body.user_id, UserProfile.profile_id == profile_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already in this profile")
    db.add(UserProfile(user_id=body.user_id, profile_id=profile_id))
    db.add(AuditLog(user_id=user.id, action="profile.user.add", target=profile.name, detail=f"added user_id={body.user_id}"))
    db.commit()
    return {"ok": True}


@router.delete("/{profile_id}/users/{target_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user_from_profile(profile_id: int, target_user_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove a user from a profile."""
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    up = db.query(UserProfile).filter(UserProfile.user_id == target_user_id, UserProfile.profile_id == profile_id).first()
    if not up:
        raise HTTPException(status_code=404, detail="User not in this profile")
    db.add(AuditLog(user_id=user.id, action="profile.user.remove", target=profile.name, detail=f"removed user_id={target_user_id}"))
    db.delete(up)
    db.commit()


@router.post("/{profile_id}/pin", status_code=status.HTTP_200_OK)
def set_profile_pin(profile_id: int, body: UserProfileSetPin, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Set or change the current user's PIN for a profile."""
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    up = db.query(UserProfile).filter(UserProfile.user_id == user.id, UserProfile.profile_id == profile_id).first()
    if not up:
        raise HTTPException(status_code=403, detail="No access to this profile")
    up.pin_hash = hash_password(body.pin)
    db.commit()
    return {"ok": True}


@router.delete("/{profile_id}/pin", status_code=status.HTTP_200_OK)
def remove_profile_pin(profile_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Remove the current user's PIN for a profile."""
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    up = db.query(UserProfile).filter(UserProfile.user_id == user.id, UserProfile.profile_id == profile_id).first()
    if not up:
        raise HTTPException(status_code=403, detail="No access to this profile")
    up.pin_hash = None
    db.commit()
    return {"ok": True}


@router.post("/{profile_id}/select")
def select_profile(profile_id: int, body: ProfileSelectRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Select a profile. If PIN is set, verify it. Returns profile info for entry scoping."""
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    up = db.query(UserProfile).filter(UserProfile.user_id == user.id, UserProfile.profile_id == profile_id).first()
    if not up:
        raise HTTPException(status_code=403, detail="No access to this profile")
    # verify PIN if set
    if up.pin_hash is not None:
        if body.pin is None:
            raise HTTPException(status_code=401, detail="PIN required")
        if not verify_password(body.pin, up.pin_hash):
            raise HTTPException(status_code=401, detail="Invalid PIN")
    return {
        "profile_id": profile.id,
        "name": profile.name,
        "avatar_url": profile.avatar_url,
    }
