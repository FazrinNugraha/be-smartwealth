"""
Insight Engine Service - Rule-based portfolio analysis

Fungsi file ini:
- Analyze portfolio berdasarkan rules finansial
- Generate insights (warnings, suggestions, alerts)
- Calculate health score (0-100)
- Return structured insights untuk frontend

Rules:
1. Concentration Risk - Single asset > 40%
2. Risk Profile Mismatch - Allocation tidak sesuai risk profile
3. Emergency Fund - Cash < 10%
4. Loss Alert - Any asset ROI < -20%
5. Diversification - < 3 asset types
6. High Performer - Any asset ROI > 50%
"""

from decimal import Decimal
from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services import dashboard_service


async def get_rule_based_insights(
    db: AsyncSession,
    user: User,
) -> Dict:
    """
    Generate rule-based insights untuk portfolio user

    Args:
        db: Database session
        user: User object

    Returns:
        {
            "health_score": 65,
            "health_status": "fair",
            "summary": "Portfolio Anda cukup baik...",
            "insights": [...],
            "disclaimer": "..."
        }
    """
    # Get portfolio data
    allocation = await dashboard_service.get_allocation(db, str(user.id))
    performance = await dashboard_service.get_performance(db, str(user.id))

    # Extract data
    allocations = {
        item["asset_type"]: Decimal(item["percentage"])
        for item in allocation["allocations"]
    }

    assets = performance["assets"]

    # Run all checks
    insights = []

    # Rule 1: Concentration Risk
    insights.extend(check_concentration_risk(assets, allocations))

    # Rule 2: Risk Profile Mismatch
    insights.extend(check_risk_profile_mismatch(user, allocations))

    # Rule 3: Emergency Fund
    insights.extend(check_emergency_fund(allocations))

    # Rule 4: Loss Alert
    insights.extend(check_loss_alert(assets))

    # Rule 5: Diversification
    insights.extend(check_diversification(allocations))

    # Rule 6: High Performer
    insights.extend(check_high_performer(assets))

    # Calculate health score
    health_score = calculate_health_score(insights, allocations, assets)
    health_status = get_health_status(health_score)

    # Generate summary
    summary = generate_summary(health_score, len(insights))

    return {
        "health_score": health_score,
        "health_status": health_status,
        "summary": summary,
        "insights": insights,
        "disclaimer": "Insights ini bersifat edukatif dan bukan nasihat investasi. Konsultasikan dengan financial advisor untuk keputusan investasi.",
    }


def check_concentration_risk(
    assets: List[Dict], allocations: Dict[str, Decimal]
) -> List[Dict]:
    """
    Check: Apakah ada single asset yang terlalu dominan (> 40%)?
    """
    insights = []

    # Check per asset
    for asset in assets:
        percentage = (
            Decimal(asset["current_value"])
            / sum(Decimal(a["current_value"]) for a in assets)
        ) * 100

        if percentage > 40:
            insights.append(
                {
                    "type": "warning",
                    "category": "concentration_risk",
                    "title": "Concentration Risk Tinggi",
                    "message": f"{asset['asset_name']} menyumbang {percentage:.1f}% dari portfolio Anda.",
                    "recommendation": f"Kurangi exposure {asset['asset_name']} menjadi maksimal 40% untuk mengurangi risiko.",
                    "severity": "high",
                    "affected_assets": [asset["symbol"]],
                }
            )

    # Check per asset type
    for asset_type, percentage in allocations.items():
        if percentage > 60:
            insights.append(
                {
                    "type": "warning",
                    "category": "concentration_risk",
                    "title": f"Terlalu Banyak di {asset_type.replace('_', ' ').title()}",
                    "message": f"{asset_type.replace('_', ' ').title()} menyumbang {percentage}% dari portfolio.",
                    "recommendation": f"Diversifikasi ke asset type lain untuk mengurangi risiko.",
                    "severity": "medium",
                }
            )

    return insights


