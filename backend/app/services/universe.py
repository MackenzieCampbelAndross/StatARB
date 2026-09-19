from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.instrument import Instrument
import logging

logger = logging.getLogger(__name__)


class UniverseService:
    """
    Service for managing the Nifty 50 universe and other stock universes.
    Handles current and historical constituents.
    """

    # Current Nifty 50 constituents (as of 2024)
    # This should be updated periodically or fetched from NSE
    NIFTY_50_CURRENT = [
        ("RELIANCE", "Reliance Industries Ltd", "Energy"),
        ("TCS", "Tata Consultancy Services", "Technology"),
        ("HDFCBANK", "HDFC Bank Ltd", "Financials"),
        ("INFY", "Infosys Ltd", "Technology"),
        ("ICICIBANK", "ICICI Bank Ltd", "Financials"),
        ("HINDUNILVR", "Hindustan Unilever Ltd", "Consumer"),
        ("ITC", "ITC Ltd", "Consumer"),
        ("SBIN", "State Bank of India", "Financials"),
        ("BHARTIARTL", "Bharti Airtel Ltd", "Telecom"),
        ("KOTAKBANK", "Kotak Mahindra Bank", "Financials"),
        ("LT", "Larsen & Toubro Ltd", "Industrials"),
        ("AXISBANK", "Axis Bank Ltd", "Financials"),
        ("ASIANPAINT", "Asian Paints Ltd", "Consumer"),
        ("MARUTI", "Maruti Suzuki India", "Consumer"),
        ("SUNPHARMA", "Sun Pharmaceutical Industries", "Healthcare"),
        ("TITAN", "Titan Company Ltd", "Consumer"),
        ("BAJFINANCE", "Bajaj Finance Ltd", "Financials"),
        ("DMART", "Avenue Supermarts Ltd", "Consumer"),
        ("WIPRO", "Wipro Ltd", "Technology"),
        ("HCLTECH", "HCL Technologies Ltd", "Technology"),
        ("ULTRACEMCO", "UltraTech Cement Ltd", "Materials"),
        ("NTPC", "NTPC Ltd", "Utilities"),
        ("POWERGRID", "Power Grid Corporation", "Utilities"),
        ("TATAMOTORS", "Tata Motors Ltd", "Consumer"),
        ("TATASTEEL", "Tata Steel Ltd", "Materials"),
        ("ONGC", "Oil & Natural Gas Corporation", "Energy"),
        ("JSWSTEEL", "JSW Steel Ltd", "Materials"),
        ("BPCL", "Bharat Petroleum Corporation", "Energy"),
        ("CIPLA", "Cipla Ltd", "Healthcare"),
        ("BRITANNIA", "Britannia Industries Ltd", "Consumer"),
        ("DIVISLAB", "Divi's Laboratories Ltd", "Healthcare"),
        ("DRREDDY", "Dr Reddy's Laboratories Ltd", "Healthcare"),
        ("EICHERMOT", "Eicher Motors Ltd", "Consumer"),
        ("GRASIM", "Grasim Industries Ltd", "Materials"),
        ("HINDALCO", "Hindalco Industries Ltd", "Materials"),
        ("APOLLOHOSP", "Apollo Hospitals Enterprise", "Healthcare"),
        ("NESTLEIND", "Nestle India Ltd", "Consumer"),
        ("SHREECEM", "Shree Cement Ltd", "Materials"),
        ("MAHINDRA", "Mahindra & Mahindra Ltd", "Consumer"),
        ("ADANIENT", "Adani Enterprises Ltd", "Conglomerate"),
        ("ADANIPORTS", "Adani Ports & Special Economic Zone", "Industrials"),
        ("TATACONSUM", "Tata Consumer Products Ltd", "Consumer"),
        ("COALINDIA", "Coal India Ltd", "Energy"),
        ("BAJAJFINSV", "Bajaj Finserv Ltd", "Financials"),
        ("UPL", "UPL Ltd", "Materials"),
        ("M&MFIN", "Mahindra & Mahindra Financial Services", "Financials"),
        ("TECHM", "Tech Mahindra Ltd", "Technology"),
        ("HEROMOTOCO", "Hero MotoCorp Ltd", "Consumer"),
        ("BEL", "Bharat Electronics Ltd", "Industrials"),
        ("PIDILITIND", "Pidilite Industries Ltd", "Materials"),
        ("ZOMATO", "Zomato Ltd", "Consumer"),
        ("PAYTM", "One97 Communications Ltd", "Technology"),
        ("NYKAA", "FSN E-Commerce Ventures Ltd", "Consumer"),
    ]

    def __init__(self, db: Session):
        """
        Initialize the universe service.

        Args:
            db: Database session
        """
        self.db = db

    def get_current_nifty_50(self) -> List[Instrument]:
        """
        Get the current Nifty 50 constituents from the database.

        Returns:
            List of Instrument objects
        """
        symbols = [symbol for symbol, _, _ in self.NIFTY_50_CURRENT]
        instruments = self.db.query(Instrument).filter(
            Instrument.id.in_(symbols),
            Instrument.is_active == True
        ).all()

        return instruments

    def initialize_nifty_50(self) -> int:
        """
        Initialize the Nifty 50 universe in the database.
        Creates instrument records if they don't exist.

        Returns:
            Number of instruments created/updated
        """
        logger.info("Initializing Nifty 50 universe")

        count = 0
        for symbol, name, sector in self.NIFTY_50_CURRENT:
            instrument = self.db.query(Instrument).filter(Instrument.id == symbol).first()

            if instrument:
                # Update existing
                instrument.name = name
                instrument.sector = sector
                instrument.exchange = "NSE"
                instrument.instrument_type = "EQUITY"
                instrument.is_active = True
            else:
                # Create new
                instrument = Instrument(
                    id=symbol,
                    name=name,
                    sector=sector,
                    exchange="NSE",
                    instrument_type="EQUITY",
                    is_active=True
                )
                self.db.add(instrument)

            count += 1

        self.db.commit()
        logger.info(f"Initialized {count} Nifty 50 instruments")

        return count

    def get_universe_by_sector(self, sector: str) -> List[Instrument]:
        """
        Get instruments by sector.

        Args:
            sector: Sector name

        Returns:
            List of Instrument objects
        """
        return self.db.query(Instrument).filter(
            Instrument.sector == sector,
            Instrument.is_active == True
        ).all()

    def get_all_active_instruments(self) -> List[Instrument]:
        """
        Get all active instruments.

        Returns:
            List of Instrument objects
        """
        return self.db.query(Instrument).filter(
            Instrument.is_active == True
        ).all()

    def get_historical_constituents(self, date: datetime) -> List[Instrument]:
        """
        Get Nifty 50 constituents as of a specific historical date.

        NOTE: This is a placeholder implementation.
        For accurate historical analysis, you need:
        1. Historical constituent data from NSE
        2. A table tracking index changes over time
        3. Point-in-time universe queries

        Args:
            date: Historical date

        Returns:
            List of Instrument objects (currently returns current universe)
        """
        logger.warning(
            "Historical constituent lookup not implemented. "
            "Returning current universe - this introduces survivorship bias."
        )

        # TODO: Implement proper historical constituent tracking
        # For now, return current universe
        return self.get_current_nifty_50()

    def get_universe_symbols(self, universe_type: str = "nifty_50") -> List[str]:
        """
        Get list of symbols for a universe.

        Args:
            universe_type: Type of universe (nifty_50, nifty_100, etc.)

        Returns:
            List of symbol strings
        """
        if universe_type == "nifty_50":
            return [symbol for symbol, _, _ in self.NIFTY_50_CURRENT]
        else:
            # For other universes, query database
            instruments = self.get_all_active_instruments()
            return [inst.id for inst in instruments]

    def add_instrument(
        self,
        symbol: str,
        name: str,
        sector: Optional[str] = None,
        exchange: str = "NSE",
        instrument_type: str = "EQUITY"
    ) -> Instrument:
        """
        Add a new instrument to the universe.

        Args:
            symbol: Stock symbol
            name: Full name
            sector: Sector classification
            exchange: Exchange
            instrument_type: Type of instrument

        Returns:
            Instrument object
        """
        instrument = Instrument(
            id=symbol,
            name=name,
            sector=sector,
            exchange=exchange,
            instrument_type=instrument_type,
            is_active=True
        )

        self.db.add(instrument)
        self.db.commit()

        logger.info(f"Added instrument: {symbol}")
        return instrument

    def deactivate_instrument(self, symbol: str) -> bool:
        """
        Deactivate an instrument (e.g., when delisted).

        Args:
            symbol: Stock symbol

        Returns:
            True if successful
        """
        instrument = self.db.query(Instrument).filter(Instrument.id == symbol).first()

        if instrument:
            instrument.is_active = False
            instrument.delisted_date = datetime.now()
            self.db.commit()
            logger.info(f"Deactivated instrument: {symbol}")
            return True

        return False

    def get_universe_summary(self) -> Dict:
        """
        Get summary statistics of the current universe.

        Returns:
            Dictionary with universe statistics
        """
        instruments = self.get_all_active_instruments()

        sector_counts = {}
        for inst in instruments:
            sector = inst.sector or "Unknown"
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        return {
            'total_instruments': len(instruments),
            'sectors': sector_counts,
            'exchanges': list(set(inst.exchange for inst in instruments if inst.exchange)),
            'instrument_types': list(set(inst.instrument_type for inst in instruments if inst.instrument_type))
        }
