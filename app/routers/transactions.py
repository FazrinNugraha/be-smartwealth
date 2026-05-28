"""
Transactions Router - API endpoints for transaction management

Endpoints:
- POST /transactions: Create transaction (BUY/SELL)
- GET /transactions: List all transactions with filters
- GET /transactions/{id}: Get transaction detail
- DELETE /transactions/{id}: Delete transaction

Semua endpoint protected (butuh login)
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.schemas import TransactionCreate, TransactionResponse
from app.services.transaction_service import (
    create_transaction,
    get_user_transactions,
    get_transaction,
    delete_transaction,
)
from app.utils.security import get_current_user

router = APIRouter()


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction_endpoint(
    data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create transaction (BUY/SELL)

    Request Body:
        - asset_id: UUID asset yang ditransaksikan
        - type: "buy" atau "sell"
        - quantity: Jumlah unit
        - price_per_unit: Harga per unit
        - fees: Biaya transaksi (optional)
        - notes: Catatan (optional)
        - transaction_date: Tanggal transaksi

    Response:
        - Transaction object yang baru dibuat
        - Asset quantity & avg_buy_price otomatis terupdate

    Errors:
        - 401: Not authenticated
        - 403: Asset bukan milik user
        - 404: Asset not found
        - 400: Oversell (sell > quantity)
        - 422: Validation error

    BUY Process:
        1. Tambah quantity ke asset
        2. Recalculate avg_buy_price
        3. Simpan transaction

    SELL Process:
        1. Validasi quantity cukup
        2. Kurangi quantity dari asset
        3. Avg_buy_price tetap
        4. Simpan transaction

    Example BUY:
        POST /api/v1/transactions
        {
          "asset_id": "uuid-bbca",
          "type": "buy",
          "quantity": 50,
          "price_per_unit": 10000,
          "fees": 25000,
          "notes": "Beli saat dip",
          "transaction_date": "2026-05-12T10:00:00Z"
        }

    Example SELL:
        POST /api/v1/transactions
        {
          "asset_id": "uuid-bbca",
          "type": "sell",
          "quantity": 30,
          "price_per_unit": 10500,
          "fees": 20000,
          "notes": "Take profit",
          "transaction_date": "2026-05-12T15:00:00Z"
        }
    """
    transaction = await create_transaction(db, current_user.id, data)
    return transaction


@router.get("", response_model=list[TransactionResponse])
async def list_transactions_endpoint(
    asset_id: UUID | None = Query(None, description="Filter by asset ID"),
    type: str | None = Query(None, description="Filter by type (buy/sell)"),
    start_date: datetime | None = Query(None, description="Filter from date"),
    end_date: datetime | None = Query(None, description="Filter to date"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all transactions with filters

    Query Parameters:
        - asset_id: Filter by specific asset (optional)
        - type: Filter by "buy" or "sell" (optional)
        - start_date: Filter from date (optional)
        - end_date: Filter to date (optional)

    Response:
        - List of transaction objects
        - Sorted by transaction_date descending (newest first)
        - Only user's own transactions

    Errors:
        - 401: Not authenticated

    Examples:
        GET /api/v1/transactions
        GET /api/v1/transactions?asset_id=uuid-bbca
        GET /api/v1/transactions?type=buy
        GET /api/v1/transactions?start_date=2026-01-01&end_date=2026-12-31
        GET /api/v1/transactions?asset_id=uuid-bbca&type=sell
    """
    transactions = await get_user_transactions(
        db,
        current_user.id,
        asset_id=asset_id,
        transaction_type=type,
        start_date=start_date,
        end_date=end_date,
    )
    return transactions


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction_endpoint(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get transaction detail

    Path Parameters:
        - transaction_id: UUID transaction

    Response:
        - Transaction object dengan detail lengkap

    Errors:
        - 401: Not authenticated
        - 403: Transaction bukan milik user
        - 404: Transaction not found

    Security:
        - User hanya bisa akses transaction miliknya sendiri

    Example:
        GET /api/v1/transactions/123e4567-e89b-12d3-a456-426614174000
    """
    transaction = await get_transaction(db, current_user.id, transaction_id)
    return transaction


@router.delete("/{transaction_id}")
async def delete_transaction_endpoint(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete transaction dan recalculate asset

    Path Parameters:
        - transaction_id: UUID transaction

    Response:
        - Success message
        - Asset quantity & avg_buy_price otomatis di-recalculate

    Errors:
        - 401: Not authenticated
        - 403: Transaction bukan milik user
        - 404: Transaction not found
        - 400: Cannot reverse (quantity insufficient)

    Process:
        BUY transaction deleted:
        - Kurangi quantity dari asset
        - Recalculate avg_buy_price

        SELL transaction deleted:
        - Tambah quantity kembali ke asset
        - Avg_buy_price tetap

    Note:
        - Transaction dihapus permanent dari database
        - Asset otomatis terupdate
        - Gunakan dengan hati-hati!

    Example:
        DELETE /api/v1/transactions/123e4567-e89b-12d3-a456-426614174000
    """
    result = await delete_transaction(db, current_user.id, transaction_id)
    return result
