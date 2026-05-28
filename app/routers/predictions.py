"""
Predictions Router - stock price prediction endpoints.
"""

from fastapi import APIRouter, Depends, Query
from starlette.concurrency import run_in_threadpool

from app.models.user import User
from app.schemas.prediction import StockPredictionResponse
from app.services.prediction_service import (
    MAX_HORIZON,
    StockPredictionError,
    predict_stock,
)
from app.utils.exceptions import SmartWealthException
from app.utils.security import get_current_user

router = APIRouter(tags=["Predictions"])


@router.get("/{ticker}", response_model=StockPredictionResponse)
async def predict_stock_endpoint(
    ticker: str,
    horizon: int = Query(1, description=f"Forecast horizon, 1-{MAX_HORIZON}"),
    current_user: User = Depends(get_current_user),
) -> StockPredictionResponse:
    """
    Predict an IDX stock price range for the next 1-7 business days.
    """
    _ = current_user

    try:
        result = await run_in_threadpool(predict_stock, ticker, horizon)
        return StockPredictionResponse(**result)
    except StockPredictionError as exc:
        raise SmartWealthException(
            status_code=exc.status_code,
            detail=exc.message,
            error_code=exc.error_code,
            details=exc.details,
        ) from exc
