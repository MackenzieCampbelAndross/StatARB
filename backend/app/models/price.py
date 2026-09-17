from sqlalchemy import Column, String, DateTime, Float, Integer, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.base import Base


class Price(Base):
    """Historical OHLCV price data"""
    __tablename__ = "prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, nullable=False, index=True)  # Instrument symbol
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=True)  # Trading volume
    adjusted_close = Column(Float, nullable=True)  # Adjusted for splits/dividends
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_price_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_price_timestamp', 'timestamp'),
    )
