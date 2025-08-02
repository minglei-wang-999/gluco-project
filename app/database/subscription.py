from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime, Numeric, ForeignKey
from sqlalchemy.sql import text

from app.database.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    plan_id = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False)  # active, inactive, expired
    expires_at = Column(DateTime(timezone=True), nullable=True)
    start_date = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=text("CURRENT_TIMESTAMP")
    )


class PaymentRecord(Base):
    __tablename__ = "payment_records"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False, index=True)
    subscription_id = Column(
        BigInteger,
        ForeignKey("subscriptions.id", ondelete="CASCADE"),
        nullable=True
    )
    transaction_id = Column(String(64), nullable=False, unique=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(16), nullable=False)  # success, failed
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP")
    ) 