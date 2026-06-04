"""
AI Service - Gemini AI integration untuk portfolio insights

Fungsi file ini:
- Build portfolio context untuk AI
- Call Gemini API dengan prompt
- Parse & validate AI response
- Caching dengan TTL 6 jam
- Fallback ke rule-based jika API error

Note:
- Gemini 2.0 Flash Experimental gratis untuk usage wajar
- Response time: 2-5 detik
- Cache di tabel insight_cache
"""

import json
import re
import traceback
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Optional

try:
    from google import genai

    GENAI_SDK = "google-genai"
except ImportError:
    try:
        import google.generativeai as genai

        GENAI_SDK = "google-generativeai"
    except ImportError:
        print("[WARNING] Gemini SDK not installed. AI insights will be unavailable.")
        genai = None
        GENAI_SDK = None

GENAI_AVAILABLE = genai is not None

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, InsightCache
from app.services import dashboard_service

# Configure Gemini API (lazy initialization)
_client = None


def get_client():
    """Get or initialize Gemini client"""
    global _client

    if not GENAI_AVAILABLE:
        print("[GEMINI AI] google-generativeai package not installed")
        return None

    if _client is None:
        if not settings.GEMINI_API_KEY:
            print("[GEMINI AI] API key not configured")
            return None

        try:
            print(f"[GEMINI AI] Initializing client with SDK: {GENAI_SDK}")
            if GENAI_SDK == "google-genai":
                _client = genai.Client(api_key=settings.GEMINI_API_KEY)
            else:
                genai.configure(api_key=settings.GEMINI_API_KEY)
                _client = genai.GenerativeModel("gemini-2.5-flash")
            print("[GEMINI AI] Client initialized successfully")
        except Exception as e:
            print(f"[GEMINI AI] Failed to initialize client: {e}")
            traceback.print_exc()
            return None

    return _client


async def get_gemini_insights(
    db: AsyncSession,
    user: User,
    force_refresh: bool = False,
) -> Optional[Dict]:
    """
    Get AI-powered insights dari Gemini

    Args:
        db: Database session
        user: User object
        force_refresh: Force regenerate (bypass cache)

    Returns:
        {
            "summary": "...",
            "detailed_analysis": {...},
            "action_plan": [...],
            "risk_assessment": "...",
            "source": "cache" | "fresh" | "unavailable"
        }

    Note:
        - Check cache first (TTL 6 jam)
        - If cache valid → return cache
        - If cache expired or force_refresh → call Gemini
        - If API error → return None (fallback ke rule-based)
    """
    # Check if Gemini API is configured
    client = get_client()
    if not client:
        return {
            "summary": "AI insights tidak tersedia. Silakan konfigurasi GEMINI_API_KEY.",
            "source": "unavailable",
        }

    # Check cache (jika tidak force refresh)
    if not force_refresh:
        cached = await get_cached_insights(db, user.id)
        if cached:
            return {
                **cached["insight_data"],
                "source": "cache",
                "cached_at": str(cached["created_at"]),
            }

    # Generate fresh insights
    try:
        # Build context
        context = await build_portfolio_context(db, user)

        # Call Gemini API
        prompt = build_gemini_prompt(context)

        # Use Gemini 2.5 Flash model
        if GENAI_SDK == "google-genai":
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
        else:
            response = client.generate_content(prompt)

        # Parse response
        insights = parse_gemini_response(response.text)

        # Save to cache
        await save_to_cache(db, user.id, insights)

        return {
            **insights,
            "source": "fresh",
        }

    except Exception as e:
        print(f"[GEMINI AI] Error: {e}")
        traceback.print_exc()
        return None


async def get_cached_gemini_insights(
    db: AsyncSession,
    user: User,
) -> Optional[Dict]:
    """
    Get cached Gemini insights without generating a fresh response.
    """
    cached = await get_cached_insights(db, user.id)
    if not cached:
        return None

    return {
        **cached["insight_data"],
        "source": "cache",
        "cached_at": str(cached["created_at"]),
    }


async def build_portfolio_context(
    db: AsyncSession,
    user: User,
) -> Dict:
    """
    Build portfolio context untuk Gemini AI

    Returns:
        {
            "user": {...},
            "portfolio": {...},
            "performance": {...},
            "allocation": {...}
        }
    """
    # Get portfolio data
    performance = await dashboard_service.get_performance(db, str(user.id))
    allocation = await dashboard_service.get_allocation(db, str(user.id))

    return {
        "user": {
            "full_name": user.full_name,
            "email": user.email,
            "risk_profile": user.risk_profile or "moderate",
            "default_currency": user.default_currency or "IDR",
        },
        "portfolio": {
            "total_value": performance["summary"]["current_value"],
            "total_invested": performance["summary"]["total_invested"],
            "total_pnl": performance["summary"]["total_unrealized_pnl"],
            "average_roi": performance["summary"]["average_roi"],
        },
        "assets": performance["assets"],
        "allocation": allocation["allocations"],
    }


