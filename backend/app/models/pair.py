from sqlalchemy import Column, String, DateTime, Float, Integer, Index, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database.base import Base


class Pair(Base):
    """Represents a trading pair of two instruments"""
    __tablename__ = "pairs"

    id = Column(String, primary_key=True)  # Unique identifier (e.g., "hdfcbank-icicibank")
    symbol_a = Column(String, nullable=False, index=True)  # First instrument
    symbol_b = Column(String, nullable=False, index=True)  # Second instrument
    sector = Column(String, nullable=True)  # Common sector
    correlation = Column(Float, nullable=True)  # Correlation coefficient
    correlation_lookback = Column(Integer, nullable=True)  # Lookback period for correlation
    correlation_period = Column(DateTime, nullable=True)  # Calculation period
    coint_p_value = Column(Float, nullable=True)  # Cointegration test p-value
    hedge_ratio = Column(Float, nullable=True)  # Hedge ratio (beta)
    half_life = Column(Float, nullable=True)  # Half-life of mean reversion (days)
    adf_p_value = Column(Float, nullable=True)  # Augmented Dickey-Fuller p-value
    adf_statistic = Column(Float, nullable=True)  # ADF test statistic
    is_active = Column(Integer, default=1)  # Currently cointegrated
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_pair_symbols', 'symbol_a', 'symbol_b'),
        Index('idx_pair_active', 'is_active'),
        Index('idx_pair_correlation', 'correlation'),
    )
