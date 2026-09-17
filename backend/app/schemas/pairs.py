from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class Pair(BaseModel):
    """Trading pair data matching frontend interface"""
    id: str
    pair: str  # Format: "SYMBOL_A / SYMBOL_B"
    a: str  # Symbol A
    b: str  # Symbol B
    sector: Optional[str] = None
    correlation: float
    cointP: float  # Cointegration p-value
    hedgeRatio: float
    halfLife: float  # Half-life in days
    adfP: float  # ADF test p-value
    z: float  # Current Z-score
    signal: Literal["LONG SPREAD", "SHORT SPREAD", "EXIT", "WATCH"]

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "hdfcbank-icicibank",
                "pair": "HDFCBANK / ICICIBANK",
                "a": "HDFCBANK",
                "b": "ICICIBANK",
                "sector": "Financials",
                "correlation": 0.89,
                "cointP": 0.014,
                "hedgeRatio": 1.12,
                "halfLife": 5.3,
                "adfP": 0.021,
                "z": 2.31,
                "signal": "SHORT SPREAD"
            }
        }
    }


class PairFilter(BaseModel):
    """Filter parameters for pair queries"""
    minCorrelation: float = Field(default=0.70, ge=0, le=1)
    maxP: float = Field(default=0.05, ge=0, le=1)
    maxHalfLife: float = Field(default=30, ge=0)
    signal: Optional[str] = Field(default="ALL")
    query: Optional[str] = Field(default=None)

    model_config = {"arbitrary_types_allowed": True}


class Signal(BaseModel):
    """Signal data with current prices"""
    id: str
    pair: str
    a: str
    b: str
    sector: Optional[str] = None
    correlation: float
    cointP: float
    hedgeRatio: float
    halfLife: float
    adfP: float
    z: float
    signal: Literal["LONG SPREAD", "SHORT SPREAD", "EXIT", "WATCH"]
    priceA: float
    priceB: float
    spread: float
    updated: str  # Timestamp string

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "hdfcbank-icicibank",
                "pair": "HDFCBANK / ICICIBANK",
                "a": "HDFCBANK",
                "b": "ICICIBANK",
                "sector": "Financials",
                "correlation": 0.89,
                "cointP": 0.014,
                "hedgeRatio": 1.12,
                "halfLife": 5.3,
                "adfP": 0.021,
                "z": 2.31,
                "signal": "SHORT SPREAD",
                "priceA": 1732.4,
                "priceB": 823.7,
                "spread": 0.88,
                "updated": "13:42:08 IST"
            }
        }
    }
