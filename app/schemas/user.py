"""
User Schemas - Request/Response models for user profile

Fungsi file ini:
- UserResponse: Format data user yang dikirim ke client (TANPA password!)
- UserUpdate: Validasi data saat user update profile
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserResponse(BaseModel):
    """
    Schema untuk response data user

    Dipakai di:
    - GET /api/v1/users/me (response)
    - POST /api/v1/auth/register (optional, return user data)

    PENTING: Schema ini TIDAK include password!
    Password tidak boleh ter-expose ke client untuk keamanan.

    Field:
    - id: UUID user
    - email: Email user
    - full_name: Nama lengkap
    - avatar_url: URL foto profil (bisa null)
    - risk_profile: Profil risiko investasi (conservative/moderate/aggressive)
    - default_currency: Mata uang default (IDR/USD)
    - is_active: Status akun aktif atau tidak
    - created_at: Kapan akun dibuat
    - updated_at: Kapan terakhir diupdate
    """

    id: UUID = Field(..., description="User unique identifier")
    email: EmailStr = Field(..., description="Email address")
    full_name: str = Field(..., description="Full name")
    avatar_url: str | None = Field(None, description="Profile picture URL")
    google_id: str | None = Field(None, description="Google ID (if OAuth login)")
    risk_profile: str = Field(
        ..., description="Risk profile: conservative | moderate | aggressive"
    )
    default_currency: str = Field(..., description="Default currency (IDR, USD, etc)")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Config untuk convert dari SQLAlchemy model ke Pydantic
    model_config = ConfigDict(
        from_attributes=True,  # Allow conversion from ORM models
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "john@example.com",
                    "full_name": "John Doe",
                    "avatar_url": "https://example.com/avatar.jpg",
                    "google_id": None,
                    "risk_profile": "moderate",
                    "default_currency": "IDR",
                    "is_active": True,
                    "created_at": "2026-05-12T10:00:00Z",
                    "updated_at": "2026-05-12T10:00:00Z",
                }
            ]
        },
    )


class UserUpdate(BaseModel):
    """
    Schema untuk update user profile

    Dipakai di: PUT /api/v1/users/me

    Semua field optional (user bisa update sebagian saja)

    Field yang bisa diupdate:
    - full_name: Ganti nama
    - risk_profile: Ganti profil risiko
    - default_currency: Ganti mata uang default

    Field yang TIDAK bisa diupdate:
    - email: Tidak bisa diganti (identifier utama)
    - password: Harus lewat endpoint khusus change password
    - id, created_at, updated_at: Auto-managed
    """

    full_name: str | None = Field(
        None, min_length=2, max_length=100, description="Full name"
    )
    risk_profile: str | None = Field(
        None,
        description="Risk profile",
        pattern="^(conservative|moderate|aggressive)$",  # Hanya 3 pilihan ini
    )
    default_currency: str | None = Field(
        None,
        min_length=3,
        max_length=5,
        description="Default currency code (e.g., IDR, USD)",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "full_name": "John Doe Updated",
                    "risk_profile": "aggressive",
                    "default_currency": "USD",
                }
            ]
        }
    }
