"""
Dashboard Service - Business logic untuk dashboard metrics

Fungsi file ini:
- get_net_worth: Hitung total net worth user (semua aset)
- get_allocation: Hitung breakdown alokasi per asset type
- get_performance: Hitung performance metrics per aset (ROI, P&L, dll)
- get_portfolio_summary: Gabungan semua metrics untuk dashboard

Performance optimization:
- Fetch semua harga aset secara PARALEL (asyncio.gather), bukan sequential
- get_portfolio_summary fetch data sekali, lalu reuse untuk net_worth/allocation/performance
- In-memory cache untuk summary endpoint (30 detik TTL) supaya reload page instant
- Setelah cache hit (< 5 menit), response time < 100ms
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Literal, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import UserAsset, WealthHistory
from app.services import price_service, calculator

# Fallback USD/IDR rate jika API gagal
FALLBACK_USD_IDR = Decimal("16000")

# In-memory cache untuk summary endpoint (per user, TTL 30 detik)
# Key: user_id (str), Value: (timestamp_seconds, summary_dict)
_SUMMARY_CACHE: Dict[str, Tuple[float, Dict]] = {}
SUMMARY_CACHE_TTL_SECONDS = 30

# In-memory cache untuk analytics endpoint (per user + period, TTL 5 menit)
# Key: user_id:period (str), Value: (timestamp_seconds, dict)
_ANALYTICS_CACHE: Dict[str, Tuple[float, Dict]] = {}
ANALYTICS_CACHE_TTL_SECONDS = 300


def invalidate_summary_cache(user_id: str | None = None) -> None:
    """
    Invalidate summary cache. Dipanggil saat asset/transaction berubah.

    Args:
        user_id: Jika None, clear semua. Jika ada, clear user tertentu saja.
    """
    if user_id is None:
        _SUMMARY_CACHE.clear()
    else:
        _SUMMARY_CACHE.pop(user_id, None)


def invalidate_analytics_cache(user_id: str | None = None) -> None:
    """
    Invalidate analytics cache. Dipanggil saat asset/transaction berubah.

    Args:
        user_id: Jika None, clear semua. Jika ada, clear user tertentu saja.
    """
    if user_id is None:
        _ANALYTICS_CACHE.clear()
    else:
        # Clear semua period untuk user ini
        keys_to_delete = [
            k for k in _ANALYTICS_CACHE if k.startswith(f"{user_id}:")
        ]
        for key in keys_to_delete:
            del _ANALYTICS_CACHE[key]


# ─────────────────────────────────────────────────────────────
# Currency conversion helpers
# ─────────────────────────────────────────────────────────────


async def get_usd_idr_rate(db: AsyncSession) -> Decimal:
    """Get kurs USD/IDR — pakai cache atau fetch baru."""
    try:
        cache = await price_service.get_price_from_cache(db, "IDR=X")
        if await price_service.is_cache_valid(cache):
            return cache.price
        rate = await price_service.fetch_usd_idr_rate()
        if rate:
            await price_service.update_price_cache(
                db, "IDR=X", rate, "yfinance", "forex"
            )
            return rate
    except Exception as e:
        print(f"Failed to get USD/IDR rate: {e}")
    return FALLBACK_USD_IDR


def to_idr(value: Decimal, currency: str, usd_idr_rate: Decimal) -> Decimal:
    """Konversi nilai ke IDR berdasarkan currency aset."""
    if currency == "IDR":
        return value
    if currency == "USD":
        return value * usd_idr_rate
    return value * usd_idr_rate  # fallback untuk EUR/SGD/dll


# ─────────────────────────────────────────────────────────────
# Internal: fetch all asset prices in parallel
# ─────────────────────────────────────────────────────────────


async def _fetch_assets_with_prices(
    db: AsyncSession,
    user_id: str,
) -> Tuple[List[UserAsset], Dict[str, Decimal], Decimal]:
    """
    Fetch semua aset user + harga terkininya (PARALLEL) + USD/IDR rate.

    Optimization: pakai asyncio.gather agar semua API call jalan bersamaan.
    Untuk 5 asset: dari ~10 detik (sequential) jadi ~2 detik (parallel).

    Returns:
        Tuple (assets, prices_by_id, usd_idr_rate)
    """
    # 1. Get assets dari DB
    result = await db.execute(
        select(UserAsset)
        .where(UserAsset.user_id == user_id)
        .where(UserAsset.is_active == True)
    )
    assets = list(result.scalars().all())

    if not assets:
        return [], {}, FALLBACK_USD_IDR

    async def fetch_rate() -> Decimal:
        async with async_session() as price_db:
            try:
                return await get_usd_idr_rate(price_db)
            except Exception:
                await price_db.rollback()
                raise

    async def fetch_price(asset: UserAsset) -> Decimal | None:
        async with async_session() as price_db:
            try:
                return await price_service.get_price(
                    price_db,
                    asset.symbol,
                    asset.asset_type,
                )
            except Exception:
                await price_db.rollback()
                raise

    # 2. Fetch USD/IDR rate + semua asset prices PARALLEL
    rate_task = fetch_rate()
    price_tasks = [fetch_price(asset) for asset in assets]
        _build_asset_performance_series(
            db,
            asset,
            prices[str(asset.id)],
            rate,
            period,
            total_idr,
            total_pnl_idr,
        )
        for asset in priced_assets
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    asset_series = [result for result in results if not isinstance(result, Exception)]
    asset_series.sort(key=lambda x: Decimal(x["current_value_idr"]), reverse=True)

    winners = sorted(asset_series, key=lambda x: Decimal(x["roi"]), reverse=True)[:5]
    losers = sorted(asset_series, key=lambda x: Decimal(x["roi"]))[:5]

    return {
        "period": period,
        "currency": "IDR",
        "portfolio": portfolio,
        "assets": asset_series,
        "movers": {
            "winners": winners,
            "losers": losers,
        },
        "summary": {
            "total_invested": str(total_invested_idr),
            "current_value": str(total_idr),
            "total_unrealized_pnl": str(total_pnl_idr),
            "average_roi": str(avg_roi),
            "asset_count": len(asset_series),
        },
        "metadata": {
            "portfolio_source": "wealth_history_plus_current_snapshot",
            "asset_source": "market_price_history",
            "supports": [
                "portfolio_line_chart",
                "asset_position_performance_chart",
                "market_performance_chart",
                "winners_losers",
                "allocation_vs_return",
            ],
        },
    }


async def get_portfolio_summary(db: AsyncSession, user_id: str) -> Dict:
    """
    Gabungan semua metrics untuk dashboard (one-stop endpoint).

    Optimization layers:
    1. In-memory cache (30 detik TTL) → response < 5ms kalau hit
    2. Fetch assets+prices SATU KALI, derive ke 3 section
    3. Price cache di DB (5 menit TTL) dengan stale-while-revalidate

    Cache di-invalidate otomatis saat user create/update/delete asset atau transaction.
    """
    # Layer 1: Check in-memory cache
    cached = _SUMMARY_CACHE.get(user_id)
    if cached is not None:
        ts, data = cached
        if time.time() - ts < SUMMARY_CACHE_TTL_SECONDS:
            return data

    # Build fresh
    assets, prices, rate = await _fetch_assets_with_prices(db, user_id)
    metrics = [
        _build_asset_metric(a, prices[str(a.id)], rate)
        for a in assets
        if str(a.id) in prices
    ]

    breakdown, total_idr, total_invested_idr, total_pnl_idr, avg_roi = _aggregate(
        metrics
    )

    # Build net_worth section
    net_worth = {
        "total": str(total_idr),
        "breakdown": {k: str(v) for k, v in breakdown.items()},
        "change_24h": None,
        "currency": "IDR",
    }

    # Build allocation section
    allocation_pct = calculator.calculate_allocation(breakdown)
    allocations = [
        {
            "asset_type": atype,
            "value": str(value),
            "percentage": str(allocation_pct[atype]),
        }
        for atype, value in breakdown.items()
    ]
    allocations.sort(key=lambda x: Decimal(x["value"]), reverse=True)
    allocation = {"allocations": allocations, "total": str(total_idr)}

    # Build performance section (sorted)
    sorted_metrics = sorted(
        metrics, key=lambda x: Decimal(x["current_value_idr"]), reverse=True
    )
    performance = {
        "assets": sorted_metrics,
        "summary": {
            "total_invested": str(total_invested_idr),
            "current_value": str(total_idr),
            "total_unrealized_pnl": str(total_pnl_idr),
            "average_roi": str(avg_roi),
        },
    }

    summary = {
        "net_worth": net_worth,
        "allocation": allocation,
        "performance": performance,
    }

    # Save to memory cache
    _SUMMARY_CACHE[user_id] = (time.time(), summary)

    return summary
