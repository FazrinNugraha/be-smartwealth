"""
UserAsset model
"""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class UserAsset(Base):
    """User's asset holdings"""

    __tablename__ = "user_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Asset identification
    symbol = Column(String(20), nullable=False)  # BBCA.JK, bitcoin, GC=F
    asset_name = Column(String(255), nullable=False)  # Bank Central Asia, Bitcoin, Gold
    asset_type = Column(
        String(20), nullable=False
    )  # stock_id | stock_us | crypto | gold | cash

    # Holdings
    quantity = Column(
        Numeric(20, 8), nullable=False, default=0
    )  # Support crypto decimals
    avg_buy_price = Column(Numeric(20, 8), nullable=False)  # Average purchase price
    currency = Column(String(3), nullable=False, default="IDR")  # USD, IDR, EUR, etc

    # Optional metadata
    notes = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relationships
    user = relationship("User", back_populates="assets")
    transactions = relationship(
        "Transaction", back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<UserAsset {self.symbol} ({self.asset_type})>"
