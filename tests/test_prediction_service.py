from datetime import datetime

import pandas as pd
import pytest

from app.services.prediction_service import (
    InvalidHorizonError,
    InvalidTickerError,
    StockPredictor,
    format_prediction,
    normalize_ticker,
)


class FakePredictor:
    last_close = 1000.0
    last_date = pd.Timestamp(datetime(2026, 5, 22))

    def predict(self, horizon: int) -> dict[str, float]:
        return {"q10": 980.0, "q50": 1008.0, "q90": 1030.0}


def test_normalize_ticker_adds_idx_suffix():
    assert normalize_ticker("bbca") == "BBCA.JK"
    assert normalize_ticker("BBCA.JK") == "BBCA.JK"


def test_normalize_ticker_rejects_unsafe_input():
    with pytest.raises(InvalidTickerError):
        normalize_ticker("BBCA JK")


def test_predictor_rejects_invalid_horizon_before_fit():
    predictor = StockPredictor()

    with pytest.raises(InvalidHorizonError):
        predictor.predict(8)


def test_format_prediction_sorts_quantiles_and_skips_weekend():
    result = format_prediction("BBCA.JK", FakePredictor(), horizon=2)

    assert result["ticker"] == "BBCA.JK"
    assert result["prediction_date"] == "2026-05-26"
    assert result["direction"] == "naik"
    assert result["predicted_price"] == {
        "lower": 980.0,
        "median": 1008.0,
        "upper": 1030.0,
    }
