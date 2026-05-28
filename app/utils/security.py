"""
Security Utilities - Helper functions for authentication

Fungsi file ini:
- get_current_user: FastAPI dependency untuk get user dari JWT token
- oauth2_scheme: OAuth2 password bearer scheme

Dipakai untuk protected routes:
@app.get("/api/v1/users/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.services.auth_service import verify_token

# ── HTTP Bearer Scheme ────────────────────────────────────────
# Ini akan bikin field "Value" di Swagger UI untuk paste token langsung
http_bearer = HTTPBearer(
    scheme_name="Bearer Token",
    description="Paste your access_token here (without 'Bearer' prefix)",
    auto_error=True,
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get current user dari JWT token
    
    Args:
        credentials: HTTP Bearer credentials (token dari header "Authorization: Bearer <token>")
        db: Database session
    
    Returns:
        User object
    
    Raises:
        HTTPException 401: Jika token invalid atau user tidak ditemukan
    
    Process:
        1. Extract token dari header "Authorization: Bearer <token>"
        2. Decode JWT token
        3. Get user_id dari token payload
        4. Query user dari database
        5. Return user object
    
    Fungsi: Dipakai sebagai dependency di protected routes
    
    Contoh:
        @app.get("/api/v1/users/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return current_user
    
    Swagger UI:
        - Klik "Authorize" button (icon gembok)
        - Paste access_token di field "Value"
        - Klik "Authorize"
        - Semua protected routes otomatis include token di header
    """
    # Get token from credentials
    token = credentials.credentials
    
    # Verify token and get payload
    payload = verify_token(token, token_type="access")
    
    # Get user_id from payload
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    
    return user
