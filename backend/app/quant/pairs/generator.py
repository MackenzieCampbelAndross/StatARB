import itertools
from typing import List, Tuple, Set
from sqlalchemy.orm import Session
from app.models.instrument import Instrument
from app.models.pair import Pair
import logging

logger = logging.getLogger(__name__)


class PairGenerator:
    """
    Generates all possible pairs from a universe of instruments.
    Ensures no duplicate pairs (A/B and B/A are the same).
    """

    def __init__(self, db: Session):
        """
        Initialize the pair generator.

        Args:
            db: Database session
        """
        self.db = db

    def generate_all_pairs(self, instruments: List[Instrument]) -> List[Tuple[str, str]]:
        """
        Generate all possible unordered pairs from a list of instruments.

        For N instruments, generates N × (N - 1) / 2 pairs.

        Args:
            instruments: List of Instrument objects

        Returns:
            List of tuples (symbol_a, symbol_b)
        """
        symbols = [inst.id for inst in instruments]

        # Generate all unique combinations of 2 symbols
        # combinations generates unordered pairs, so (A,B) and (B,A) are the same
        pairs = list(itertools.combinations(symbols, 2))

        logger.info(f"Generated {len(pairs)} pairs from {len(symbols)} instruments")

        return pairs

    def generate_pairs_by_sector(self, instruments: List[Instrument]) -> dict:
        """
        Generate pairs grouped by sector.

        Args:
            instruments: List of Instrument objects

        Returns:
            Dictionary mapping sector to list of pairs
        """
        # Group instruments by sector
        sector_instruments = {}
        for inst in instruments:
            sector = inst.sector or "Unknown"
            if sector not in sector_instruments:
                sector_instruments[sector] = []
            sector_instruments[sector].append(inst.id)

        # Generate pairs within each sector
        sector_pairs = {}
        for sector, symbols in sector_instruments.items():
            if len(symbols) >= 2:
                pairs = list(itertools.combinations(symbols, 2))
                sector_pairs[sector] = pairs
                logger.info(f"Generated {len(pairs)} pairs in {sector} sector")

        return sector_pairs

    def generate_pair_id(self, symbol_a: str, symbol_b: str) -> str:
        """
        Generate a unique ID for a pair.

        Uses alphabetical order to ensure consistency:
        (A,B) and (B,A) both generate the same ID.

        Args:
            symbol_a: First symbol
            symbol_b: Second symbol

        Returns:
            Unique pair ID
        """
        # Sort symbols alphabetically to ensure consistent IDs
        sorted_symbols = sorted([symbol_a, symbol_b])
        return f"{sorted_symbols[0].lower()}-{sorted_symbols[1].lower()}"

    def store_pairs(self, pairs: List[Tuple[str, str]]) -> int:
        """
        Store pairs in the database.

        Args:
            pairs: List of tuples (symbol_a, symbol_b)

        Returns:
            Number of pairs stored
        """
        stored_count = 0

        for symbol_a, symbol_b in pairs:
            pair_id = self.generate_pair_id(symbol_a, symbol_b)

            # Check if pair already exists
            existing = self.db.query(Pair).filter(Pair.id == pair_id).first()

            if not existing:
                # Get sector (assuming both stocks are in same sector)
                instrument_a = self.db.query(Instrument).filter(Instrument.id == symbol_a).first()
                sector = instrument_a.sector if instrument_a else None

                # Create new pair
                pair = Pair(
                    id=pair_id,
                    symbol_a=symbol_a,
                    symbol_b=symbol_b,
                    sector=sector,
                    is_active=1
                )
                self.db.add(pair)
                stored_count += 1

        self.db.commit()
        logger.info(f"Stored {stored_count} new pairs in database")

        return stored_count

    def get_existing_pairs(self) -> Set[str]:
        """
        Get all existing pair IDs from the database.

        Returns:
            Set of existing pair IDs
        """
        pairs = self.db.query(Pair.id).all()
        return set(pair[0] for pair in pairs)

    def get_missing_pairs(self, all_pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Find pairs that are not yet in the database.

        Args:
            all_pairs: List of all possible pairs

        Returns:
            List of missing pairs
        """
        existing_ids = self.get_existing_pairs()
        missing_pairs = []

        for symbol_a, symbol_b in all_pairs:
            pair_id = self.generate_pair_id(symbol_a, symbol_b)
            if pair_id not in existing_ids:
                missing_pairs.append((symbol_a, symbol_b))

        logger.info(f"Found {len(missing_pairs)} missing pairs out of {len(all_pairs)} total")

        return missing_pairs

    def generate_and_store_pairs(self, instruments: List[Instrument]) -> dict:
        """
        Complete workflow: generate pairs and store in database.

        Args:
            instruments: List of Instrument objects

        Returns:
            Dictionary with statistics
        """
        logger.info("Starting pair generation workflow")

        # Generate all possible pairs
        all_pairs = self.generate_all_pairs(instruments)

        # Find missing pairs
        missing_pairs = self.get_missing_pairs(all_pairs)

        # Store missing pairs
        stored_count = self.store_pairs(missing_pairs)

        return {
            'total_possible_pairs': len(all_pairs),
            'existing_pairs': len(all_pairs) - len(missing_pairs),
            'new_pairs_stored': stored_count,
            'instruments_count': len(instruments)
        }

    def get_pairs_for_symbols(self, symbol: str) -> List[Pair]:
        """
        Get all pairs that include a specific symbol.

        Args:
            symbol: Stock symbol

        Returns:
            List of Pair objects
        """
        return self.db.query(Pair).filter(
            (Pair.symbol_a == symbol) | (Pair.symbol_b == symbol)
        ).all()

    def delete_pair(self, pair_id: str) -> bool:
        """
        Delete a pair from the database.

        Args:
            pair_id: Pair ID

        Returns:
            True if successful
        """
        pair = self.db.query(Pair).filter(Pair.id == pair_id).first()

        if pair:
            self.db.delete(pair)
            self.db.commit()
            logger.info(f"Deleted pair: {pair_id}")
            return True

        return False

    def get_pair_statistics(self) -> dict:
        """
        Get statistics about pairs in the database.

        Returns:
            Dictionary with pair statistics
        """
        total_pairs = self.db.query(Pair).count()
        active_pairs = self.db.query(Pair).filter(Pair.is_active == 1).count()

        # Count by sector
        sector_counts = {}
        for pair in self.db.query(Pair.sector, Pair.id).all():
            sector = pair[0] or "Unknown"
            sector_counts[sector] = sector_counts.get(sector, 0) + 1

        return {
            'total_pairs': total_pairs,
            'active_pairs': active_pairs,
            'inactive_pairs': total_pairs - active_pairs,
            'pairs_by_sector': sector_counts
        }
