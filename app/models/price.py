"""
AssetPrice and InsightCache models
"""

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class AssetPrice(Base):
    """Cached asset prices from external APIs"""

    __tablename__ = "asset_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Asset identification
    symbol = Column(String(20), nullable=False, index=True)
    asset_type = Column(String(20), nullable=False)

    # Price data
    price = Column(Numeric(20, 8), nullable=False)
    price_change_24h = Column(Numeric(10, 4), nullable=True)  # Percentage change
    currency = Column(String(5), nullable=False, default="IDR")
    source = Column(String(50), nullable=False)  # yfinance | coingecko

    # Metadata
    fetched_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self):
        return f"<AssetPrice {self.symbol} = {self.price} {self.currency}>"


class InsightCache(Base):
    """Cached AI insights from Gemini"""

    __tablename__ = "insight_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Cached data
    insight_data = Column(JSONB, nullable=False)  # Full Gemini response
    health_score = Column(Integer, nullable=True)  # 0-100

    # TTL
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="insight_cache")

    def __repr__(self):
        return f"<InsightCache user={self.user_id} score={self.health_score}>"
