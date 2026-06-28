"""
Authentication Router - API endpoints for auth operations

Endpoints:
- POST /auth/register: Register user baru
- POST /auth/login: Login dan get tokens
- POST /auth/refresh: Refresh access token
- POST /auth/logout: Logout dan revoke refresh token
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User, RefreshToken
from app.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    GoogleAuthRequest,
)
from app.services.auth_service import (
    register_user,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    verify_token,
    exchange_google_code,
    get_google_user_info,
    google_login_or_register,
)
from app.utils.security import get_current_user
from app.services import dashboard_service

router = APIRouter()


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register user baru

    Process:
    1. Validasi input (email format, password min 8 char, dll)
    2. Check email sudah terdaftar atau belum
    3. Hash password dengan bcrypt
    4. Create user di database
    5. Generate access_token (expire 15 menit)
    6. Generate refresh_token (expire 7 hari) + save to DB
    7. Return tokens

    Request Body:
        - email: Email address (must be valid format)
        - password: Password (min 8 characters)
        - full_name: Full name (min 2 characters)

    Response:
        - access_token: JWT token untuk akses API (15 min)
        - refresh_token: Token untuk refresh access_token (7 days)
        - token_type: "bearer"

    Errors:
        - 409: Email already registered
        - 422: Validation error (invalid email, password too short, dll)
    """
    # Register user
    user = await register_user(db, data)

    # Generate tokens
    access_token = create_access_token(user.id, user.email)
    refresh_token, _ = await create_refresh_token(db, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Login dan get tokens (Support OAuth2 password flow untuk Swagger UI)

    Process:
    1. Validasi input (email format)
    2. Find user by email
    3. Verify password
    4. Generate access_token (expire 15 menit)
    5. Generate refresh_token (expire 7 hari) + save to DB
    6. Return tokens

    Form Data (untuk Swagger UI Authorize):
        - username: Email address (pakai email sebagai username)
        - password: Password

    Request Body (untuk manual API call):
        - email: Email address
        - password: Password

    Response:
        - access_token: JWT token untuk akses API (15 min)
        - refresh_token: Token untuk refresh access_token (7 days)
        - token_type: "bearer"

    Errors:
        - 401: Invalid email or password
        - 422: Validation error (invalid email format)

    Note:
        - Swagger UI "Authorize" button akan pakai endpoint ini
        - Username di form = email address
    """
    # Authenticate user (username = email)
    user = await authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    access_token = create_access_token(user.id, user.email)
    refresh_token, _ = await create_refresh_token(db, user.id)

    # Invalidate dashboard cache for fresh load
    dashboard_service.invalidate_summary_cache(str(user.id))
    dashboard_service.invalidate_analytics_cache(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/login/json", response_model=TokenResponse)
async def login_json(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Login dengan JSON body (alternative endpoint)

    Endpoint ini untuk client yang prefer JSON body daripada form data.
    Fungsi sama dengan /login, tapi accept JSON body.

    Request Body:
        - email: Email address
        - password: Password

    Response:
        - access_token: JWT token untuk akses API (15 min)
        - refresh_token: Token untuk refresh access_token (7 days)
        - token_type: "bearer"

    Errors:
        - 401: Invalid email or password
        - 422: Validation error (invalid email format)
    """
    # Authenticate user
    user = await authenticate_user(db, data.email, data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate tokens
    access_token = create_access_token(user.id, user.email)
    refresh_token, _ = await create_refresh_token(db, user.id)

    # Invalidate dashboard cache for fresh load
    dashboard_service.invalidate_summary_cache(str(user.id))
    dashboard_service.invalidate_analytics_cache(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token

    Process:
    1. Verify refresh_token valid
    2. Check token belum expired
    3. Check token belum di-revoke
    4. Revoke old refresh_token
    5. Generate new access_token + refresh_token
    6. Return new tokens

    Request Body:
        - refresh_token: Valid refresh token

    Response:
        - access_token: NEW JWT token (15 min)
        - refresh_token: NEW refresh token (7 days)
        - token_type: "bearer"

    Errors:
        - 401: Invalid or expired refresh token
        - 401: Token has been revoked

    Security:
        - Old refresh_token di-revoke (tidak bisa dipakai lagi)
        - Refresh token rotation untuk security
    """
    # Verify refresh token
    payload = verify_token(data.refresh_token, token_type="refresh")
    user_id = payload.get("sub")

    # Check if refresh token exists and not revoked
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == data.refresh_token,
            RefreshToken.is_revoked == False,
        )
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Revoke old refresh token
    token_record.is_revoked = True
    await db.commit()

    # Generate new tokens
    access_token = create_access_token(user.id, user.email)
    new_refresh_token, _ = await create_refresh_token(db, user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@router.post("/logout")
async def logout(
    data: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Logout dan revoke refresh token

    Process:
    1. Verify access_token (user must be logged in)
    2. Find refresh_token di database
    3. Revoke refresh_token (set is_revoked = true)
    4. Return success message

    Headers:
        - Authorization: Bearer <access_token>

    Request Body:
        - refresh_token: Refresh token yang mau di-revoke

    Response:
        - message: "Logged out successfully"

    Errors:
        - 401: Invalid access token (not logged in)
        - 404: Refresh token not found

    Security:
        - Setelah logout, refresh_token tidak bisa dipakai lagi
        - Access_token masih valid sampai expire (15 menit)
        - Untuk full logout, client harus hapus access_token dari storage
    """
    # Find and revoke refresh token
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == data.refresh_token,
            RefreshToken.user_id == current_user.id,
        )
    )
    token_record = result.scalar_one_or_none()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refresh token not found",
        )

    # Revoke token
    token_record.is_revoked = True
    await db.commit()

    # Invalidate dashboard cache on logout
    dashboard_service.invalidate_summary_cache(str(current_user.id))
    dashboard_service.invalidate_analytics_cache(str(current_user.id))

    return {"message": "Logged out successfully"}


@router.post("/google", response_model=TokenResponse)
async def google_auth(
    data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login atau register via Google OAuth"""
    try:
        # Step 1: Exchange code → Google access token
        token_data = await exchange_google_code(data.code)
        access_token_google = token_data.get("access_token")

        if not access_token_google:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get access token from Google",
            )

        # Step 2: Get user info dari Google
        user_info = await get_google_user_info(access_token_google)

        # Step 3: Login atau register user
        user = await google_login_or_register(db, user_info)

        # Step 4: Generate tokens
        access_token = create_access_token(user.id, user.email)
        refresh_token, _ = await create_refresh_token(db, user.id)

        # Invalidate dashboard cache for fresh load
        dashboard_service.invalidate_summary_cache(str(user.id))
        dashboard_service.invalidate_analytics_cache(str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    except HTTPException:
        raise  # Re-raise HTTPException as-is

    except Exception as e:
        import traceback

        print(f"[GOOGLE AUTH] Unexpected error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google auth failed: {str(e)}",
        )
