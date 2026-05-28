"""
Prices Router - Endpoints untuk fetch harga aset

Endpoints:
- GET /api/v1/prices/{symbol} - Get harga satu aset
- GET /api/v1/prices/search - Search crypto symbols

Fungsi:
- User bisa cek harga aset sebelum tambah transaksi
- User bisa search crypto symbol yang valid
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import price_service
from app.utils.security import get_current_user
from app.models.user import User

router = APIRouter(tags=["Prices"])


@router.get("/search/crypto")
async def search_crypto(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Search crypto symbols dari CoinGecko

    Args:
        q: Search query (bitcoin, eth, bnb, dll)
        limit: Max results (default 10, max 50)

    Returns:
        {
            "query": "bitcoin",
            "results": [
                {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
                {"id": "bitcoin-cash", "symbol": "bch", "name": "Bitcoin Cash"},
                ...
            ]
        }

    Examples:
        GET /api/v1/prices/search/crypto?q=bitcoin
        GET /api/v1/prices/search/crypto?q=eth&limit=5
    """
    _ = current_user
    results = await price_service.search_crypto_symbols(q, limit)

    return {
        "query": q,
        "results": results,
    }



@router.get("/{symbol}")
async def get_asset_price(
    symbol: str,
    asset_type: Literal[
        "stock_id",
        "stock_us",
        "crypto",
        "gold",
        "mutual_fund",
        "bond",
        "cash",
        "property",
    ] = Query(..., description="Asset type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get harga terkini untuk satu aset

    Args:
        symbol: Asset symbol (BBCA.JK, bitcoin, GC=F, dll)
        asset_type: Jenis aset (stock_id, crypto, dll)

    Returns:
        {
            "symbol": "BBCA.JK",
            "price": "8750",
            "asset_type": "stock_id",
            "cached": false
        }

    Examples:
        GET /api/v1/prices/BBCA.JK?asset_type=stock_id
        GET /api/v1/prices/bitcoin?asset_type=crypto
        GET /api/v1/prices/GC=F?asset_type=gold
    """
    try:
        price = await price_service.get_price(db, symbol, asset_type)

        if price is None:
            raise HTTPException(
                status_code=404,
                detail=f"Price not found for {symbol}. Check symbol or try again later.",
            )

        # Check if from cache
        cache = await price_service.get_price_from_cache(db, symbol)
        is_cached = await price_service.is_cache_valid(cache)

        return {
            "symbol": symbol.upper(),
            "price": str(price),
            "asset_type": asset_type,
            "cached": is_cached,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in get_asset_price: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


