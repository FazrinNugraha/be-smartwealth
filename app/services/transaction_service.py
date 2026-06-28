"""
Transaction Service - Business logic for transaction management

Fungsi file ini:
- create_transaction: Catat transaksi BUY/SELL + auto-update asset
- get_user_transactions: List transactions dengan filter
- get_transaction: Detail satu transaction
- delete_transaction: Hapus transaction + recalculate asset
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, UserAsset, User
from app.schemas import TransactionCreate
from app.services import dashboard_service


def _attach_asset_info(tx: Transaction) -> Transaction:
    """Attach denormalized asset info to transaction object for response."""
    if tx.asset:
        tx.asset_symbol = tx.asset.symbol
        tx.asset_name = tx.asset.asset_name
        tx.asset_type = tx.asset.asset_type
        tx.currency = getattr(tx.asset, "currency", "IDR")
    else:
        tx.asset_symbol = None
        tx.asset_name = None
        tx.asset_type = None
        tx.currency = "IDR"
    return tx


async def create_transaction(
    db: AsyncSession,
    user_id: UUID,
    data: TransactionCreate,
) -> Transaction:
    """
    Catat transaksi BUY/SELL dan auto-update asset

    Args:
        db: Database session
        user_id: UUID user yang membuat transaksi
        data: TransactionCreate schema

    Returns:
        Transaction object yang baru dibuat

    Process:
        BUY:
        1. Tambah quantity ke asset
        2. Recalculate avg_buy_price: (old_qty×old_avg + buy_qty×buy_price) / total_qty
        3. Simpan transaction

        SELL:
        1. Validasi quantity cukup (tidak oversell)
        2. Kurangi quantity dari asset
        3. Avg_buy_price TIDAK berubah
        4. Simpan transaction

    Raises:
        HTTPException 404: Asset tidak ditemukan
        HTTPException 403: Asset bukan milik user
        HTTPException 400: Oversell (sell > quantity)

    Fungsi: Dipakai di endpoint POST /api/v1/transactions
    """
    # Get asset with ownership validation
    result = await db.execute(
        select(UserAsset).where(
            UserAsset.id == data.asset_id,
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
            detail="You don't have permission to create transaction for this asset",
        )

    # Calculate total amount
    total_amount = data.quantity * data.price_per_unit

    # Process based on transaction type
    if data.transaction_type == "buy":
        # BUY: Tambah quantity + recalculate avg_buy_price
        old_qty = asset.quantity
        old_avg = asset.avg_buy_price
        new_qty = old_qty + data.quantity

        # Rumus: (old_qty × old_avg + buy_qty × buy_price) / total_qty
        new_avg = (old_qty * old_avg + data.quantity * data.price_per_unit) / new_qty

        asset.quantity = new_qty
        asset.avg_buy_price = new_avg

    elif data.transaction_type == "sell":
        # SELL: Kurangi quantity, avg_buy_price tetap

        # Validasi: tidak bisa sell lebih dari yang dimiliki
        if data.quantity > asset.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot sell {data.quantity} units. You only have {asset.quantity} units.",
            )

        asset.quantity -= data.quantity
        # avg_buy_price TIDAK berubah saat sell

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transaction type. Must be 'buy' or 'sell'.",
        )

    # Update asset timestamp
    asset.updated_at = datetime.utcnow()

    # Create transaction record
    transaction = Transaction(
        user_id=user_id,
        asset_id=data.asset_id,
        transaction_type=data.transaction_type,
        quantity=data.quantity,
        price_per_unit=data.price_per_unit,
        total_amount=total_amount,
        fees=data.fees,
        notes=data.notes,
        transaction_date=data.transaction_date,
    )

    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    await db.refresh(asset)

    # Attach asset info for response
    transaction.asset = asset
    _attach_asset_info(transaction)

    # Invalidate dashboard cache (asset quantity/avg changed)
    dashboard_service.invalidate_summary_cache(str(user_id))
    dashboard_service.invalidate_analytics_cache(str(user_id))

    return transaction


async def get_user_transactions(
    db: AsyncSession,
    user_id: UUID,
    asset_id: UUID | None = None,
    transaction_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[Transaction]:
    """
    List transactions user dengan filter

    Args:
        db: Database session
        user_id: UUID user
        asset_id: Filter by asset (optional)
        transaction_type: Filter by type "buy" or "sell" (optional)
        start_date: Filter from date (optional)
        end_date: Filter to date (optional)

    Returns:
        List of Transaction objects

    Filter:
        - Hanya transactions milik user
        - Optional: filter by asset_id
        - Optional: filter by type (buy/sell)
        - Optional: filter by date range

    Fungsi: Dipakai di endpoint GET /api/v1/transactions
    """
    query = (
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .options(selectinload(Transaction.asset))
    )

    # Filter by asset_id
    if asset_id:
        query = query.where(Transaction.asset_id == asset_id)

    # Filter by type
    if transaction_type:
        query = query.where(Transaction.transaction_type == transaction_type)

    # Filter by date range
    if start_date:
        query = query.where(Transaction.transaction_date >= start_date)

    if end_date:
        query = query.where(Transaction.transaction_date <= end_date)

    # Order by transaction_date descending (newest first)
    query = query.order_by(Transaction.transaction_date.desc())

    result = await db.execute(query)
    transactions = result.scalars().all()

    # Attach asset info for response
    for tx in transactions:
        _attach_asset_info(tx)

    return list(transactions)


async def get_transaction(
    db: AsyncSession,
    user_id: UUID,
    transaction_id: UUID,
) -> Transaction:
    """
    Get detail satu transaction dengan validasi ownership

    Args:
        db: Database session
        user_id: UUID user yang request
        transaction_id: UUID transaction

    Returns:
        Transaction object

    Raises:
        HTTPException 404: Transaction tidak ditemukan
        HTTPException 403: Transaction bukan milik user

    Security:
        - User hanya bisa akses transaction miliknya sendiri

    Fungsi: Dipakai di endpoint GET /api/v1/transactions/{id}
    """
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    # Validate ownership
    if transaction.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this transaction",
        )

    return transaction


async def delete_transaction(
    db: AsyncSession,
    user_id: UUID,
    transaction_id: UUID,
) -> dict:
    """
    Hapus transaction dan recalculate asset

    Args:
        db: Database session
        user_id: UUID user yang request
        transaction_id: UUID transaction yang mau dihapus

    Returns:
        Dict dengan message success

    Raises:
        HTTPException 404: Transaction tidak ditemukan
        HTTPException 403: Transaction bukan milik user

    Process:
        1. Get transaction dengan ownership validation
        2. Get asset terkait
        3. Reverse transaction:
           - Jika BUY: kurangi quantity, recalculate avg_buy_price
           - Jika SELL: tambah quantity kembali
        4. Delete transaction
        5. Update asset

    Note:
        - Recalculate avg_buy_price hanya untuk BUY transactions
        - SELL transactions hanya restore quantity

    Fungsi: Dipakai di endpoint DELETE /api/v1/transactions/{id}
    """
    # Get transaction with ownership validation
    transaction = await get_transaction(db, user_id, transaction_id)

    # Get asset
    result = await db.execute(
        select(UserAsset).where(UserAsset.id == transaction.asset_id)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Reverse transaction
    if transaction.transaction_type == "buy":
        # Reverse BUY: kurangi quantity, recalculate avg_buy_price

        # Validasi: pastikan quantity cukup untuk di-reverse
        if transaction.quantity > asset.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete this transaction. Asset quantity is less than transaction quantity.",
            )

        # Recalculate avg_buy_price
        # Formula: (current_total - tx_total) / (current_qty - tx_qty)
        current_total = asset.quantity * asset.avg_buy_price
        tx_total = transaction.quantity * transaction.price_per_unit
        new_qty = asset.quantity - transaction.quantity

        if new_qty > 0:
            new_avg = (current_total - tx_total) / new_qty
            asset.avg_buy_price = new_avg
        else:
            # Jika quantity jadi 0, reset avg_buy_price ke 0
            asset.avg_buy_price = Decimal("0")

        asset.quantity = new_qty

    elif transaction.transaction_type == "sell":
        # Reverse SELL: tambah quantity kembali, avg_buy_price tetap
        asset.quantity += transaction.quantity
        # avg_buy_price tidak berubah

    # Update asset timestamp
    asset.updated_at = datetime.utcnow()

    # Delete transaction
    await db.delete(transaction)
    await db.commit()

    dashboard_service.invalidate_summary_cache(str(user_id))
    dashboard_service.invalidate_analytics_cache(str(user_id))

    return {"message": "Transaction deleted successfully"}
