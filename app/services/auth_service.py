"""
Authentication Service - Business logic for auth operations

Fungsi file ini:
- hash_password / verify_password: Bcrypt password handling
- create_access_token / create_refresh_token: JWT token generation
- verify_token: Decode dan verify JWT token
- register_user / authenticate_user: Email + password auth
- exchange_google_code / get_google_user_info / google_login_or_register: Google OAuth
"""

import asyncio
import secrets
from datetime import datetime, timedelta
from uuid import UUID

import bcrypt
import httpx
from fastapi import HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, RefreshToken
from app.schemas import RegisterRequest
from app.utils.exceptions import AlreadyExistsError, ValidationError

# ══════════════════════════════════════════════════════════════
# Password Management
# ══════════════════════════════════════════════════════════════


def hash_password(password: str) -> str:
    """
    Hash password menggunakan bcrypt (rounds=10 — balance security vs speed)
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=10)  # 10 = ~100ms, cukup aman untuk dev/prod
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password cocok atau tidak
    """
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    """
    Async version of verify_password — runs bcrypt in thread pool
    agar tidak blocking event loop FastAPI
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, verify_password, plain_password, hashed_password
    )


# ══════════════════════════════════════════════════════════════
# JWT Token Management
# ══════════════════════════════════════════════════════════════


def create_access_token(user_id: UUID, email: str) -> str:
    """
    Buat JWT access token

    Args:
        user_id: UUID user
        email: Email user

    Returns:
        JWT token string (contoh: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")

    Token payload:
        - sub: user_id (subject)
        - email: email user
        - exp: expiry timestamp (15 menit dari sekarang)
        - iat: issued at timestamp
        - type: "access"

    Fungsi: Token ini dipakai untuk akses protected routes
    Expire: 15 menit (short-lived untuk security)
    """
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }

    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return token


async def create_refresh_token(db: AsyncSession, user_id: UUID) -> tuple[str, datetime]:
    """
    Buat refresh token dan simpan ke database

    Args:
        db: Database session
        user_id: UUID user

    Returns:
        Tuple (token_string, expires_at)

    Token payload:
        - sub: user_id
        - exp: expiry timestamp (7 hari dari sekarang)
        - iat: issued at timestamp
        - type: "refresh"

    Fungsi: Token ini dipakai untuk refresh access token yang expired
    Expire: 7 hari (long-lived)
    Disimpan di database untuk bisa di-revoke saat logout
    """
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }

    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    # Save to database
    refresh_token_record = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expire,
        is_revoked=False,
    )
    db.add(refresh_token_record)
    await db.commit()

    return token, expire


def verify_token(token: str, token_type: str = "access") -> dict:
    """
    Decode dan verify JWT token

    Args:
        token: JWT token string
        token_type: "access" atau "refresh"

    Returns:
        Token payload dict {"sub": user_id, "email": email, ...}

    Raises:
        HTTPException 401: Jika token invalid, expired, atau type salah

    Fungsi: Verify token valid dan belum expired
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

        # Check token type
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}",
            )

        return payload

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ══════════════════════════════════════════════════════════════
# User Management
# ══════════════════════════════════════════════════════════════


async def register_user(db: AsyncSession, data: RegisterRequest) -> User:
    """
    Register user baru

    Args:
        db: Database session
        data: RegisterRequest (email, password, full_name)

    Returns:
        User object yang baru dibuat

    Raises:
        AlreadyExistsError: Jika email sudah terdaftar

    Process:
        1. Check email sudah ada atau belum
        2. Hash password
        3. Create user di database
        4. Return user object

    Fungsi: Dipakai di endpoint POST /auth/register
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise AlreadyExistsError("User", "email", data.email)

    # Hash password
    hashed_password = hash_password(data.password)

    # Create user
    user = User(
        email=data.email,
        password=hashed_password,
        full_name=data.full_name,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    """
    Authenticate user (verify email + password)

    Args:
        db: Database session
        email: Email user
        password: Plain password dari user

    Returns:
        User object jika valid, None jika tidak

    Process:
        1. Find user by email
        2. Verify password
        3. Return user jika valid, None jika tidak

    Fungsi: Dipakai di endpoint POST /auth/login
    """
    # Find user by email
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return None

    # Verify password async (non-blocking)
    if not await verify_password_async(password, user.password):
        return None

    return user


# ══════════════════════════════════════════════════════════════
# Google OAuth
# ══════════════════════════════════════════════════════════════


async def exchange_google_code(code: str) -> dict:
    """
    Exchange Google authorization code untuk access token

    Args:
        code: Authorization code dari Google OAuth redirect

    Returns:
        dict dengan access_token, id_token, dll

    Raises:
        ValidationError: Jika code invalid atau expired

    Process:
        1. POST ke Google token endpoint
        2. Exchange code → access token
        3. Return token data

    Fungsi: Step 1 dari Google OAuth flow
    """
    token_url = "https://oauth2.googleapis.com/token"

    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=data)

        if response.status_code != 200:
            error_detail = response.json()
            print(f"[GOOGLE OAUTH] Token exchange failed: {error_detail}")
            print(f"[GOOGLE OAUTH] redirect_uri used: {settings.GOOGLE_REDIRECT_URI}")
            raise ValidationError(
                f"Google OAuth failed: {error_detail.get('error_description', error_detail.get('error', 'Unknown error'))}"
            )

        return response.json()


async def get_google_user_info(access_token: str) -> dict:
    """
    Get user info dari Google menggunakan access token

    Args:
        access_token: Google access token

    Returns:
        dict dengan email, name, picture, dll

    Raises:
        ValidationError: Jika token invalid

    Process:
        1. GET ke Google userinfo endpoint
        2. Return user data (email, name, picture)

    Fungsi: Step 2 dari Google OAuth flow
    """
    userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(userinfo_url, headers=headers)

        if response.status_code != 200:
            raise ValidationError("Failed to get user info from Google")

        return response.json()


async def google_login_or_register(db: AsyncSession, user_info: dict) -> User:
    """
    Login atau register user via Google OAuth

    Args:
        db: Database session
        user_info: User info dari Google (email, name, picture)

    Returns:
        User object (existing atau baru dibuat)

    Raises:
        ValidationError: Jika email tidak ada di Google response

    Process:
        1. Check apakah user dengan email ini sudah ada
        2. Jika sudah ada → return user (login)
        3. Jika belum ada → create user baru (register)
        4. Update avatar_url dari Google

    Fungsi: Step 3 dari Google OAuth flow

    Note:
        - Password di-set random karena user login via Google (tidak perlu password)
        - Avatar URL disimpan dari Google profile picture
    """
    email = user_info.get("email")
    name = user_info.get("name", email.split("@")[0] if email else "User")
    picture = user_info.get("picture")

    if not email:
        raise ValidationError("Email not provided by Google")

    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        # User exists → update avatar if changed
        if picture and user.avatar_url != picture:
            user.avatar_url = picture
            await db.commit()
            await db.refresh(user)

        return user

    # User doesn't exist → create new user
    # Generate random password (user won't use it, login via Google)
    random_password = secrets.token_urlsafe(32)
    hashed_password = hash_password(random_password)

    new_user = User(
        email=email,
        password=hashed_password,
        full_name=name,
        avatar_url=picture,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user
