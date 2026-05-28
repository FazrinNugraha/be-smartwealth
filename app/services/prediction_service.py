"""
Stock prediction service for IDX tickers.

The model is trained on demand from recent Yahoo Finance history. It returns a
median forecast plus lower/upper quantile estimates for 1-7 business days.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

HISTORY_PERIOD = "3y"
MIN_DATA_POINTS = 252
MAX_HORIZON = 7
QUANTILES = (0.1, 0.5, 0.9)
CACHE_TTL_SECONDS = 60 * 60

DISCLAIMER = (
    "Prediksi ini dihasilkan oleh model statistik berdasarkan data historis "
    "dan BUKAN merupakan rekomendasi investasi."
)

logger = logging.getLogger(__name__)

YFINANCE_CACHE_DIR = os.path.join(tempfile.gettempdir(), "smartwealth_yfinance_cache")


class StockPredictionError(Exception):
    """Base error with an API-friendly error code."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class InvalidTickerError(StockPredictionError):
    def __init__(self, ticker: str):
        super().__init__(
            "Ticker tidak valid. Gunakan kode saham IDX seperti BBCA atau BBCA.JK.",
            "INVALID_TICKER",
            400,
            {"ticker": ticker},
        )


class InvalidHorizonError(StockPredictionError):
    def __init__(self, horizon: int):
        super().__init__(
            f"Horizon harus 1..{MAX_HORIZON}, dapat {horizon}.",
            "INVALID_HORIZON",
            400,
            {"horizon": horizon, "max_horizon": MAX_HORIZON},
        )


class TickerNotFoundError(StockPredictionError):
    def __init__(self, ticker: str):
        super().__init__(
            f"Tidak ada data untuk {ticker}. Cek lagi kode sahamnya.",
            "TICKER_NOT_FOUND",
            404,
            {"ticker": ticker},
        )


class InsufficientDataError(StockPredictionError):
    def __init__(self, ticker: str, actual_rows: int):
        super().__init__(
            (
                f"Data {ticker} hanya {actual_rows} baris "
                f"(minimal {MIN_DATA_POINTS})."
            ),
            "INSUFFICIENT_DATA",
            422,
            {
                "ticker": ticker,
                "actual_rows": actual_rows,
                "required_rows": MIN_DATA_POINTS,
            },
        )


class MarketDataUnavailableError(StockPredictionError):
    def __init__(self, ticker: str, detail: str):
        super().__init__(
            f"Data market untuk {ticker} sedang tidak tersedia. Coba lagi sebentar.",
            "RATE_LIMITED",
            503,
            {"ticker": ticker, "detail": detail},
        )


class DependencyUnavailableError(StockPredictionError):
    def __init__(self, package: str):
        super().__init__(
            (
                f"Dependency model '{package}' belum terinstall di backend. "
                "Jalankan pip install -r requirements.txt lalu restart server."
            ),
            "MODEL_DEPENDENCY_MISSING",
            503,
            {"package": package},
        )


class ModelTrainingError(StockPredictionError):
    def __init__(self, detail: str):
        super().__init__(
            "Model gagal membuat prediksi untuk data ini.",
            "PREDICTION_FAILED",
            500,
            {"detail": detail},
        )


@dataclass
class CacheEntry:
    expires_at: datetime
    data: dict[str, Any]


_prediction_cache: dict[tuple[str, int], CacheEntry] = {}

_PROXY_ENV_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
)


@contextmanager
def _without_broken_local_proxy():
    """
    Some local dev shells set proxies to 127.0.0.1:9, which intentionally
    refuses outbound network calls. yfinance must bypass that dummy proxy.
    """
    removed: dict[str, str] = {}
    for name in _PROXY_ENV_VARS:
        value = os.environ.get(name)
        if value and "127.0.0.1:9" in value:
            removed[name] = value
            os.environ.pop(name, None)

    try:
        yield
    finally:
        os.environ.update(removed)


def normalize_ticker(ticker: str) -> str:
    raw = ticker.upper().strip()
    if not raw or not re.fullmatch(r"[A-Z0-9.-]+", raw):
        raise InvalidTickerError(ticker)
    if not raw.endswith(".JK"):
        raw = f"{raw}.JK"
    return raw


def _make_yf_session():
    try:
        from curl_cffi import requests as cffi_requests

        return cffi_requests.Session(impersonate="chrome")
    except Exception as exc:
        logger.warning("curl_cffi unavailable, using default yfinance session: %s", exc)
        return None


def _looks_rate_limited(error: Exception | None) -> bool:
    if error is None:
        return False
    text = str(error).lower()
    return any(
        marker in text
        for marker in ("429", "rate", "too many", "timed out", "timeout", "blocked")
    )


