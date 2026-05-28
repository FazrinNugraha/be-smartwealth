"""
Authentication Schemas - Request/Response models for auth endpoints

Fungsi file ini:
- RegisterRequest: Validasi data saat user register (email, password, nama)
- LoginRequest: Validasi data saat user login (email, password)
- TokenResponse: Format response setelah login/register berhasil (access_token, refresh_token)
- RefreshTokenRequest: Validasi data saat refresh token
- GoogleAuthRequest: Validasi data dari Google OAuth
"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """
    Schema untuk register user baru

    Dipakai di: POST /api/v1/auth/register

    Validasi:
    - email: Harus format email valid (auto-check oleh EmailStr)
    - password: Min 8 karakter
    - full_name: Min 2 karakter, max 100 karakter
    """

    email: EmailStr = Field(..., description="Email address for login")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "john@example.com",
                    "password": "MySecurePass123!",
                    "full_name": "John Doe",
                }
            ]
        }
    }


class LoginRequest(BaseModel):
    """
    Schema untuk login user

    Dipakai di: POST /api/v1/auth/login

    Validasi:
    - email: Harus format email valid
    - password: Required (tidak ada min length karena user sudah pernah register)
    """

    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "email": "john@example.com",
                    "password": "MySecurePass123!",
                }
            ]
        }
    }


class TokenResponse(BaseModel):
    """
    Schema untuk response setelah login/register berhasil

    Dipakai di:
    - POST /api/v1/auth/register (response)
    - POST /api/v1/auth/login (response)
    - POST /api/v1/auth/refresh (response)

    Field:
    - access_token: JWT token untuk akses API (expire 15 menit)
    - refresh_token: Token untuk refresh access_token (expire 7 hari)
    - token_type: Selalu "bearer" (standar OAuth2)
    """

    access_token: str = Field(..., description="JWT access token (15 min expiry)")
    refresh_token: str = Field(..., description="Refresh token (7 days expiry)")
    token_type: str = Field(
        default="bearer", description="Token type (always 'bearer')"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                }
            ]
        }
    }


class RefreshTokenRequest(BaseModel):
    """
    Schema untuk refresh access token

    Dipakai di: POST /api/v1/auth/refresh

    Fungsi: Tukar refresh_token lama dengan access_token + refresh_token baru
    """

    refresh_token: str = Field(..., description="Valid refresh token")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                }
            ]
        }
    }


class GoogleAuthRequest(BaseModel):
    """
    Schema untuk Google OAuth login

    Dipakai di: POST /api/v1/auth/google

    Fungsi: Terima authorization code dari Google, tukar jadi user info
    """

    code: str = Field(..., description="Authorization code from Google OAuth")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "code": "4/0AY0e-g7xxxxxxxxxxxxxxxxxxx",
                }
            ]
        }
    }
