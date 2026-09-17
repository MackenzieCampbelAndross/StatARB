import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Literal
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SignalType(str, Enum):
    """Types of trading signals"""
    LONG_SPREAD = "LONG SPREAD"
    SHORT_SPREAD = "SHORT SPREAD"
    EXIT = "EXIT"
    WATCH = "WATCH"


class SignalDirection(str, Enum):
    """Direction of trade"""
    LONG = "LONG"
    SHORT = "SHORT"
    NONE = "NONE"


class SignalEngine:
    """
    Generates trading signals based on Z-score thresholds and configurable rules.

    Default Strategy:
    - Z > +2σ: SHORT SPREAD (spread is too high, expect reversion down)
    - Z < -2σ: LONG SPREAD (spread is too low, expect reversion up)
    - Z moves toward 0: EXIT (take profit when spread normalizes)
    - |Z| < entry threshold: WATCH (no trade)

    All thresholds are configurable.
    """

    def __init__(
        self,
        entry_z_score: float = 2.0,
        exit_z_score: float = 0.0,
        stop_z_score: float = 4.0,
        max_holding_period: int = 30
    ):
        """
        Initialize the signal engine.

        Args:
            entry_z_score: Z-score threshold for entry signals
            exit_z_score: Z-score threshold for exit signals
            stop_z_score: Z-score threshold for stop-loss
            max_holding_period: Maximum holding period in days
        """
        self.entry_z_score = entry_z_score
        self.exit_z_score = exit_z_score
        self.stop_z_score = stop_z_score
        self.max_holding_period = max_holding_period

    def generate_signal(
        self,
        current_z_score: float,
        previous_z_score: Optional[float] = None,
        current_position: Optional[Literal["LONG", "SHORT", "NONE"]] = None,
        holding_period: Optional[int] = None
    ) -> Dict:
        """
        Generate a trading signal based on current Z-score.

        Args:
            current_z_score: Current Z-score of the spread
            previous_z_score: Previous Z-score (for detecting crossovers)
            current_position: Current position (if any)
            holding_period: Days since position entry

        Returns:
            Dictionary with signal information
        """
        signal_info = {
            'z_score': current_z_score,
            'signal': SignalType.WATCH.value,
            'direction': SignalDirection.NONE.value,
            'entry_reason': None,
            'exit_reason': None,
            'confidence': None,
            'timestamp': datetime.now()
        }

        # Check for stop-loss conditions
        if abs(current_z_score) > self.stop_z_score:
            signal_info['signal'] = SignalType.EXIT.value
            signal_info['exit_reason'] = f"Stop-loss triggered (Z={current_z_score:.2f} > {self.stop_z_score})"
            logger.warning(signal_info['exit_reason'])
            return signal_info

        # Check for maximum holding period
        if holding_period and holding_period >= self.max_holding_period:
            signal_info['signal'] = SignalType.EXIT.value
            signal_info['exit_reason'] = f"Max holding period reached ({holding_period} days)"
            logger.info(signal_info['exit_reason'])
            return signal_info

        # Generate entry signals if no current position
        if current_position is None or current_position == "NONE":
            if current_z_score >= self.entry_z_score:
                signal_info['signal'] = SignalType.SHORT_SPREAD.value
                signal_info['direction'] = SignalDirection.SHORT.value
                signal_info['entry_reason'] = f"Z-score {current_z_score:.2f} >= entry threshold {self.entry_z_score}"
                signal_info['confidence'] = self._calculate_confidence(current_z_score, self.entry_z_score)
                logger.info(f"SHORT SPREAD signal: {signal_info['entry_reason']}")

            elif current_z_score <= -self.entry_z_score:
                signal_info['signal'] = SignalType.LONG_SPREAD.value
                signal_info['direction'] = SignalDirection.LONG.value
                signal_info['entry_reason'] = f"Z-score {current_z_score:.2f} <= -entry threshold {-self.entry_z_score}"
                signal_info['confidence'] = self._calculate_confidence(abs(current_z_score), self.entry_z_score)
                logger.info(f"LONG SPREAD signal: {signal_info['entry_reason']}")

        # Generate exit signals if we have a position
        else:
            # Check for profit-taking exit
            if abs(current_z_score) <= self.exit_z_score:
                signal_info['signal'] = SignalType.EXIT.value
                signal_info['exit_reason'] = f"Z-score {current_z_score:.2f} crossed exit threshold {self.exit_z_score}"
                logger.info(f"EXIT signal: {signal_info['exit_reason']}")

            # Check for reversal (signal change)
            elif previous_z_score is not None:
                if current_position == "LONG" and current_z_score > 0:
                    signal_info['signal'] = SignalType.EXIT.value
                    signal_info['exit_reason'] = f"Z-score turned positive while in LONG position"
                    logger.info(f"EXIT signal: {signal_info['exit_reason']}")

                elif current_position == "SHORT" and current_z_score < 0:
                    signal_info['signal'] = SignalType.EXIT.value
                    signal_info['exit_reason'] = f"Z-score turned negative while in SHORT position"
                    logger.info(f"EXIT signal: {signal_info['exit_reason']}")

        return signal_info

    def _calculate_confidence(self, current_z: float, threshold: float) -> float:
        """
        Calculate signal confidence based on how far Z-score is from threshold.

        Args:
            current_z: Current absolute Z-score
            threshold: Entry threshold

        Returns:
            Confidence score between 0 and 1
        """
        # Confidence increases as Z-score moves further from threshold
        excess = current_z - threshold
        confidence = min(1.0, max(0.0, excess / 2.0))  # Cap at 1.0
        return round(confidence, 2)

    def generate_signals_history(
        self,
        z_scores: pd.Series,
        positions: Optional[pd.Series] = None
    ) -> pd.DataFrame:
        """
        Generate signal history for a series of Z-scores.

        Args:
            z_scores: Series of Z-scores
            positions: Optional series of current positions

        Returns:
            DataFrame with signal history
        """
        signals = []

        for i in range(len(z_scores)):
            current_z = z_scores.iloc[i]
            previous_z = z_scores.iloc[i-1] if i > 0 else None
            current_pos = positions.iloc[i] if positions is not None and i < len(positions) else None

            signal_info = self.generate_signal(current_z, previous_z, current_pos)
            signals.append(signal_info)

        return pd.DataFrame(signals)

    def filter_signals_by_type(
        self,
        signals_df: pd.DataFrame,
        signal_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Filter signals by type.

        Args:
            signals_df: DataFrame of signals
            signal_type: Signal type to filter by (None = all)

        Returns:
            Filtered DataFrame
        """
        if signal_type is None:
            return signals_df

        return signals_df[signals_df['signal'] == signal_type]

    def calculate_signal_performance(
        self,
        signals_df: pd.DataFrame,
        z_scores: pd.Series,
        spread: pd.Series
    ) -> Dict:
        """
        Calculate basic performance metrics for generated signals.

        Args:
            signals_df: DataFrame of signals
            z_scores: Series of Z-scores
            spread: Series of spread values

        Returns:
            Dictionary with performance metrics
        """
        if signals_df.empty:
            return {
                'total_signals': 0,
                'long_signals': 0,
                'short_signals': 0,
                'exit_signals': 0,
                'avg_confidence': None
            }

        total_signals = len(signals_df)
        long_signals = len(signals_df[signals_df['signal'] == SignalType.LONG_SPREAD.value])
        short_signals = len(signals_df[signals_df['signal'] == SignalType.SHORT_SPREAD.value])
        exit_signals = len(signals_df[signals_df['signal'] == SignalType.EXIT.value])

        avg_confidence = signals_df['confidence'].mean() if 'confidence' in signals_df.columns else None

        return {
            'total_signals': total_signals,
            'long_signals': long_signals,
            'short_signals': short_signals,
            'exit_signals': exit_signals,
            'watch_signals': total_signals - long_signals - short_signals - exit_signals,
            'avg_confidence': avg_confidence
        }

    def validate_signal_consistency(
        self,
        signals_df: pd.DataFrame
    ) -> Dict:
        """
        Validate signal consistency and detect potential issues.

        Args:
            signals_df: DataFrame of signals

        Returns:
            Dictionary with validation results
        """
        issues = []

        # Check for consecutive entry signals without exit
        for i in range(1, len(signals_df)):
            current_signal = signals_df.iloc[i]['signal']
            previous_signal = signals_df.iloc[i-1]['signal']

            if (previous_signal in [SignalType.LONG_SPREAD.value, SignalType.SHORT_SPREAD.value] and
                current_signal in [SignalType.LONG_SPREAD.value, SignalType.SHORT_SPREAD.value]):
                issues.append(f"Consecutive entry signals at index {i-1} and {i}")

        # Check for exit signals without prior entry
        for i in range(len(signals_df)):
            if signals_df.iloc[i]['signal'] == SignalType.EXIT.value:
                if i == 0:
                    issues.append(f"Exit signal at index {i} without prior entry")
                else:
                    prev_signal = signals_df.iloc[i-1]['signal']
                    if prev_signal == SignalType.EXIT.value or prev_signal == SignalType.WATCH.value:
                        issues.append(f"Exit signal at index {i} without prior entry")

        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'total_issues': len(issues)
        }

    def get_signal_summary(self, current_z_score: float) -> Dict:
        """
        Get a summary of current market condition based on Z-score.

        Args:
            current_z_score: Current Z-score

        Returns:
            Dictionary with market condition summary
        """
        condition = "NEUTRAL"
        if current_z_score >= self.entry_z_score:
            condition = "OVERBOUGHT"
        elif current_z_score <= -self.entry_z_score:
            condition = "OVERSOLD"
        elif abs(current_z_score) <= self.exit_z_score:
            condition = "NEUTRAL_RANGE"

        distance_to_entry = abs(current_z_score) - self.entry_z_score
        distance_to_exit = abs(current_z_score) - self.exit_z_score

        return {
            'current_z_score': current_z_score,
            'condition': condition,
            'distance_to_entry': distance_to_entry,
            'distance_to_exit': distance_to_exit,
            'entry_threshold': self.entry_z_score,
            'exit_threshold': self.exit_z_score,
            'stop_threshold': self.stop_z_score
        }

    def update_parameters(
        self,
        entry_z_score: Optional[float] = None,
        exit_z_score: Optional[float] = None,
        stop_z_score: Optional[float] = None,
        max_holding_period: Optional[int] = None
    ) -> None:
        """
        Update signal engine parameters.

        Args:
            entry_z_score: New entry Z-score threshold
            exit_z_score: New exit Z-score threshold
            stop_z_score: New stop Z-score threshold
            max_holding_period: New maximum holding period
        """
        if entry_z_score is not None:
            self.entry_z_score = entry_z_score
        if exit_z_score is not None:
            self.exit_z_score = exit_z_score
        if stop_z_score is not None:
            self.stop_z_score = stop_z_score
        if max_holding_period is not None:
            self.max_holding_period = max_holding_period

        logger.info(f"Updated signal parameters: entry={self.entry_z_score}, exit={self.exit_z_score}, stop={self.stop_z_score}")