def fetch_stock_data(
    ticker: str,
    period: str = HISTORY_PERIOD,
    max_retry: int = 3,
) -> pd.DataFrame:
    import yfinance as yf

    os.makedirs(YFINANCE_CACHE_DIR, exist_ok=True)
    yf.set_tz_cache_location(YFINANCE_CACHE_DIR)
    yf.cache.set_cache_location(YFINANCE_CACHE_DIR)

    session = _make_yf_session()
    last_error: Exception | None = None
    df: pd.DataFrame | None = None

    for attempt in range(1, max_retry + 1):
        logger.info(
            "Fetching %s (%s) attempt %s/%s", ticker, period, attempt, max_retry
        )
        try:
            with _without_broken_local_proxy():
                yf_ticker = yf.Ticker(ticker, session=session)
                df = yf_ticker.history(
                    period=period,
                    auto_adjust=True,
                    actions=False,
                )
        except Exception as exc:
            last_error = exc
            logger.warning("Failed to fetch %s on attempt %s: %s", ticker, attempt, exc)
            time.sleep(1.5 * attempt)
            continue

        if df is not None and not df.empty:
            break

        last_error = ValueError("empty dataframe")
        time.sleep(1.5 * attempt)
    else:
        if _looks_rate_limited(last_error):
            raise MarketDataUnavailableError(ticker, str(last_error))
        raise TickerNotFoundError(ticker)

    if df is None or df.empty:
        raise TickerNotFoundError(ticker)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()

    if len(df) < MIN_DATA_POINTS:
        raise InsufficientDataError(ticker, len(df))

    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    try:
        import ta
    except ImportError as exc:
        raise DependencyUnavailableError("ta") from exc

    df = df.copy()
    open_price = df["Open"].astype(float)
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    volume = df["Volume"].astype(float)

    feat = pd.DataFrame(index=df.index)

    feat["return_1"] = close.pct_change(1)
    feat["return_2"] = close.pct_change(2)
    feat["return_3"] = close.pct_change(3)
    feat["return_5"] = close.pct_change(5)
    feat["return_10"] = close.pct_change(10)
    feat["log_return_1"] = np.log(close / close.shift(1))

    feat["open_gap"] = (open_price / close.shift(1)) - 1
    feat["intraday_return"] = (close / open_price) - 1

    for lag in (1, 2, 3, 5, 10, 20):
        feat[f"price_ratio_{lag}"] = close.shift(lag) / close

    for window in (5, 10, 20):
        feat[f"roll_mean_{window}"] = close.rolling(window).mean() / close
        feat[f"roll_std_{window}"] = close.rolling(window).std() / close
        feat[f"roll_min_{window}"] = close.rolling(window).min() / close
        feat[f"roll_max_{window}"] = close.rolling(window).max() / close

    feat["volatility_5"] = feat["log_return_1"].rolling(5).std()
    feat["volatility_10"] = feat["log_return_1"].rolling(10).std()
    feat["volatility_20"] = feat["log_return_1"].rolling(20).std()

    feat["rsi_14"] = ta.momentum.rsi(close, window=14)

    macd = ta.trend.MACD(close)
    feat["macd"] = macd.macd() / close
    feat["macd_signal"] = macd.macd_signal() / close
    feat["macd_diff"] = macd.macd_diff() / close

    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    feat["bb_pband"] = bb.bollinger_pband()
    feat["bb_wband"] = bb.bollinger_wband()

    feat["atr_14"] = (
        ta.volatility.average_true_range(
            high,
            low,
            close,
            window=14,
        )
        / close
    )

    stoch = ta.momentum.StochasticOscillator(high, low, close, window=14)
    feat["stoch_k"] = stoch.stoch()
    feat["stoch_d"] = stoch.stoch_signal()

    feat["vol_ratio_5"] = volume / volume.rolling(5).mean().replace(0, np.nan)
    feat["vol_ratio_20"] = volume / volume.rolling(20).mean().replace(0, np.nan)
    feat["vol_change_1"] = volume.pct_change(1)

    obv = ta.volume.on_balance_volume(close, volume)
    feat["obv_norm"] = obv.pct_change(5)

    feat["dow"] = df.index.dayofweek
    feat["dom"] = df.index.day
    feat["month"] = df.index.month

    return feat.replace([np.inf, -np.inf], np.nan)


