from sqlalchemy import Column, String, DateTime, Float, Boolean, Index
from sqlalchemy.sql import func
from app.database.base import Base


class Instrument(Base):
    """Represents a financial instrument (stock, index, etc.)"""
    __tablename__ = "instruments"

    id = Column(String, primary_key=True)  # Symbol (e.g., "HDFCBANK")
    name = Column(String, nullable=False)  # Full name
    sector = Column(String, nullable=True)  # Sector classification
    exchange = Column(String, nullable=True)  # Exchange (e.g., "NSE")
    instrument_type = Column(String, nullable=True)  # "EQUITY", "INDEX", etc.
    is_active = Column(Boolean, default=True)  # Currently traded
    listed_date = Column(DateTime, nullable=True)  # Listing date
    delisted_date = Column(DateTime, nullable=True)  # Delisting date (if any)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_instrument_sector', 'sector'),
        Index('idx_instrument_exchange', 'exchange'),
        Index('idx_instrument_active', 'is_active'),
    )
