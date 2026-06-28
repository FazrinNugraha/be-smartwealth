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

    results = await asyncio.gather(rate_task, *price_tasks, return_exceptions=True)

    usd_idr_rate = (
        results[0] if not isinstance(results[0], Exception) else FALLBACK_USD_IDR
    )
    prices_by_id = {}
    for asset, price in zip(assets, results[1:]):
        if isinstance(price, Exception) or price is None:
            continue
        prices_by_id[str(asset.id)] = price

    return assets, prices_by_id, usd_idr_rate


def _build_asset_metric(
    asset: UserAsset,
    current_price: Decimal,
    usd_idr_rate: Decimal,
) -> Dict:
    """Build single asset metric dict (native currency + IDR for summary)."""
    currency = getattr(asset, "currency", None) or "IDR"

    total_invested_native = calculator.calculate_total_invested(
        asset.quantity, asset.avg_buy_price
    )
    current_value_native = calculator.calculate_current_value(
        asset.quantity, current_price
    )
    unrealized_pnl_native = calculator.calculate_unrealized_pnl(
        asset.quantity, asset.avg_buy_price, current_price
    )
    roi = calculator.calculate_roi(current_value_native, total_invested_native)

    return {
        "asset_id": str(asset.id),
        "symbol": asset.symbol,
        "asset_name": asset.asset_name,
        "asset_type": asset.asset_type,
        "currency": currency,
        "quantity": str(asset.quantity),
        "avg_buy_price": str(asset.avg_buy_price),
        "current_price": str(current_price),
        "total_invested": str(total_invested_native),
        "current_value": str(current_value_native),
        "unrealized_pnl": str(unrealized_pnl_native),
        "total_invested_idr": str(
            to_idr(total_invested_native, currency, usd_idr_rate)
        ),
        "current_value_idr": str(to_idr(current_value_native, currency, usd_idr_rate)),
        "unrealized_pnl_idr": str(
            to_idr(unrealized_pnl_native, currency, usd_idr_rate)
        ),
        "roi": str(roi),
    }


def _aggregate(
    metrics: List[Dict],
) -> Tuple[Dict[str, Decimal], Decimal, Decimal, Decimal, Decimal]:
    """
    Aggregate metrics ke breakdown by type + summary totals (semua dalam IDR).

    Returns:
        (breakdown_by_type, total_idr, total_invested_idr, total_pnl_idr, average_roi)
    """
    breakdown: Dict[str, Decimal] = {}
    total_idr = Decimal("0")
    total_invested_idr = Decimal("0")
    total_pnl_idr = Decimal("0")

    for m in metrics:
        cv_idr = Decimal(m["current_value_idr"])
        ti_idr = Decimal(m["total_invested_idr"])
        pnl_idr = Decimal(m["unrealized_pnl_idr"])

        atype = m["asset_type"]
        breakdown[atype] = breakdown.get(atype, Decimal("0")) + cv_idr

        total_idr += cv_idr
        total_invested_idr += ti_idr
        total_pnl_idr += pnl_idr

    average_roi = Decimal("0")
    if total_invested_idr > 0:
        average_roi = calculator.calculate_roi(total_idr, total_invested_idr)

    return breakdown, total_idr, total_invested_idr, total_pnl_idr, average_roi


def _period_start_date(period: str):
    today = datetime.now(timezone.utc).date()
    if period == "7d":
        return today - timedelta(days=7)
    if period == "30d":
        return today - timedelta(days=30)
    if period == "90d":
        return today - timedelta(days=90)
    if period == "1y":
        return today - timedelta(days=365)
    return None


def _percentage_change(value: Decimal, baseline: Decimal) -> Decimal | None:
    if baseline <= 0:
        return None
    return ((value - baseline) / baseline * 100).quantize(Decimal("0.01"))


