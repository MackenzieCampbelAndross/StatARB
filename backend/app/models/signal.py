from sqlalchemy import Column, String, DateTime, Float, Integer, Index, ForeignKey
from sqlalchemy.sql import func
from app.database.base import Base


class Signal(Base):
    """Trading signals for pairs"""
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pair_id = Column(String, nullable=False, index=True)  # Reference to pair
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    price_a = Column(Float, nullable=False)  # Current price of instrument A
    price_b = Column(Float, nullable=False)  # Current price of instrument B
    spread = Column(Float, nullable=False)  # Current spread
    z_score = Column(Float, nullable=False)  # Current Z-score
    signal = Column(String, nullable=False)  # Signal type: LONG SPREAD, SHORT SPREAD, EXIT, WATCH
    direction = Column(String, nullable=True)  # LONG, SHORT, or None
    hedge_ratio = Column(Float, nullable=True)  # Hedge ratio at signal time
    confidence = Column(Float, nullable=True)  # Signal confidence if applicable
    entry_reason = Column(String, nullable=True)  # Reason for entry signal
    exit_reason = Column(String, nullable=True)  # Reason for exit signal
    data_timestamp = Column(DateTime(timezone=True), nullable=True)  # Market data timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_signal_pair_timestamp', 'pair_id', 'timestamp'),
        Index('idx_signal_timestamp', 'timestamp'),
        Index('idx_signal_type', 'signal'),
    )
