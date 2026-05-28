"""
Transaction Schemas - Request/Response models for transaction records

Fungsi file ini:
- TransactionCreate: Validasi data saat user catat transaksi buy/sell
- TransactionResponse: Format data transaksi yang dikirim ke client
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator


class TransactionCreate(BaseModel):
    """
    Schema untuk catat transaksi baru

    Dipakai di: POST /api/v1/transactions

    Validasi:
    - asset_id: UUID aset yang ditransaksikan
    - transaction_type: "buy" atau "sell"
    - quantity: Jumlah yang dibeli/dijual (harus > 0)
    - price_per_unit: Harga per unit saat transaksi
    - fees: Biaya broker/admin (default 0)
    - transaction_date: Kapan transaksi terjadi
    - notes: Catatan pribadi (optional)

    Logic setelah create:
    - Jika "buy": quantity aset bertambah, avg_buy_price dihitung ulang
    - Jika "sell": quantity aset berkurang, validasi tidak oversell
    """

    asset_id: UUID = Field(..., description="Asset ID to transact")
    transaction_type: str = Field(
        ...,
        description="Transaction type",
        pattern="^(buy|sell)$",  # Hanya buy atau sell
    )
    quantity: Decimal = Field(..., gt=0, description="Quantity to buy/sell")
    price_per_unit: Decimal = Field(
        ..., gt=0, description="Price per unit at transaction time"
    )
    fees: Decimal = Field(
        default=Decimal("0"), ge=0, description="Transaction fees (broker, admin)"
    )
    transaction_date: datetime = Field(..., description="Transaction date and time")
    notes: str | None = Field(None, max_length=1000, description="Personal notes")

    @field_validator("transaction_type")
    @classmethod
    def validate_transaction_type(cls, v: str) -> str:
        """Validasi transaction_type harus lowercase"""
        return v.lower()

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "asset_id": "123e4567-e89b-12d3-a456-426614174000",
                    "transaction_type": "buy",
                    "quantity": "100",
                    "price_per_unit": "8500",
                    "fees": "5000",
                    "transaction_date": "2026-05-12T10:00:00Z",
                    "notes": "Beli saat turun",
                }
            ]
        }
    }


class TransactionResponse(BaseModel):
    """
    Schema untuk response data transaksi

    Dipakai di:
    - GET /api/v1/transactions (list semua transaksi)
    - POST /api/v1/transactions (response setelah create)
    """

    id: UUID = Field(..., description="Transaction unique identifier")
    user_id: UUID = Field(..., description="Owner user ID")
    asset_id: UUID = Field(..., description="Asset ID")
    transaction_type: str = Field(..., description="Transaction type (buy/sell)")
    quantity: Decimal = Field(..., description="Quantity transacted")
    price_per_unit: Decimal = Field(..., description="Price per unit")
    total_amount: Decimal = Field(..., description="Total amount (qty × price)")
    fees: Decimal = Field(..., description="Transaction fees")
    notes: str | None = Field(None, description="Personal notes")
    transaction_date: datetime = Field(..., description="Transaction date")
    created_at: datetime = Field(..., description="Record creation timestamp")

    # Asset info (denormalized for convenience)
    asset_symbol: str | None = Field(None, description="Asset symbol")
    asset_name: str | None = Field(None, description="Asset name")
    asset_type: str | None = Field(None, description="Asset type")
    currency: str | None = Field(None, description="Asset currency")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_id": "987e6543-e21b-12d3-a456-426614174000",
                    "asset_id": "456e7890-e12b-34d5-a678-901234567890",
                    "transaction_type": "buy",
                    "quantity": "100",
                    "price_per_unit": "8500",
                    "total_amount": "850000",
                    "fees": "5000",
                    "notes": "Beli saat turun",
                    "transaction_date": "2026-05-12T10:00:00Z",
                    "created_at": "2026-05-12T10:05:00Z",
                }
            ]
        },
    )