def check_risk_profile_mismatch(
    user: User, allocations: Dict[str, Decimal]
) -> List[Dict]:
    """
    Check: Apakah allocation sesuai dengan risk profile user?

    Guidelines:
    - Conservative: Crypto max 10%, Cash min 30%
    - Moderate: Crypto max 30%, Cash min 15%
    - Aggressive: Crypto max 50%, Cash min 5%
    """
    insights = []

    crypto_pct = allocations.get("crypto", Decimal("0"))
    cash_pct = allocations.get("cash", Decimal("0"))

    risk_profile = user.risk_profile or "moderate"

    if risk_profile == "conservative":
        if crypto_pct > 10:
            insights.append(
                {
                    "type": "warning",
                    "category": "risk_mismatch",
                    "title": "Crypto Terlalu Tinggi untuk Conservative",
                    "message": f"Crypto {crypto_pct}% terlalu tinggi untuk profil conservative.",
                    "recommendation": "Kurangi crypto menjadi maksimal 10%. Alokasikan ke obligasi atau deposito.",
                    "severity": "high",
                }
            )

        if cash_pct < 30:
            insights.append(
                {
                    "type": "warning",
                    "category": "risk_mismatch",
                    "title": "Cash Terlalu Rendah untuk Conservative",
                    "message": f"Cash {cash_pct}% terlalu rendah untuk profil conservative.",
                    "recommendation": "Tingkatkan cash menjadi minimal 30%.",
                    "severity": "medium",
                }
            )

    elif risk_profile == "moderate":
        if crypto_pct > 30:
            insights.append(
                {
                    "type": "warning",
                    "category": "risk_mismatch",
                    "title": "Crypto Terlalu Tinggi untuk Moderate",
                    "message": f"Crypto {crypto_pct}% terlalu agresif untuk profil moderate.",
                    "recommendation": "Kurangi crypto menjadi maksimal 30%.",
                    "severity": "medium",
                }
            )

        if cash_pct < 15:
            insights.append(
                {
                    "type": "suggestion",
                    "category": "risk_mismatch",
                    "title": "Cash Bisa Ditingkatkan",
                    "message": f"Cash {cash_pct}% di bawah rekomendasi untuk profil moderate.",
                    "recommendation": "Tingkatkan cash menjadi minimal 15%.",
                    "severity": "low",
                }
            )

    elif risk_profile == "aggressive":
        if crypto_pct > 50:
            insights.append(
                {
                    "type": "alert",
                    "category": "risk_mismatch",
                    "title": "Crypto Sangat Tinggi",
                    "message": f"Crypto {crypto_pct}% sangat tinggi bahkan untuk profil aggressive.",
                    "recommendation": "Pertimbangkan diversifikasi untuk mengurangi volatilitas.",
                    "severity": "medium",
                }
            )

    return insights


def check_emergency_fund(allocations: Dict[str, Decimal]) -> List[Dict]:
    """
    Check: Apakah punya emergency fund cukup (cash >= 10%)?
    """
    insights = []

    cash_pct = allocations.get("cash", Decimal("0"))

    if cash_pct < 10:
        insights.append(
            {
                "type": "warning",
                "category": "emergency_fund",
                "title": "Emergency Fund Kurang",
                "message": f"Cash hanya {cash_pct}% dari portfolio.",
                "recommendation": "Tingkatkan cash reserve minimal 10-20% untuk emergency fund. Target ideal: 3-6 bulan pengeluaran.",
                "severity": "high",
            }
        )
    elif cash_pct >= 10 and cash_pct < 15:
        insights.append(
            {
                "type": "suggestion",
                "category": "emergency_fund",
                "title": "Emergency Fund Cukup",
                "message": f"Cash {cash_pct}% sudah cukup untuk emergency fund dasar.",
                "recommendation": "Pertimbangkan tingkatkan menjadi 15-20% untuk lebih aman.",
                "severity": "low",
            }
        )

    return insights


def check_loss_alert(assets: List[Dict]) -> List[Dict]:
    """
    Check: Apakah ada asset yang rugi besar (ROI < -20%)?
    """
    insights = []

    for asset in assets:
        roi = Decimal(asset["roi"])

        if roi < -20:
            insights.append(
                {
                    "type": "alert",
                    "category": "loss_alert",
                    "title": f"{asset['asset_name']} Rugi Besar",
                    "message": f"{asset['asset_name']} turun {roi}% (Rugi Rp {abs(Decimal(asset['unrealized_pnl'])):,.0f}).",
                    "recommendation": "Evaluasi: Hold untuk recovery atau cut loss? Pertimbangkan average down jika masih percaya dengan aset ini.",
                    "severity": "high",
                    "affected_assets": [asset["symbol"]],
                }
            )
        elif roi < -10:
            insights.append(
                {
                    "type": "alert",
                    "category": "loss_alert",
                    "title": f"{asset['asset_name']} Turun",
                    "message": f"{asset['asset_name']} turun {roi}%.",
                    "recommendation": "Monitor pergerakan harga. Pertimbangkan strategi jika turun lebih dalam.",
                    "severity": "medium",
                    "affected_assets": [asset["symbol"]],
                }
            )

    return insights


