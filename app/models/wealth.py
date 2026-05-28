"""
WealthHistory model
"""

from datetime import datetime, date
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class WealthHistory(Base):
    """Daily snapshot of user's net worth"""

    __tablename__ = "wealth_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Snapshot data
    total_value = Column(Numeric(20, 2), nullable=False)  # Total net worth
    breakdown = Column(
        JSONB, nullable=True
    )  # {"stock_id": 50000000, "crypto": 20000000, ...}

    # Timing
    snapshot_date = Column(Date, nullable=False, default=date.today)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="wealth_history")

    def __repr__(self):
        return f"<WealthHistory {self.snapshot_date} = {self.total_value}>"
