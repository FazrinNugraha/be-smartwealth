"""
Users Router - API endpoints for user profile

Endpoints:
- GET /users/me: Get current user profile (protected)
- PUT /users/me: Update current user profile (protected)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import UserResponse, UserUpdate
from app.utils.security import get_current_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Get current user profile

    Headers:
        - Authorization: Bearer <access_token>

    Response:
        - User profile data (WITHOUT password!)

    Errors:
        - 401: Invalid or expired access token

    Fungsi: Test protected route
    User harus login dulu (punya access_token) untuk akses endpoint ini
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update current user profile

    Headers:
        - Authorization: Bearer <access_token>

    Request Body:
        - full_name: New full name (optional)
        - risk_profile: New risk profile (optional): conservative | moderate | aggressive
        - default_currency: New default currency (optional): IDR | USD | etc

    Response:
        - Updated user profile data

    Errors:
        - 401: Invalid or expired access token
        - 422: Validation error (invalid risk_profile, dll)

    Fungsi: Update user profile
    Semua field optional, user bisa update sebagian saja
    """
    # Update fields yang di-provide
    if data.full_name is not None:
        current_user.full_name = data.full_name

    if data.risk_profile is not None:
        current_user.risk_profile = data.risk_profile

    if data.default_currency is not None:
        current_user.default_currency = data.default_currency

    await db.commit()
    await db.refresh(current_user)

    return current_user
