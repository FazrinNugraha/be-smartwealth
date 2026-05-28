"""
Asset Service - Business logic for asset management

Fungsi file ini:
- create_asset: Tambah aset baru ke portfolio user
- get_user_assets: List semua aset aktif user
- get_asset: Detail satu aset (dengan validasi ownership)
- update_asset: Update aset (quantity, avg_buy_price, notes)
- delete_asset: Soft delete aset (set is_active=False)
- enrich_asset_with_price: Tambahkan harga real-time ke asset response
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserAsset, User
from app.schemas import AssetCreate, AssetUpdate, AssetResponse
from app.services import price_service, dashboard_service
from app.utils.currency import infer_currency


async def create_asset(
    db: AsyncSession,
    user_id: UUID,
    data: AssetCreate,
) -> UserAsset:
    """
    Tambah aset baru ke portfolio user

    Args:
        db: Database session
        user_id: UUID user yang menambahkan aset
        data: AssetCreate schema (symbol, asset_name, asset_type, quantity, avg_buy_price)

    Returns:
        UserAsset object yang baru dibuat

    Validasi:
        - Symbol tidak boleh duplikat untuk user yang sama
        - Quantity dan avg_buy_price harus > 0

    Fungsi: Dipakai di endpoint POST /api/v1/assets
    """
    # Check if asset with same symbol already exists for this user
    result = await db.execute(
        select(UserAsset).where(
            UserAsset.user_id == user_id,
            UserAsset.symbol == data.symbol,
            UserAsset.is_active == True,
        )
    )
    existing_asset = result.scalar_one_or_none()

    if existing_asset:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset with symbol '{data.symbol}' already exists in your portfolio",
        )

    # Auto-detect currency if not provided
    currency = data.currency or infer_currency(data.asset_type, data.symbol)

    # Create new asset
    asset = UserAsset(
        user_id=user_id,
        symbol=data.symbol,
        asset_name=data.asset_name,
        asset_type=data.asset_type,
        quantity=data.quantity,
        avg_buy_price=data.avg_buy_price,
        currency=currency,
        notes=data.notes,
        is_active=True,
    )

    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    # Invalidate dashboard cache so next summary fetch is fresh
    dashboard_service.invalidate_summary_cache(str(user_id))

    return asset


async def get_user_assets(
    db: AsyncSession,
    user_id: UUID,
    asset_type: str | None = None,
) -> list[UserAsset]:
    """
    List semua aset aktif user

    Args:
        db: Database session
        user_id: UUID user
        asset_type: Filter by asset_type (optional)

    Returns:
        List of UserAsset objects

    Filter:
        - Hanya aset dengan is_active=True
        - Hanya aset milik user tersebut
        - Optional: filter by asset_type (stock_id, stock_us, crypto, gold, etc)

    Fungsi: Dipakai di endpoint GET /api/v1/assets
    """
    query = select(UserAsset).where(
        UserAsset.user_id == user_id,
        UserAsset.is_active == True,
    )

    # Filter by asset_type if provided
    if asset_type:
        query = query.where(UserAsset.asset_type == asset_type)

    # Order by created_at descending (newest first)
    query = query.order_by(UserAsset.created_at.desc())

    result = await db.execute(query)
    assets = result.scalars().all()

    return list(assets)


async def get_asset(
    db: AsyncSession,
    user_id: UUID,
    asset_id: UUID,
) -> UserAsset:
    """
    Get detail satu aset dengan validasi ownership

    Args:
        db: Database session
        user_id: UUID user yang request
        asset_id: UUID aset yang mau diambil

    Returns:
        UserAsset object

    Raises:
        HTTPException 404: Jika aset tidak ditemukan
        HTTPException 403: Jika aset bukan milik user

    Security:
        - User hanya bisa akses aset miliknya sendiri
        - Aset yang sudah di-delete (is_active=False) tidak bisa diakses

    Fungsi: Dipakai di endpoint GET /api/v1/assets/{id}
    """
    result = await db.execute(
        select(UserAsset).where(
            UserAsset.id == asset_id,
            UserAsset.is_active == True,
        )
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Validate ownership
    if asset.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this asset",
        )

    return asset


async def update_asset(
    db: AsyncSession,
    user_id: UUID,
    asset_id: UUID,
    data: AssetUpdate,
) -> UserAsset:
    """
    Update aset (quantity, avg_buy_price, notes)

    Args:
        db: Database session
        user_id: UUID user yang request
        asset_id: UUID aset yang mau diupdate
        data: AssetUpdate schema (quantity?, avg_buy_price?, notes?)

    Returns:
        UserAsset object yang sudah diupdate

    Raises:
        HTTPException 404: Jika aset tidak ditemukan
        HTTPException 403: Jika aset bukan milik user

    Note:
        - Semua field optional (partial update)
        - Hanya update field yang di-provide
        - Quantity dan avg_buy_price harus > 0 jika di-update

    Fungsi: Dipakai di endpoint PUT /api/v1/assets/{id}
    """
    # Get asset with ownership validation
    asset = await get_asset(db, user_id, asset_id)

    # Update fields yang di-provide
    if data.quantity is not None:
        asset.quantity = data.quantity

    if data.avg_buy_price is not None:
        asset.avg_buy_price = data.avg_buy_price

    if data.notes is not None:
        asset.notes = data.notes

    asset.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(asset)

    dashboard_service.invalidate_summary_cache(str(user_id))

    return asset


async def delete_asset(
    db: AsyncSession,
    user_id: UUID,
    asset_id: UUID,
) -> dict:
    """
    Soft delete aset (set is_active=False)

    Args:
        db: Database session
        user_id: UUID user yang request
        asset_id: UUID aset yang mau dihapus

    Returns:
        Dict dengan message success

    Raises:
        HTTPException 404: Jika aset tidak ditemukan
        HTTPException 403: Jika aset bukan milik user

    Note:
        - Soft delete: data tidak dihapus dari database
        - Hanya set is_active=False
        - Aset yang sudah di-delete tidak muncul di list
        - Transactions terkait aset ini tetap ada (untuk history)

    Fungsi: Dipakai di endpoint DELETE /api/v1/assets/{id}
    """
    # Get asset with ownership validation
    asset = await get_asset(db, user_id, asset_id)

    # Soft delete
    asset.is_active = False
    asset.updated_at = datetime.utcnow()

    await db.commit()

    dashboard_service.invalidate_summary_cache(str(user_id))

    return {"message": "Asset deleted successfully"}
