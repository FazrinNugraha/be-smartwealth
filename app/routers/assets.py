"""
Assets Router - API endpoints for asset management

Endpoints:
- POST /assets: Tambah aset baru
- GET /assets: List semua aset user
- GET /assets/{id}: Detail satu aset
- PUT /assets/{id}: Update aset
- DELETE /assets/{id}: Hapus aset (soft delete)

Semua endpoint protected (butuh login)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import AssetCreate, AssetResponse, AssetUpdate
from app.services.asset_service import (
    create_asset,
    get_user_assets,
    get_asset,
    update_asset,
    delete_asset,
)
from app.utils.security import get_current_user

router = APIRouter()


@router.post("", response_model=AssetResponse, status_code=201)
async def create_asset_endpoint(
    data: AssetCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Tambah aset baru ke portfolio

    Request Body:
        - symbol: Ticker symbol (e.g., "BBCA.JK", "bitcoin", "gold")
        - asset_name: Nama aset (e.g., "Bank Central Asia", "Bitcoin", "Gold")
        - asset_type: Tipe aset (stock_id | stock_us | crypto | gold | property | other)
        - quantity: Jumlah unit (e.g., 100 lembar saham, 0.5 BTC)
        - avg_buy_price: Harga beli rata-rata per unit
        - notes: Catatan tambahan (optional)

    Response:
        - Asset object yang baru dibuat

    Errors:
        - 401: Not authenticated
        - 409: Asset dengan symbol yang sama sudah ada
        - 422: Validation error (quantity/price <= 0, invalid asset_type)

    Example:
        POST /api/v1/assets
        {
          "symbol": "BBCA.JK",
          "asset_name": "Bank Central Asia",
          "asset_type": "stock_id",
          "quantity": 100,
          "avg_buy_price": 9500,
          "notes": "Beli saat dip"
        }
    """
    asset = await create_asset(db, current_user.id, data)
    return asset


@router.get("", response_model=list[AssetResponse])
async def list_assets_endpoint(
    asset_type: str | None = Query(None, description="Filter by asset type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List semua aset aktif user

    Query Parameters:
        - asset_type: Filter by asset type (optional)
          Valid values: stock_id, stock_us, crypto, gold, property, other

    Response:
        - List of asset objects
        - Sorted by created_at descending (newest first)
        - Only active assets (is_active=True)

    Errors:
        - 401: Not authenticated

    Example:
        GET /api/v1/assets
        GET /api/v1/assets?asset_type=crypto
    """
    assets = await get_user_assets(db, current_user.id, asset_type)
    return assets


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset_endpoint(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detail satu aset

    Path Parameters:
        - asset_id: UUID aset

    Response:
        - Asset object dengan detail lengkap

    Errors:
        - 401: Not authenticated
        - 403: Asset bukan milik user (forbidden)
        - 404: Asset not found

    Security:
        - User hanya bisa akses aset miliknya sendiri
        - Aset yang sudah di-delete tidak bisa diakses

    Example:
        GET /api/v1/assets/123e4567-e89b-12d3-a456-426614174000
    """
    asset = await get_asset(db, current_user.id, asset_id)
    return asset


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset_endpoint(
    asset_id: UUID,
    data: AssetUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update aset

    Path Parameters:
        - asset_id: UUID aset

    Request Body (semua field optional):
        - quantity: Update jumlah unit
        - avg_buy_price: Update harga beli rata-rata
        - notes: Update catatan

    Response:
        - Asset object yang sudah diupdate

    Errors:
        - 401: Not authenticated
        - 403: Asset bukan milik user (forbidden)
        - 404: Asset not found
        - 422: Validation error (quantity/price <= 0)

    Note:
        - Partial update: hanya update field yang di-provide
        - Field yang tidak di-provide tetap sama

    Example:
        PUT /api/v1/assets/123e4567-e89b-12d3-a456-426614174000
        {
          "quantity": 150,
          "notes": "Tambah beli lagi"
        }
    """
    asset = await update_asset(db, current_user.id, asset_id, data)
    return asset


@router.delete("/{asset_id}")
async def delete_asset_endpoint(
    asset_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Hapus aset (soft delete)

    Path Parameters:
        - asset_id: UUID aset

    Response:
        - Success message

    Errors:
        - 401: Not authenticated
        - 403: Asset bukan milik user (forbidden)
        - 404: Asset not found

    Note:
        - Soft delete: data tidak dihapus dari database
        - Aset set is_active=False
        - Aset tidak muncul di list lagi
        - Transactions terkait aset ini tetap ada (untuk history)

    Example:
        DELETE /api/v1/assets/123e4567-e89b-12d3-a456-426614174000
    """
    result = await delete_asset(db, current_user.id, asset_id)
    return result