async def _build_portfolio_history(
    db: AsyncSession,
    user_id: str,
    period: str,
    current_total_idr: Decimal,
) -> Dict:
    """Build total portfolio chart series from wealth snapshots plus current value."""
    start_date = _period_start_date(period)

    query = select(WealthHistory).where(WealthHistory.user_id == user_id)
    if start_date:
        query = query.where(WealthHistory.snapshot_date >= start_date)
    query = query.order_by(WealthHistory.snapshot_date.asc())

    result = await db.execute(query)
    history = list(result.scalars().all())

    data = [
        {
            "date": record.snapshot_date.isoformat(),
            "total_value": record.total_value,
        }
        for record in history
    ]

    today = datetime.now(timezone.utc).date().isoformat()
    if current_total_idr > 0:
        if data and data[-1]["date"] == today:
            data[-1]["total_value"] = current_total_idr
        else:
            data.append({"date": today, "total_value": current_total_idr})

    start_value = data[0]["total_value"] if data else None
    end_value = data[-1]["total_value"] if data else None
    change = (
        end_value - start_value
        if start_value is not None and end_value is not None
        else None
    )
    change_percentage = (
        _percentage_change(end_value, start_value)
        if start_value is not None and end_value is not None
        else None
    )

    baseline = start_value if start_value is not None else Decimal("0")
    chart_data = []
    for point in data:
        return_percentage = (
            _percentage_change(point["total_value"], baseline) if baseline > 0 else None
        )
        chart_data.append(
            {
                "date": point["date"],
                "total_value": str(point["total_value"]),
                "return_percentage": (
                    str(return_percentage) if return_percentage is not None else None
                ),
            }
        )

    return {
        "data": chart_data,
        "start_value": str(start_value) if start_value is not None else None,
        "end_value": str(end_value) if end_value is not None else None,
        "change": str(change) if change is not None else None,
        "change_percentage": (
            str(change_percentage) if change_percentage is not None else None
        ),
    }


async def _build_asset_performance_series(
    db: AsyncSession,
    asset: UserAsset,
    current_price: Decimal,
    usd_idr_rate: Decimal,
    period: Literal["7d", "30d", "90d", "1y", "all"],
    portfolio_total_idr: Decimal,
    total_pnl_idr: Decimal,
) -> Dict:
    """Build per-asset chart series based on historical market prices."""
    metric = _build_asset_metric(asset, current_price, usd_idr_rate)
    currency = metric["currency"]

    price_history = await price_service.get_price_history(
        db,
        asset.symbol,
        asset.asset_type,
        period,
        usd_idr_rate=usd_idr_rate,
    )

    today = datetime.now(timezone.utc).date().isoformat()
    if not price_history:
        price_history = [{"date": today, "price": current_price}]
    elif price_history[-1]["date"] == today:
        price_history[-1]["price"] = current_price
    else:
        price_history.append({"date": today, "price": current_price})

    baseline_price = price_history[0]["price"]
    avg_buy_price = asset.avg_buy_price
    total_invested_native = Decimal(metric["total_invested"])
    data = []

    for point in price_history:
        value_native = calculator.calculate_current_value(
            asset.quantity, point["price"]
        )
        value_idr = to_idr(value_native, currency, usd_idr_rate)
        roi = calculator.calculate_roi(value_native, total_invested_native)
        period_return = _percentage_change(point["price"], baseline_price)
        position_return = _percentage_change(point["price"], avg_buy_price)

        data.append(
            {
                "date": point["date"],
                "price": str(point["price"]),
                "current_value": str(value_native),
                "current_value_idr": str(value_idr),
                "roi": str(roi),
                "period_return_percentage": (
                    str(period_return) if period_return is not None else None
                ),
                "position_return_percentage": (
                    str(position_return) if position_return is not None else None
                ),
            }
        )

    daily_change = None
    if len(price_history) >= 2:
        daily_change = _percentage_change(
            price_history[-1]["price"], price_history[-2]["price"]
        )

    period_return = _percentage_change(price_history[-1]["price"], baseline_price)
    current_value_idr = Decimal(metric["current_value_idr"])
    unrealized_pnl_idr = Decimal(metric["unrealized_pnl_idr"])

    weight_percentage = Decimal("0")
    if portfolio_total_idr > 0:
        weight_percentage = (current_value_idr / portfolio_total_idr * 100).quantize(
            Decimal("0.01")
        )

    contribution_percentage = None
    if total_pnl_idr != 0:
        contribution_percentage = (unrealized_pnl_idr / total_pnl_idr * 100).quantize(
            Decimal("0.01")
        )

    return {
        **metric,
        "weight_percentage": str(weight_percentage),
        "daily_change_percentage": (
            str(daily_change) if daily_change is not None else None
        ),
        "period_return_percentage": (
            str(period_return) if period_return is not None else None
        ),
        "position_return_percentage": metric["roi"],
        "contribution_percentage": (
            str(contribution_percentage)
            if contribution_percentage is not None
            else None
        ),
        "data": data,
    }


