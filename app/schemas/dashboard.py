"""
Dashboard Schemas - Response models for dashboard endpoints

Fungsi file ini:
- NetWorthResponse: Total kekayaan + breakdown per jenis aset
- AllocationItem: Item alokasi aset (untuk pie chart)
- AllocationResponse: Alokasi aset dalam persentase
- PerformanceItem: Performa per aset (ROI, CAGR, P&L)
- PerformanceResponse: Performa semua aset
- WealthHistoryItem: Item riwayat kekayaan (untuk line chart)
- WealthHistoryResponse: Riwayat kekayaan harian
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class NetWorthResponse(BaseModel):
    """
    Schema untuk response net worth

    Dipakai di: GET /api/v1/dashboard/net-worth

    Field:
    - total: Total kekayaan (sum semua aset)
    - breakdown: Detail per jenis aset {"stock_id": 100000000, "crypto": 30000000, ...}
    - change_24h: Perubahan 24 jam terakhir (%)

    Fungsi: Menampilkan total kekayaan user di dashboard
    """

    total: Decimal = Field(..., description="Total net worth")
    breakdown: dict[str, Decimal] = Field(..., description="Breakdown by asset type")
    change_24h: Decimal | None = Field(None, description="24h change percentage")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total": "150000000",
                    "breakdown": {
                        "stock_id": "100000000",
                        "crypto": "30000000",
                        "gold": "20000000",
                    },
                    "change_24h": "2.5",
                }
            ]
        }
    }


class AllocationItem(BaseModel):
    """
    Schema untuk item alokasi aset

    Field:
    - asset_type: Jenis aset (stock_id, crypto, dll)
    - value: Nilai dalam rupiah
    - percentage: Persentase dari total (untuk pie chart)

    Fungsi: Satu slice di pie chart alokasi
    """

    asset_type: str = Field(..., description="Asset type")
    value: Decimal = Field(..., description="Value in currency")
    percentage: Decimal = Field(..., description="Percentage of total portfolio")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "asset_type": "stock_id",
                    "value": "100000000",
                    "percentage": "66.67",
                }
            ]
        }
    }


class AllocationResponse(BaseModel):
    """
    Schema untuk response alokasi aset

    Dipakai di: GET /api/v1/dashboard/allocation

    Field:
    - allocations: List item alokasi (untuk pie chart)

    Fungsi: Menampilkan pie chart alokasi aset di dashboard
    """

    allocations: list[AllocationItem] = Field(
        ..., description="Asset allocation breakdown"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "allocations": [
                        {
                            "asset_type": "stock_id",
                            "value": "100000000",
                            "percentage": "66.67",
                        },
                        {
                            "asset_type": "crypto",
                            "value": "30000000",
                            "percentage": "20.00",
                        },
                        {
                            "asset_type": "gold",
                            "value": "20000000",
                            "percentage": "13.33",
                        },
                    ]
                }
            ]
        }
    }


class PerformanceItem(BaseModel):
    """
    Schema untuk item performa aset

    Field:
    - asset_id: UUID aset
    - symbol: Kode aset
    - asset_name: Nama aset
    - current_value: Nilai sekarang
    - total_invested: Total yang diinvestasikan
    - roi: Return on Investment (%)
    - cagr: Compound Annual Growth Rate (%)
    - unrealized_pnl: Profit/Loss yang belum direalisasi

    Fungsi: Menampilkan performa satu aset
    """

    asset_id: str = Field(..., description="Asset ID")
    symbol: str = Field(..., description="Asset symbol")
    asset_name: str = Field(..., description="Asset name")
    current_value: Decimal = Field(..., description="Current value")
    total_invested: Decimal = Field(..., description="Total invested")
    roi: Decimal = Field(..., description="Return on Investment (%)")
    cagr: Decimal | None = Field(None, description="Compound Annual Growth Rate (%)")
    unrealized_pnl: Decimal = Field(..., description="Unrealized Profit/Loss")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "asset_id": "123e4567-e89b-12d3-a456-426614174000",
                    "symbol": "BBCA.JK",
                    "asset_name": "Bank Central Asia",
                    "current_value": "875000",
                    "total_invested": "850000",
                    "roi": "2.94",
                    "cagr": "5.2",
                    "unrealized_pnl": "25000",
                }
            ]
        }
    }


class PerformanceResponse(BaseModel):
    """
    Schema untuk response performa semua aset

    Dipakai di: GET /api/v1/dashboard/performance

    Field:
    - performances: List performa per aset

    Fungsi: Menampilkan tabel performa semua aset di dashboard
    """

    performances: list[PerformanceItem] = Field(
        ..., description="Performance metrics per asset"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "performances": [
                        {
                            "asset_id": "123e4567-e89b-12d3-a456-426614174000",
                            "symbol": "BBCA.JK",
                            "asset_name": "Bank Central Asia",
                            "current_value": "875000",
                            "total_invested": "850000",
                            "roi": "2.94",
                            "cagr": "5.2",
                            "unrealized_pnl": "25000",
                        }
                    ]
                }
            ]
        }
    }


class WealthHistoryItem(BaseModel):
    """
    Schema untuk item riwayat kekayaan

    Field:
    - snapshot_date: Tanggal snapshot
    - total_value: Total kekayaan pada tanggal tersebut

    Fungsi: Satu titik di line chart riwayat kekayaan
    """

    snapshot_date: date = Field(..., description="Snapshot date")
    total_value: Decimal = Field(..., description="Total net worth on that date")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "snapshot_date": "2026-05-12",
                    "total_value": "150000000",
                }
            ]
        }
    }


class WealthHistoryResponse(BaseModel):
    """
    Schema untuk response riwayat kekayaan

    Dipakai di: GET /api/v1/dashboard/wealth-history?period=30d

    Field:
    - history: List riwayat kekayaan harian (untuk line chart)

    Fungsi: Menampilkan line chart pertumbuhan kekayaan di dashboard
    """

    history: list[WealthHistoryItem] = Field(
        ..., description="Wealth history over time"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "history": [
                        {"snapshot_date": "2026-05-01", "total_value": "145000000"},
                        {"snapshot_date": "2026-05-02", "total_value": "147000000"},
                        {"snapshot_date": "2026-05-12", "total_value": "150000000"},
                    ]
                }
            ]
        }
    }
