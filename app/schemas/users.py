from pydantic import BaseModel, Field, field_validator

USER_ID_PATTERN = r"^[A-Za-z0-9._-]{1,64}$"


class RegisterRequest(BaseModel):
    user_id: str = Field(pattern=USER_ID_PATTERN)
    name: str = Field(min_length=1, max_length=100)
    consent: bool
    frames: list[str] = Field(min_length=1, max_length=20, description="Gambar JPEG/PNG base64")

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Nama tidak boleh kosong")
        return v


class UserOut(BaseModel):
    user_id: str
    name: str
    template_count: int
    created_at: str
    consent_at: str


class UserListOut(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class FrameReport(BaseModel):
    index: int
    accepted: bool
    reasons: list[str]
    messages: list[str]


class RegisterResponse(BaseModel):
    user: UserOut
    accepted_samples: int
    reports: list[FrameReport]


class DeleteResponse(BaseModel):
    user_id: str
    deleted_templates: int