# ─────────────────────────────────────────────────────────────
# Public API: standalone endpoints
# ─────────────────────────────────────────────────────────────


async def get_net_worth(db: AsyncSession, user_id: str) -> Dict:
    """Hitung total net worth user (nilai semua aset dalam IDR)."""
    assets, prices, rate = await _fetch_assets_with_prices(db, user_id)
    metrics = [
        _build_asset_metric(a, prices[str(a.id)], rate)
        for a in assets
        if str(a.id) in prices
    ]

    breakdown, total, *_ = _aggregate(metrics)

    return {
        "total": str(total),
        "breakdown": {k: str(v) for k, v in breakdown.items()},
        "change_24h": None,  # TODO: butuh historical data
        "currency": "IDR",
    }


async def get_allocation(db: AsyncSession, user_id: str) -> Dict:
    """Hitung breakdown alokasi per asset type (dalam persentase)."""
    assets, prices, rate = await _fetch_assets_with_prices(db, user_id)
    metrics = [
        _build_asset_metric(a, prices[str(a.id)], rate)
        for a in assets
        if str(a.id) in prices
    ]

    breakdown, total, *_ = _aggregate(metrics)

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

    return {"allocations": allocations, "total": str(total)}


async def get_performance(db: AsyncSession, user_id: str) -> Dict:
    """Hitung performance metrics untuk semua aset user."""
    assets, prices, rate = await _fetch_assets_with_prices(db, user_id)
    metrics = [
        _build_asset_metric(a, prices[str(a.id)], rate)
        for a in assets
        if str(a.id) in prices
    ]

    _, total_idr, total_invested_idr, total_pnl_idr, avg_roi = _aggregate(metrics)

    metrics.sort(key=lambda x: Decimal(x["current_value_idr"]), reverse=True)

    return {
        "assets": metrics,
        "summary": {
            "total_invested": str(total_invested_idr),
            "current_value": str(total_idr),
            "total_unrealized_pnl": str(total_pnl_idr),
            "average_roi": str(avg_roi),
        },
    }


# ─────────────────────────────────────────────────────────────
# Public API: combined endpoint (FAST — fetch sekali, reuse)
# ─────────────────────────────────────────────────────────────


async def get_performance_analytics(
    db: AsyncSession,
    user_id: str,
    period: Literal["7d", "30d", "90d", "1y", "all"] = "30d",
) -> Dict:
    """
    Build chart-ready performance analytics for the dashboard.

    This endpoint powers the interactive performance UI:
    - portfolio line chart from wealth snapshots
    - multi-line asset performance chart from market price history
    - winners and losers lists for quick scanning
    """
    # ── Layer 1: Check in-memory cache ──────────────────────
    cache_key = f"{user_id}:{period}"
    cached = _ANALYTICS_CACHE.get(cache_key)
    if cached is not None:
        ts, data = cached
        if time.time() - ts < ANALYTICS_CACHE_TTL_SECONDS:
            return data  # Cache hit

    # ── Layer 2: Build fresh data ────────────────────────────
    assets, prices, rate = await _fetch_assets_with_prices(db, user_id)
    priced_assets = [asset for asset in assets if str(asset.id) in prices]
    metrics = [_build_asset_metric(a, prices[str(a.id)], rate) for a in priced_assets]

    _, total_idr, total_invested_idr, total_pnl_idr, avg_roi = _aggregate(metrics)
    portfolio = await _build_portfolio_history(db, user_id, period, total_idr)

    tasks = [
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

    result = {
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
            "cached_at": time.time(),
        },
    }

    # ── Save to cache ────────────────────────────────────────
    _ANALYTICS_CACHE[cache_key] = (time.time(), result)
    return result


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
