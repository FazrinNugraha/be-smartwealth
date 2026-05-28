"""
Schemas package - Pydantic request/response models

Fungsi file ini:
- Export semua schemas agar mudah di-import
- Contoh: from app.schemas import RegisterRequest, UserResponse

Schemas yang tersedia:
- auth: RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest, GoogleAuthRequest
- user: UserResponse, UserUpdate
- asset: AssetCreate, AssetResponse, AssetUpdate
- transaction: TransactionCreate, TransactionResponse
- dashboard: NetWorthResponse, AllocationResponse, PerformanceResponse, WealthHistoryResponse
- insight: InsightResponse
"""

# Auth schemas
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    GoogleAuthRequest,
)

# User schemas
from app.schemas.user import UserResponse, UserUpdate

# Asset schemas
from app.schemas.asset import AssetCreate, AssetResponse, AssetUpdate

# Transaction schemas
from app.schemas.transaction import TransactionCreate, TransactionResponse

# Dashboard schemas
from app.schemas.dashboard import (
    NetWorthResponse,
    AllocationResponse,
    AllocationItem,
    PerformanceResponse,
    PerformanceItem,
    WealthHistoryResponse,
    WealthHistoryItem,
)

# Insight schemas
from app.schemas.insight import InsightResponse

# Prediction schemas
from app.schemas.prediction import (
    PredictionChangeRange,
    PredictionPriceRange,
    StockPredictionResponse,
)

__all__ = [
    # Auth
    "RegisterRequest",
    "LoginRequest",
    "TokenResponse",
    "RefreshTokenRequest",
    "GoogleAuthRequest",
    # User
    "UserResponse",
    "UserUpdate",
    # Asset
    "AssetCreate",
    "AssetResponse",
    "AssetUpdate",
    # Transaction
    "TransactionCreate",
    "TransactionResponse",
    # Dashboard
    "NetWorthResponse",
    "AllocationResponse",
    "AllocationItem",
    "PerformanceResponse",
    "PerformanceItem",
    "WealthHistoryResponse",
    "WealthHistoryItem",
    # Insight
    "InsightResponse",
    # Prediction
    "PredictionChangeRange",
    "PredictionPriceRange",
    "StockPredictionResponse",
]
