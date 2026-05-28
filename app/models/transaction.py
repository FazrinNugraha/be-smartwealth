"""
Transaction model
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Transaction(Base):
    """Buy/Sell transaction records"""

    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Transaction details
    transaction_type = Column(String(10), nullable=False)  # buy | sell
    quantity = Column(Numeric(20, 8), nullable=False)
    price_per_unit = Column(Numeric(20, 8), nullable=False)
    total_amount = Column(Numeric(20, 2), nullable=False)  # quantity × price_per_unit
    fees = Column(Numeric(20, 2), default=0, nullable=False)  # Broker/admin fees

    # Metadata
    notes = Column(Text, nullable=True)
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="transactions")
    asset = relationship("UserAsset", back_populates="transactions")

    def __repr__(self):
        return f"<Transaction {self.transaction_type} {self.quantity} @ {self.price_per_unit}>"