class StockPredictor:
    def __init__(self, max_horizon: int = MAX_HORIZON):
        self.max_horizon = max_horizon
        self.models: dict[tuple[int, float], Any] = {}
        self.feature_columns: list[str] = []
        self.last_close: float | None = None
        self.last_date: pd.Timestamp | None = None
        self._last_features: pd.DataFrame | None = None

    @staticmethod
    def _lgb_params(alpha: float) -> dict[str, Any]:
        return {
            "objective": "quantile",
            "alpha": alpha,
            "metric": "quantile",
            "learning_rate": 0.05,
            "num_leaves": 31,
            "min_data_in_leaf": 20,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "n_estimators": 300,
            "n_jobs": 1,
        }

    @staticmethod
    def _make_target(close: pd.Series, horizon: int) -> pd.Series:
        return np.log(close.shift(-horizon) / close)

    def fit(self, df: pd.DataFrame, horizons: list[int] | None = None) -> "StockPredictor":
        try:
            import sklearn  # noqa: F401
        except ImportError as exc:
            raise DependencyUnavailableError("scikit-learn") from exc

        try:
            import lightgbm as lgb
        except ImportError as exc:
            raise DependencyUnavailableError("lightgbm") from exc

        if df is None or df.empty:
            raise ModelTrainingError("DataFrame kosong.")

        close = df["Close"].astype(float)
        self.last_close = float(close.iloc[-1])
        self.last_date = df.index[-1]

        features = build_features(df)
        self.feature_columns = list(features.columns)

        horizons_to_train = horizons or list(range(1, self.max_horizon + 1))
        for horizon in horizons_to_train:
            if not (1 <= horizon <= self.max_horizon):
                raise InvalidHorizonError(horizon)

            target = self._make_target(close, horizon).rename("target")
            data = features.join(target).dropna()

            if len(data) < 100:
                raise ModelTrainingError(
                    f"Data tidak cukup untuk horizon {horizon} ({len(data)} baris)."
                )

            x_train = data[self.feature_columns]
            y_train = data["target"]

            for quantile in QUANTILES:
                model = lgb.LGBMRegressor(**self._lgb_params(quantile))
                model.fit(x_train, y_train)
                self.models[(horizon, quantile)] = model

        self._last_features = features.iloc[[-1]][self.feature_columns].fillna(0)
        logger.info("Trained %s quantile models", len(self.models))
        return self

    def predict(self, horizon: int) -> dict[str, float]:
        if not (1 <= horizon <= self.max_horizon):
            raise InvalidHorizonError(horizon)
        if self._last_features is None or self.last_close is None:
            raise ModelTrainingError("Model belum di-fit.")
        if (horizon, QUANTILES[0]) not in self.models:
            raise ModelTrainingError(f"Model horizon {horizon} belum dilatih.")

        output: dict[str, float] = {}
        for quantile in QUANTILES:
            prediction = self.models[(horizon, quantile)].predict(self._last_features)
            log_return = float(prediction[0])
            price = self.last_close * float(np.exp(log_return))
            output[f"q{int(quantile * 100)}"] = price
        return output


def _next_business_date(start: pd.Timestamp, days: int) -> pd.Timestamp:
    current = start
    added = 0
    while added < days:
        current = current + pd.Timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def format_prediction(
    ticker: str,
    predictor: StockPredictor,
    horizon: int,
    flat_threshold_pct: float = 0.5,
) -> dict[str, Any]:
    raw = predictor.predict(horizon)
    last_close = predictor.last_close
    last_date = predictor.last_date

    if last_close is None or last_date is None:
        raise ModelTrainingError("Model belum punya harga terakhir.")

    lower, median, upper = sorted([raw["q10"], raw["q50"], raw["q90"]])
    pct_change_median = (median - last_close) / last_close * 100

    if pct_change_median > flat_threshold_pct:
        direction = "naik"
    elif pct_change_median < -flat_threshold_pct:
        direction = "turun"
    else:
        direction = "sideways"

    return {
        "ticker": ticker,
        "last_close": round(last_close, 2),
        "last_close_date": last_date.strftime("%Y-%m-%d"),
        "horizon_days": horizon,
        "prediction_date": _next_business_date(last_date, horizon).strftime("%Y-%m-%d"),
        "direction": direction,
        "predicted_price": {
            "lower": round(lower, 2),
            "median": round(median, 2),
            "upper": round(upper, 2),
        },
        "change_percent": {
            "lower": round((lower - last_close) / last_close * 100, 2),
            "median": round(pct_change_median, 2),
            "upper": round((upper - last_close) / last_close * 100, 2),
        },
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "disclaimer": DISCLAIMER,
    }


def _cache_key(ticker: str, horizon: int) -> tuple[str, int]:
    return ticker, horizon


def _get_cached_prediction(ticker: str, horizon: int) -> dict[str, Any] | None:
    entry = _prediction_cache.get(_cache_key(ticker, horizon))
    if entry is None:
        return None
    if entry.expires_at <= datetime.now(timezone.utc):
        _prediction_cache.pop(_cache_key(ticker, horizon), None)
        return None
    return {**entry.data, "cached": True}


def _set_cached_prediction(ticker: str, horizon: int, data: dict[str, Any]) -> None:
    _prediction_cache[_cache_key(ticker, horizon)] = CacheEntry(
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=CACHE_TTL_SECONDS),
        data={**data, "cached": False},
    )


def predict_stock(ticker: str, horizon: int = 1) -> dict[str, Any]:
    normalized_ticker = normalize_ticker(ticker)

    if not (1 <= horizon <= MAX_HORIZON):
        raise InvalidHorizonError(horizon)

    cached = _get_cached_prediction(normalized_ticker, horizon)
    if cached is not None:
        return cached

    df = fetch_stock_data(normalized_ticker)
    predictor = StockPredictor().fit(df, horizons=[horizon])
    result = format_prediction(normalized_ticker, predictor, horizon)
    _set_cached_prediction(normalized_ticker, horizon, result)
    return result
