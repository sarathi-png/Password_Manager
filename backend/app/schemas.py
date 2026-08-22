from pydantic import BaseModel, ConfigDict, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    is_active: bool
    created_at: object


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=256)
    role: str = Field(default="employee", pattern=r"^(admin|employee)$")


class UserUpdate(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=256)
    role: str | None = Field(default=None, pattern=r"^(admin|employee)$")
    is_active: bool | None = None


class EntryIn(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    url: str = Field(default="", max_length=1024)
    username: str = Field(default="", max_length=512)
    password: str = Field(min_length=1, max_length=2048)
    notes: str = Field(default="", max_length=4096)
    category: str = Field(default="other", max_length=32)


class EntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    url: str
    username: str
    password: str
    notes: str
    category: str
    created_at: object
    updated_at: object


class EntrySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    url: str
    category: str
    updated_at: object


class ImportPreviewRow(BaseModel):
    title: str
    url: str
    username: str
    password: str
    notes: str
    category: str = "other"


class ImportPreview(BaseModel):
    detected_format: str
    total_rows: int
    sample: list[ImportPreviewRow]
    mapping: dict[str, str]


class ImportConfirm(BaseModel):
    mapping: dict[str, str] = Field(
        default_factory=lambda: {"title": "title", "url": "url", "username": "username", "password": "password", "notes": "notes"}
    )
    skip_duplicates: bool = True


class ImportResult(BaseModel):
    imported: int
    skipped_duplicates: int
    failed: int


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: object
    user_id: int | None
    action: str
    target: str
    detail: str
    ip: str