def build_gemini_prompt(context: Dict) -> str:
    """
    Build prompt untuk Gemini AI

    Format:
    - User info (name, risk profile)
    - Portfolio summary (total, ROI, P&L)
    - Asset details (per asset)
    - Allocation breakdown
    - Request for analysis
    """
    user = context["user"]
    portfolio = context["portfolio"]
    assets = context["assets"]
    allocation = context["allocation"]

    prompt = f"""
Kamu adalah financial advisor profesional. Analisis portfolio investasi ini dan berikan advice yang personal dan actionable.

**USER PROFILE:**
- Nama: {user['full_name']}
- Risk Profile: {user['risk_profile']}
- Currency: {user['default_currency']}

**PORTFOLIO SUMMARY:**
- Total Value: {user['default_currency']} {portfolio['total_value']}
- Total Invested: {user['default_currency']} {portfolio['total_invested']}
- Unrealized P&L: {user['default_currency']} {portfolio['total_pnl']}
- Average ROI: {portfolio['average_roi']}%

**ASSETS:**
"""

    for asset in assets:
        prompt += f"""
- {asset['asset_name']} ({asset['symbol']})
  Type: {asset['asset_type']}
  Quantity: {asset['quantity']}
  Avg Buy Price: {user['default_currency']} {asset['avg_buy_price']}
  Current Price: {user['default_currency']} {asset['current_price']}
  Current Value: {user['default_currency']} {asset['current_value']}
  ROI: {asset['roi']}%
  P&L: {user['default_currency']} {asset['unrealized_pnl']}
"""

    prompt += f"""

**ALLOCATION:**
"""

    for alloc in allocation:
        prompt += f"- {alloc['asset_type']}: {alloc['percentage']}% ({user['default_currency']} {alloc['value']})\n"

    prompt += """

**TASK:**
Berikan analisis yang sangat singkat, padat, ringkas, dan to the point (maksimal 2 kalimat untuk summary, dan maksimal 1 kalimat per poin analisis/saran). Jangan bertele-tele.
1. Personal (sesuai risk profile user)
2. Actionable (step-by-step action plan yang sangat konkret, singkat, dan padat)
3. Contextual (pertimbangkan ROI, P&L, allocation)
4. Bahasa Indonesia yang natural, profesional, dan ringkas
5. PENTING: Gunakan simbol Rupiah (Rp) untuk semua nilai uang. Jangan menggunakan simbol dollar ($) atau USD karena mata uang portfolio adalah Rupiah (IDR). Contoh: Tulis "Rp 150 juta", BUKAN "$150 juta".

Format response dalam JSON:
{
  "summary": "Overall summary (Sangat singkat & to the point, maksimal 2 kalimat)",
  "detailed_analysis": {
    "strengths": ["Kekuatan utama portfolio (sangat singkat, maksimal 1 kalimat per poin)", "..."],
    "weaknesses": ["Kelemahan utama portfolio (sangat singkat, maksimal 1 kalimat per poin)", "..."],
    "opportunities": ["Peluang improvement (sangat singkat, maksimal 1 kalimat per poin)", "..."],
    "threats": ["Risiko utama (sangat singkat, maksimal 1 kalimat per poin)", "..."]
  },
  "action_plan": [
    "Step 1 (sangat singkat & to the point)",
    "Step 2 (sangat singkat & to the point)",
    "Step 3 (sangat singkat & to the point)"
  ],
  "risk_assessment": "Overall risk assessment (Sangat singkat, maksimal 1 kalimat saja)"
}

PENTING: Response HARUS valid JSON. Jangan tambahkan markdown atau text lain di luar JSON.
"""

    return prompt


def parse_gemini_response(response_text: str) -> Dict:
    """
    Parse Gemini response text menjadi structured data

    Args:
        response_text: Raw response dari Gemini

    Returns:
        Parsed JSON object

    Note:
        - Try to extract JSON from response
        - If failed, return error message
    """
    try:
        # Try to extract JSON from response
        # Sometimes Gemini wraps JSON in markdown code blocks
        json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            # Try to find JSON object directly
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                json_text = response_text

        # Parse JSON
        data = json.loads(json_text)

        return data

    except Exception as e:
        print(f"[GEMINI AI] Parse error: {e}")
        return {
            "summary": "Error parsing AI response. Silakan coba lagi.",
            "error": str(e),
        }


async def get_cached_insights(
    db: AsyncSession,
    user_id,
) -> Optional[Dict]:
    """
    Get cached insights dari database

    Returns:
        Cache object jika valid (< 6 jam), None jika expired atau tidak ada
    """
    result = await db.execute(
        select(InsightCache).where(InsightCache.user_id == user_id)
    )
    cache = result.scalar_one_or_none()

    if not cache:
        return None

    # Check if expired (6 jam TTL)
    now = datetime.now(timezone.utc)
    if now > cache.expires_at:
        return None

    return {
        "insight_data": cache.insight_data,
        "health_score": cache.health_score,
        "created_at": cache.created_at,
    }


async def save_to_cache(
    db: AsyncSession,
    user_id,
    insights: Dict,
) -> None:
    """
    Save insights ke cache database

    Args:
        db: Database session
        user_id: User ID
        insights: Insights data (JSON)

    Note:
        - TTL: 6 jam
        - Upsert: update jika sudah ada, insert jika belum
    """
    # Calculate expiry (6 jam dari sekarang)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=6)

    # Check if cache exists
    result = await db.execute(
        select(InsightCache).where(InsightCache.user_id == user_id)
    )
    cache = result.scalar_one_or_none()

    if cache:
        # Update existing cache
        cache.insight_data = insights
        cache.expires_at = expires_at
        cache.created_at = now
    else:
        # Create new cache
        cache = InsightCache(
            user_id=user_id,
            insight_data=insights,
            expires_at=expires_at,
            created_at=now,
        )
        db.add(cache)

    await db.commit()