def check_diversification(allocations: Dict[str, Decimal]) -> List[Dict]:
    """
    Check: Apakah portfolio cukup diversifikasi (>= 3 asset types)?
    """
    insights = []

    num_types = len(allocations)

    if num_types < 3:
        insights.append(
            {
                "type": "suggestion",
                "category": "diversification",
                "title": "Diversifikasi Terbatas",
                "message": f"Portfolio hanya memiliki {num_types} jenis aset.",
                "recommendation": "Pertimbangkan tambah saham, obligasi, atau aset lain untuk diversifikasi lebih baik.",
                "severity": "medium",
            }
        )
    elif num_types >= 5:
        insights.append(
            {
                "type": "positive",
                "category": "diversification",
                "title": "Diversifikasi Sangat Baik",
                "message": f"Portfolio memiliki {num_types} jenis aset yang berbeda.",
                "recommendation": "Pertahankan diversifikasi ini untuk mengurangi risiko.",
                "severity": "low",
            }
        )
    else:
        insights.append(
            {
                "type": "positive",
                "category": "diversification",
                "title": "Diversifikasi Baik",
                "message": f"Portfolio memiliki {num_types} jenis aset.",
                "recommendation": "Diversifikasi sudah cukup baik.",
                "severity": "low",
            }
        )

    return insights


def check_high_performer(assets: List[Dict]) -> List[Dict]:
    """
    Check: Apakah ada asset yang perform sangat baik (ROI > 50%)?
    """
    insights = []

    for asset in assets:
        roi = Decimal(asset["roi"])

        if roi > 50:
            insights.append(
                {
                    "type": "positive",
                    "category": "high_performer",
                    "title": f"{asset['asset_name']} Perform Sangat Baik",
                    "message": f"{asset['asset_name']} naik {roi}% (Profit Rp {Decimal(asset['unrealized_pnl']):,.0f})!",
                    "recommendation": "Pertimbangkan take profit sebagian (20-30%) untuk lock in gains. Sisanya biarkan running.",
                    "severity": "low",
                    "affected_assets": [asset["symbol"]],
                }
            )
        elif roi > 20:
            insights.append(
                {
                    "type": "positive",
                    "category": "high_performer",
                    "title": f"{asset['asset_name']} Perform Baik",
                    "message": f"{asset['asset_name']} naik {roi}%.",
                    "recommendation": "Pertahankan posisi ini. Monitor untuk take profit jika naik lebih tinggi.",
                    "severity": "low",
                    "affected_assets": [asset["symbol"]],
                }
            )

    return insights


def calculate_health_score(
    insights: List[Dict],
    allocations: Dict[str, Decimal],
    assets: List[Dict],
) -> int:
    """
    Calculate portfolio health score (0-100)

    Starting: 100 points
    Penalties:
    - High severity warning: -15 points
    - Medium severity warning: -10 points
    - Low severity warning: -5 points

    Bonuses:
    - Positive insights: +5 points each
    """
    score = 100

    for insight in insights:
        severity = insight.get("severity", "low")
        insight_type = insight.get("type", "info")

        if insight_type in ["warning", "alert"]:
            if severity == "high":
                score -= 15
            elif severity == "medium":
                score -= 10
            elif severity == "low":
                score -= 5

        elif insight_type == "positive":
            score += 5

    # Ensure score is between 0-100
    return max(0, min(100, score))


def get_health_status(score: int) -> str:
    """
    Convert health score to status label

    90-100: excellent
    70-89: good
    50-69: fair
    30-49: poor
    0-29: critical
    """
    if score >= 90:
        return "excellent"
    elif score >= 70:
        return "good"
    elif score >= 50:
        return "fair"
    elif score >= 30:
        return "poor"
    else:
        return "critical"


def generate_summary(score: int, num_insights: int) -> str:
    """
    Generate summary text based on health score
    """
    status = get_health_status(score)

    if status == "excellent":
        return f"Portfolio Anda dalam kondisi sangat baik! Pertahankan strategi investasi Anda."
    elif status == "good":
        return f"Portfolio Anda dalam kondisi baik. Ada {num_insights} insights untuk optimasi lebih lanjut."
    elif status == "fair":
        return f"Portfolio Anda cukup baik, tapi ada {num_insights} area yang perlu diperbaiki."
    elif status == "poor":
        return f"Portfolio Anda memiliki beberapa masalah yang perlu segera ditangani. Review {num_insights} insights di bawah."
    else:
        return f"Portfolio Anda memiliki risiko tinggi. Segera review dan perbaiki berdasarkan {num_insights} insights di bawah."
