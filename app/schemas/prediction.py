"""
Schemas for stock prediction responses.
"""

from typing import Literal

from pydantic import BaseModel, Field


class PredictionPriceRange(BaseModel):
    lower: float = Field(..., description="Lower quantile price estimate")
    median: float = Field(..., description="Median price estimate")
    upper: float = Field(..., description="Upper quantile price estimate")


class PredictionChangeRange(BaseModel):
    lower: float = Field(..., description="Lower estimate change percentage")
    median: float = Field(..., description="Median estimate change percentage")
    upper: float = Field(..., description="Upper estimate change percentage")


class StockPredictionResponse(BaseModel):
    ticker: str
    last_close: float
    last_close_date: str
    horizon_days: int
    prediction_date: str
    direction: Literal["naik", "turun", "sideways"]
    predicted_price: PredictionPriceRange
    change_percent: PredictionChangeRange
    generated_at: str
    disclaimer: str
    cached: bool = False

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "ticker": "BBCA.JK",
                    "last_close": 9500,
                    "last_close_date": "2026-05-26",
                    "horizon_days": 2,
                    "prediction_date": "2026-05-28",
                    "direction": "sideways",
                    "predicted_price": {
                        "lower": 9350,
                        "median": 9480,
                        "upper": 9580,
                    },
                    "change_percent": {
                        "lower": -1.58,
                        "median": -0.21,
                        "upper": 0.84,
                    },
                    "generated_at": "2026-05-26T10:30:00Z",
                    "disclaimer": "Prediksi ini ...",
                    "cached": False,
                }
            ]
        }
    }
