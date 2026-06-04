"""
Insights Router - API endpoints untuk portfolio insights

Endpoints:
- GET /insights - Get rule-based portfolio insights
- GET /insights/ai - Get cached AI-powered insights
- POST /insights/ai/refresh - Force refresh AI insights

Semua endpoints require authentication.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services import insight_engine, ai_service
from app.utils.security import get_current_user

router = APIRouter(tags=["Insights"])


@router.get("/")
async def get_insights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get portfolio insights (rule-based analysis)

    Returns:
        {
            "health_score": 65,
            "health_status": "fair",
            "summary": "Portfolio Anda cukup baik...",
            "insights": [
                {
                    "type": "warning",
                    "category": "concentration_risk",
                    "title": "Concentration Risk Tinggi",
                    "message": "Bitcoin menyumbang 65%...",
                    "recommendation": "Kurangi Bitcoin...",
                    "severity": "high",
                    "affected_assets": ["bitcoin"]
                }
            ],
            "disclaimer": "Insights ini bersifat edukatif..."
        }

    Note:
        - Rule-based analysis (instant, no AI)
        - Health score: 0-100 (higher is better)
        - Health status: excellent/good/fair/poor/critical
        - Insights sorted by severity (high → low)

    Examples:
        GET /api/v1/insights
    """
    return await insight_engine.get_rule_based_insights(db, current_user)


@router.get("/ai")
async def get_ai_insights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Get cached AI-powered portfolio insights

    Returns:
        {
            "summary": "Overall summary",
            "detailed_analysis": {
                "strengths": [...],
                "weaknesses": [...],
                "opportunities": [...],
                "threats": [...]
            },
            "action_plan": [...],
            "risk_assessment": "...",
            "source": "cache" | "empty"
        }

    Note:
        - Does not call Gemini or generate a fresh analysis
        - Use POST /ai/refresh when the user explicitly clicks Generate
        - Cached data expires after 6 hours

    Examples:
        GET /api/v1/insights/ai
    """
    ai_insights = await ai_service.get_cached_gemini_insights(db, current_user)

    if ai_insights is None:
        return {
            "summary": "Belum ada AI insights. Klik Generate untuk membuat analisis Gemini.",
            "source": "empty",
        }

    return ai_insights


@router.post("/ai/refresh")
async def refresh_ai_insights(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Force refresh AI insights (bypass cache)

    Returns:
        Same as GET /ai but always fresh from Gemini

    Note:
        - Bypasses cache
        - Regenerates insights from Gemini
        - Updates cache with new insights
        - Use sparingly (API rate limits)

    Examples:
        POST /api/v1/insights/ai/refresh
    """
    ai_insights = await ai_service.get_gemini_insights(
        db, current_user, force_refresh=True
    )

    if ai_insights is None:
        return {
            "summary": "AI insights tidak tersedia saat ini.",
            "source": "unavailable",
        }

    return ai_insights
