from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class DistrictOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: object


class DistrictCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class BlockOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    district_id: int
    created_at: object


class BlockCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    district_id: int


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    is_active: bool
    created_at: object
    district_id: int | None = None
    block_id: int | None = None
    district_name: str | None = None
    block_name: str | None = None


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=256)
    role: str = Field(default="employee", pattern=r"^(admin|employee)$")
    district_id: int | None = None
    block_id: int | None = None


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=256)
    role: str | None = Field(default=None, pattern=r"^(admin|employee)$")
    is_active: bool | None = None
    district_id: int | None = None
    block_id: int | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    parent_id: int | None = None
    is_system: bool
    created_at: object
    children: list["CategoryOut"] = Field(default_factory=list)


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    parent_id: int | None = None


class EntryIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    url: str = Field(default="", max_length=1024)
    username: str = Field(default="", max_length=512)
    password: str = Field(min_length=1, max_length=2048)
    notes: str = Field(default="", max_length=4096)
    category: str = Field(default="other", max_length=32)
    district_id: int | None = None
    block_id: int | None = None
    smart_category_id: int | None = None
    smart_subcategory_id: int | None = None


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    url: str
    username: str
    password: str
    notes: str
    category: str
    host: str = ""
    exact_host: str = ""
    registrable_domain: str = ""
    smart_category_id: int | None = None
    smart_subcategory_id: int | None = None
    smart_category_name: str | None = None
    smart_subcategory_name: str | None = None
    effective_category: str = "other"
    effective_subcategory: str | None = None
    district_id: int | None = None
    block_id: int | None = None
    district_name: str | None = None
    block_name: str | None = None
    is_duplicate: bool = False
    created_at: object
    updated_at: object
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool = False
    is_pinned: bool = False


class EntrySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    url: str
    category: str
    host: str = ""
    registrable_domain: str = ""
    smart_category_name: str | None = None
    smart_subcategory_name: str | None = None
    effective_category: str = "other"
    effective_subcategory: str | None = None
    district_id: int | None = None
    block_id: int | None = None
    district_name: str | None = None
    block_name: str | None = None
    is_duplicate: bool = False
    tags: list[str] = Field(default_factory=list)
    is_favorite: bool = False
    is_pinned: bool = False
    updated_at: object


class ImportPreviewRow(BaseModel):
    title: str
    url: str
    username: str
    password: str
    notes: str
    category: str = "other"


class HostGroup(BaseModel):
    registrable_domain: str
    exact_hosts: list[str]
    count: int
    sample_titles: list[str]


class SmartGroup(BaseModel):
    registrable_domain: str
    count: int
    proposed_category: str
    proposed_subcategory: str | None = None
    confidence: float = 0.0
    is_ai: bool = False


class ImportPreview(BaseModel):
    detected_format: str
    total_rows: int
    sample: list[ImportPreviewRow]
    mapping: dict[str, str]
    host_groups: list[HostGroup] = Field(default_factory=list)
    smart_groups: list[SmartGroup] = Field(default_factory=list)


class ImportConfirm(BaseModel):
    mapping: dict[str, str] = Field(
        default_factory=lambda: {"title": "title", "url": "url", "username": "username", "password": "password", "notes": "notes"}
    )
    skip_duplicates: bool = False
    # "exact" = title+url+username+password exact match; "title_url" = old behavior; "none" = import all without dedup
    dedup_mode: str = Field(default="none", pattern=r"^(none|exact|title_url|title_url_username)$")
    district_id: int | None = None
    block_id: int | None = None
    permit_smart: bool = False
    smart_category_id: int | None = None


class ImportResult(BaseModel):
    imported: int
    skipped_duplicates: int
    failed: int
    marked_duplicates: int = 0


class UserTagIn(BaseModel):
    tag: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_\- ]+$")


class UserMetaIn(BaseModel):
    is_favorite: bool | None = None
    is_pinned: bool | None = None


class UserCategoryIn(BaseModel):
    category_id: int | None = None
    subcategory_id: int | None = None


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: object
    user_id: int | None
    action: str
    target: str
    detail: str
    ip: str