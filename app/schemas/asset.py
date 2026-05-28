"""
Asset Schemas - Request/Response models for asset management

Fungsi file ini:
- AssetCreate: Validasi data saat user tambah aset baru
- AssetResponse: Format data aset yang dikirim ke client (include current price & ROI)
- AssetUpdate: Validasi data saat user update aset
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AssetCreate(BaseModel):
    """
    Schema untuk tambah aset baru

    Dipakai di: POST /api/v1/assets

    Validasi:
    - symbol: Kode aset (BBCA.JK, bitcoin, GC=F, dll) - max 20 char
    - asset_name: Nama lengkap aset - max 255 char
    - asset_type: Jenis aset (stock_id, stock_us, crypto, gold, cash, dll)
    - quantity: Jumlah yang dimiliki (support desimal untuk crypto)
    - avg_buy_price: Harga beli rata-rata
    - currency: Mata uang (USD, IDR, EUR) - auto-detected jika tidak diisi
    - notes: Catatan pribadi (optional)

    Contoh:
    - Saham: symbol="BBCA.JK", asset_name="Bank Central Asia", asset_type="stock_id"
    - Crypto: symbol="bitcoin", asset_name="Bitcoin", asset_type="crypto"
    - Emas: symbol="GOLD", asset_name="Gold", asset_type="gold"
    """

    symbol: str = Field(
        ..., min_length=1, max_length=20, description="Asset symbol/ticker"
    )
    asset_name: str = Field(
        ..., min_length=1, max_length=255, description="Asset full name"
    )
    asset_type: str = Field(
        ...,
        description="Asset type",
        pattern="^(stock_id|stock_us|crypto|gold|mutual_fund|bond|cash|property)$",
    )
    quantity: Decimal = Field(
        ..., gt=0, description="Quantity owned (supports decimals)"
    )
    avg_buy_price: Decimal = Field(..., gt=0, description="Average buy price per unit")
    currency: str | None = Field(
        None,
        min_length=3,
        max_length=3,
        description="Currency code (auto-detected if not provided)",
    )
    notes: str | None = Field(None, max_length=1000, description="Personal notes")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "symbol": "BBCA.JK",
                    "asset_name": "Bank Central Asia",
                    "asset_type": "stock_id",
                    "quantity": "100",
                    "avg_buy_price": "8500",
                    "notes": "Beli saat turun",
                }
            ]
        }
    }


class AssetResponse(BaseModel):
    """
    Schema untuk response data aset

    Dipakai di:
    - GET /api/v1/assets (list semua aset)
    - GET /api/v1/assets/{id} (detail satu aset)
    - POST /api/v1/assets (response setelah create)

    Field tambahan (tidak ada di database):
    - current_price: Harga terkini dari API (yfinance/coingecko)
    - current_value: Nilai sekarang (quantity × current_price)
    - roi: Return on Investment (%)
    - unrealized_pnl: Profit/Loss yang belum direalisasi

    Field ini dihitung on-the-fly saat request, tidak disimpan di database.
    """

    id: UUID = Field(..., description="Asset unique identifier")
    user_id: UUID = Field(..., description="Owner user ID")
    symbol: str = Field(..., description="Asset symbol/ticker")
    asset_name: str = Field(..., description="Asset full name")
    asset_type: str = Field(..., description="Asset type")
    quantity: Decimal = Field(..., description="Quantity owned")
    avg_buy_price: Decimal = Field(..., description="Average buy price per unit")
    currency: str = Field(default="IDR", description="Currency code (USD, IDR, EUR)")
    notes: str | None = Field(None, description="Personal notes")
    is_active: bool = Field(..., description="Asset active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Computed fields (dihitung saat runtime, tidak di database)
    current_price: Decimal | None = Field(None, description="Current market price")
    current_value: Decimal | None = Field(
        None, description="Current total value (qty × price)"
    )
    roi: Decimal | None = Field(None, description="Return on Investment (%)")
    unrealized_pnl: Decimal | None = Field(None, description="Unrealized Profit/Loss")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "user_id": "987e6543-e21b-12d3-a456-426614174000",
                    "symbol": "BBCA.JK",
                    "asset_name": "Bank Central Asia",
                    "asset_type": "stock_id",
                    "quantity": "100",
                    "avg_buy_price": "8500",
                    "notes": "Beli saat turun",
                    "is_active": True,
                    "created_at": "2026-05-12T10:00:00Z",
                    "updated_at": "2026-05-12T10:00:00Z",
                    "current_price": "8750",
                    "current_value": "875000",
                    "roi": "2.94",
                    "unrealized_pnl": "25000",
                }
            ]
        },
    )


class AssetUpdate(BaseModel):
    """
    Schema untuk update aset

    Dipakai di: PUT /api/v1/assets/{id}

    Semua field optional (user bisa update sebagian saja)

    Field yang bisa diupdate:
    - notes: Ganti catatan
    - quantity: Ganti jumlah (manual adjustment)
    - avg_buy_price: Ganti harga beli rata-rata (manual adjustment)

    Field yang TIDAK bisa diupdate:
    - symbol, asset_name, asset_type: Tidak bisa diganti (buat aset baru saja)
    - id, user_id, created_at: Auto-managed

    Note: Untuk update quantity/avg_buy_price via transaksi, pakai endpoint /transactions
    """

    notes: str | None = Field(None, max_length=1000, description="Personal notes")
    quantity: Decimal | None = Field(None, gt=0, description="Quantity owned")
    avg_buy_price: Decimal | None = Field(None, gt=0, description="Average buy price")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "notes": "Updated notes",
                    "quantity": "150",
                    "avg_buy_price": "8600",
                }
            ]
        }
    }
