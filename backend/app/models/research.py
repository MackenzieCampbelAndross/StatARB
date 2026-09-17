from sqlalchemy import Column, String, DateTime, Float, Integer, Index, Text
from sqlalchemy.sql import func
from app.database.base import Base


class ResearchExperiment(Base):
    """Research experiments for parameter exploration"""
    __tablename__ = "research_experiments"

    id = Column(String, primary_key=True)  # Unique experiment ID
    name = Column(String, nullable=False)  # Experiment name
    description = Column(Text, nullable=True)  # Experiment description

    # Parameters
    entry_z_score = Column(Float, nullable=False)
    exit_z_score = Column(Float, nullable=False)
    stop_z_score = Column(Float, nullable=False)
    holding_period = Column(Integer, nullable=False)
    transaction_cost = Column(Float, nullable=False)
    slippage = Column(Float, nullable=False)
    position_sizing = Column(String, nullable=True)
    correlation_threshold = Column(Float, nullable=True)
    coint_p_value = Column(Float, nullable=True)
    training_window = Column(Integer, nullable=True)
    testing_window = Column(Integer, nullable=True)

    # Results
    total_return = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown = Column(Float, nullable=True)
    cagr = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    num_trades = Column(Integer, nullable=True)

    # Metadata
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    status = Column(String, default="completed")  # running, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index('idx_research_created', 'created_at'),
        Index('idx_research_status', 'status'),
    )
