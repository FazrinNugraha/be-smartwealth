"""
Dashboard Router - API endpoints untuk dashboard metrics

Endpoints:
- GET /dashboard/net-worth - Total net worth user
- GET /dashboard/allocation - Breakdown alokasi per asset type
- GET /dashboard/performance - Performance metrics per aset
- GET /dashboard/summary - Gabungan semua metrics (one-stop)
- GET /dashboard/wealth-history - Historical net worth data (untuk grafik)

Semua endpoints require authentication.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.wealth import WealthHistory
from app.services import dashboard_service
from app.utils.security import get_current_user

router = APIRouter(tags=["Dashboard"])


@router.get("/net-worth")
async def get_net_worth(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get total net worth user (nilai semua aset)

    Returns:
        {
            "total": "1250000.00",
            "breakdown": {
                "crypto": "500000.00",
                "stock_id": "450000.00",
                "cash": "300000.00"
            },
            "change_24h": null,
            "currency": "IDR"
        }

    Note:
        - Total = sum of all active assets × current price
        - Breakdown = total per asset type
        - change_24h = TODO (butuh historical data)

    Examples:
        GET /api/v1/dashboard/net-worth
    """
    return await dashboard_service.get_net_worth(db, str(current_user.id))


@router.get("/allocation")
async def get_allocation(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get breakdown alokasi per asset type (dalam persentase)

    Returns:
        {
            "allocations": [
                {
                    "asset_type": "crypto",
                    "value": "500000.00",
                    "percentage": "40.00"
                },
                {
                    "asset_type": "stock_id",
                    "value": "450000.00",
                    "percentage": "36.00"
                }
            ],
            "total": "1250000.00"
        }

    Note:
        - Sorted by value (descending)
        - Percentages sum to 100%
        - Useful for pie chart visualization

    Examples:
        GET /api/v1/dashboard/allocation
    """
    return await dashboard_service.get_allocation(db, str(current_user.id))


@router.get("/performance")
async def get_performance(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get performance metrics untuk semua aset user

    Returns:
        {
            "assets": [
                {
                    "asset_id": "uuid",
                    "symbol": "BBCA.JK",
                    "asset_name": "Bank BCA",
                    "asset_type": "stock_id",
                    "quantity": "100.00",
                    "avg_buy_price": "8500.00",
                    "current_price": "9000.00",
                    "total_invested": "850000.00",
                    "current_value": "900000.00",
                    "unrealized_pnl": "50000.00",
                    "roi": "5.88"
                }
            ],
            "summary": {
                "total_invested": "1200000.00",
                "current_value": "1250000.00",
                "total_unrealized_pnl": "50000.00",
                "average_roi": "4.17"
            }
        }

    Note:
        - Assets sorted by current value (descending)
        - ROI = (current_value - total_invested) / total_invested × 100
        - Unrealized P&L = (current_price - avg_buy_price) × quantity
        - Summary = aggregated metrics for all assets

    Examples:
        GET /api/v1/dashboard/performance
    """
    return await dashboard_service.get_performance(db, str(current_user.id))


@router.get("/performance-analytics")
async def get_performance_analytics(
    period: Literal["7d", "30d", "90d", "1y", "all"] = Query(
        "30d", description="Time period for performance chart data"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get chart-ready performance analytics for the interactive dashboard.

    Returns:
        {
            "period": "30d",
            "currency": "IDR",
            "portfolio": {
                "data": [
                    {
                        "date": "2026-05-12",
                        "total_value": "1250000.00",
                        "return_percentage": "2.50"
                    }
                ],
                "change": "250000.00",
                "change_percentage": "25.00"
            },
            "assets": [
                {
                    "symbol": "BBCA.JK",
                    "roi": "5.88",
                    "daily_change_percentage": "0.64",
                    "period_return_percentage": "3.20",
                    "weight_percentage": "40.00",
                    "data": [
                        {
                            "date": "2026-05-12",
                            "price": "9000.00",
                            "current_value_idr": "900000.00",
                            "roi": "5.88"
                        }
                    ]
                }
            ],
            "movers": {
                "winners": [...],
                "losers": [...]
            }
        }

    Note:
        - Designed for multi-line charts, winners/losers, and return badges.
        - Portfolio history uses saved wealth snapshots plus current value.
        - Asset history uses market data APIs where supported.
    """
    return await dashboard_service.get_performance_analytics(
        db,
        str(current_user.id),
        period,
    )


@router.get("/summary")
async def get_portfolio_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get gabungan semua metrics untuk dashboard (one-stop endpoint)

    Returns:
        {
            "net_worth": {
                "total": "1250000.00",
                "breakdown": {...},
                "change_24h": null,
                "currency": "IDR"
            },
            "allocation": {
                "allocations": [...],
                "total": "1250000.00"
            },
            "performance": {
                "assets": [...],
                "summary": {...}
            }
        }

    Note:
        - Combines /net-worth, /allocation, and /performance
        - More efficient than calling 3 endpoints separately
        - Recommended for dashboard initial load

    Examples:
        GET /api/v1/dashboard/summary
    """
    return await dashboard_service.get_portfolio_summary(db, str(current_user.id))


@router.get("/wealth-history")
async def get_wealth_history(
    period: Literal["7d", "30d", "90d", "1y", "all"] = Query(
        "30d", description="Time period for historical data"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get historical net worth data untuk grafik

    Args:
        period: Time period (7d, 30d, 90d, 1y, all)

    Returns:
        {
            "period": "30d",
            "data": [
                {
                    "date": "2026-04-12",
                    "total_value": "1000000.00"
                },
                {
                    "date": "2026-04-13",
                    "total_value": "1050000.00"
                }
            ],
            "start_value": "1000000.00",
            "end_value": "1250000.00",
            "change": "250000.00",
            "change_percentage": "25.00"
        }

    Note:
        - Data sorted by date (ascending)
        - Useful for line chart visualization
        - If no data, returns empty array

    Examples:
        GET /api/v1/dashboard/wealth-history?period=7d
        GET /api/v1/dashboard/wealth-history?period=30d
        GET /api/v1/dashboard/wealth-history?period=all
    """
    # Calculate date range based on period
    today = datetime.now(timezone.utc).date()

    if period == "7d":
        start_date = today - timedelta(days=7)
    elif period == "30d":
        start_date = today - timedelta(days=30)
    elif period == "90d":
        start_date = today - timedelta(days=90)
    elif period == "1y":
        start_date = today - timedelta(days=365)
    else:  # all
        start_date = None

    # Query wealth history
    query = select(WealthHistory).where(WealthHistory.user_id == current_user.id)

    if start_date:
        query = query.where(WealthHistory.snapshot_date >= start_date)

    query = query.order_by(WealthHistory.snapshot_date.asc())

    result = await db.execute(query)
    history = result.scalars().all()

    # Format response
    data = [
        {
            "date": str(record.snapshot_date),
            "total_value": str(record.total_value),
        }
        for record in history
    ]

    # Calculate change
    start_value = None
    end_value = None
    change = None
    change_percentage = None

    if len(data) > 0:
        from decimal import Decimal

        start_value = Decimal(data[0]["total_value"])
        end_value = Decimal(data[-1]["total_value"])
        change = end_value - start_value

        if start_value > 0:
            change_percentage = (change / start_value) * 100
            change_percentage = change_percentage.quantize(Decimal("0.01"))

    return {
        "period": period,
        "data": data,
        "start_value": str(start_value) if start_value else None,
        "end_value": str(end_value) if end_value else None,
        "change": str(change) if change else None,
        "change_percentage": str(change_percentage) if change_percentage else None,
    }
