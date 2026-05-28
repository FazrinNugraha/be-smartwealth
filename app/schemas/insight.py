"""
Insight Schemas - Response models for AI insights

Fungsi file ini:
- InsightResponse: Format data AI insights dari Gemini API
"""

from pydantic import BaseModel, Field


class InsightResponse(BaseModel):
    """
    Schema untuk response AI insights

    Dipakai di:
    - GET /api/v1/insights (cached insights)
    - POST /api/v1/insights/refresh (force regenerate)

    Field:
    - summary: Ringkasan kondisi portofolio (1-2 kalimat)
    - health_score: Skor kesehatan portofolio 0-100
    - insights: List insight/analisis dari AI
    - recommendations: List rekomendasi aksi
    - disclaimer: Disclaimer wajib (bukan nasihat investasi)

    Fungsi: Menampilkan AI insights di dashboard

    Data source:
    - Layer 1: Rule-based insights (instant, always runs)
      * Concentration risk (single asset > 40%)
      * Risk profile mismatch (crypto > 50% untuk moderate)
      * Emergency fund warning (cash < 10%)
      * Loss alert (ROI < -20%)

    - Layer 2: Gemini API insights (cached 6 jam)
      * Analisis mendalam portofolio
      * Rekomendasi rebalancing
      * Analisis risiko
      * Saran diversifikasi
    """

    summary: str = Field(..., description="Portfolio summary (1-2 sentences)")
    health_score: int = Field(
        ..., ge=0, le=100, description="Portfolio health score (0-100)"
    )
    insights: list[str] = Field(..., description="List of insights and analysis")
    recommendations: list[str] = Field(
        ..., description="List of actionable recommendations"
    )
    disclaimer: str = Field(
        default="Ini bukan nasihat investasi. Selalu lakukan riset sendiri dan konsultasi dengan advisor profesional.",
        description="Legal disclaimer",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "Portofolio Anda cukup seimbang dengan diversifikasi yang baik. ROI keseluruhan positif.",
                    "health_score": 75,
                    "insights": [
                        "Alokasi saham Indonesia (66.7%) mendominasi portofolio Anda",
                        "Crypto allocation (20%) sesuai dengan profil risiko moderate",
                        "Emas (13.3%) memberikan hedge yang baik terhadap inflasi",
                        "ROI keseluruhan +2.94% menunjukkan performa positif",
                    ],
                    "recommendations": [
                        "Pertimbangkan menambah alokasi cash/emergency fund hingga 10-15%",
                        "Diversifikasi saham Indonesia dengan menambah saham US/global",
                        "Monitor performa BBCA.JK yang mendominasi 66% portofolio",
                        "Rebalance jika satu aset melebihi 40% dari total portofolio",
                    ],
                    "disclaimer": "Ini bukan nasihat investasi. Selalu lakukan riset sendiri dan konsultasi dengan advisor profesional.",
                }
            ]
        }
    }
