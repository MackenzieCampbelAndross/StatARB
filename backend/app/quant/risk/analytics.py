import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RiskMetrics:
    """Risk metrics for a portfolio or strategy"""
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    var_95: float  # Value at Risk at 95% confidence
    var_99: float  # Value at Risk at 99% confidence
    expected_shortfall_95: float  # Expected Shortfall at 95% confidence
    skewness: float
    kurtosis: float
    beta: float
    tracking_error: float
    information_ratio: float


class RiskAnalytics:
    """
    Risk analytics engine for quantitative strategies.

    Calculates various risk metrics including:
    - Volatility and drawdown
    - Value at Risk (VaR) and Expected Shortfall (ES)
    - Sharpe and Sortino ratios
    - Portfolio exposure and concentration
    - Correlation analysis
    """

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize the risk analytics engine.

        Args:
            risk_free_rate: Annual risk-free rate for Sharpe calculation
        """
        self.risk_free_rate = risk_free_rate

    def calculate_portfolio_risk(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None
    ) -> RiskMetrics:
        """
        Calculate comprehensive risk metrics for a portfolio.

        Args:
            returns: Portfolio returns series
            benchmark_returns: Optional benchmark returns for relative metrics

        Returns:
            RiskMetrics object with calculated metrics
        """
        if len(returns) < 2:
            logger.warning("Insufficient data for risk calculation")
            return self._empty_risk_metrics()

        # Convert to daily if needed
        if returns.max() > 1:  # Assume percentage if values > 1
            returns = returns / 100

        # Basic statistics
        volatility = returns.std() * np.sqrt(252)  # Annualized volatility

        # Drawdown analysis
        max_drawdown = self._calculate_max_drawdown(returns)

        # Sharpe ratio
        excess_returns = returns - (self.risk_free_rate / 252)
        sharpe_ratio = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252) if excess_returns.std() > 0 else 0

        # Sortino ratio
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else 1
        sortino_ratio = (returns.mean() / downside_std) * np.sqrt(252) if downside_std > 0 else 0

        # VaR and Expected Shortfall
        var_95 = self._calculate_var(returns, 0.95)
        var_99 = self._calculate_var(returns, 0.99)
        es_95 = self._calculate_expected_shortfall(returns, 0.95)

        # Higher moments
        skewness = returns.skew()
        kurtosis = returns.kurtosis()

        # Relative metrics (if benchmark provided)
        beta = 0.0
        tracking_error = 0.0
        information_ratio = 0.0

        if benchmark_returns is not None and len(benchmark_returns) == len(returns):
            beta = self._calculate_beta(returns, benchmark_returns)
            tracking_error = self._calculate_tracking_error(returns, benchmark_returns)
            information_ratio = self._calculate_information_ratio(returns, benchmark_returns)

        return RiskMetrics(
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            var_95=var_95,
            var_99=var_99,
            expected_shortfall_95=es_95,
            skewness=skewness,
            kurtosis=kurtosis,
            beta=beta,
            tracking_error=tracking_error,
            information_ratio=information_ratio
        )

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown from returns."""
        cumulative = (1 + returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative - rolling_max) / rolling_max
        return drawdown.min()

    def _calculate_var(self, returns: pd.Series, confidence: float) -> float:
        """Calculate Value at Risk at given confidence level."""
        return np.percentile(returns, (1 - confidence) * 100)

    def _calculate_expected_shortfall(self, returns: pd.Series, confidence: float) -> float:
        """Calculate Expected Shortfall (Conditional VaR) at given confidence level."""
        var = self._calculate_var(returns, confidence)
        tail_losses = returns[returns <= var]
        return tail_losses.mean() if len(tail_losses) > 0 else var

    def _calculate_beta(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """Calculate beta relative to benchmark."""
        covariance = np.cov(returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        return covariance / benchmark_variance if benchmark_variance > 0 else 0

    def _calculate_tracking_error(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """Calculate tracking error."""
        excess_returns = returns - benchmark_returns
        return excess_returns.std() * np.sqrt(252)

    def _calculate_information_ratio(self, returns: pd.Series, benchmark_returns: pd.Series) -> float:
        """Calculate information ratio."""
        excess_returns = returns - benchmark_returns
        tracking_error = excess_returns.std()
        return (excess_returns.mean() / tracking_error) * np.sqrt(252) if tracking_error > 0 else 0

    def _empty_risk_metrics(self) -> RiskMetrics:
        """Return empty risk metrics when calculation is not possible."""
        return RiskMetrics(
            volatility=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            var_95=0.0,
            var_99=0.0,
            expected_shortfall_95=0.0,
            skewness=0.0,
            kurtosis=0.0,
            beta=0.0,
            tracking_error=0.0,
            information_ratio=0.0
        )

    def calculate_concentration_risk(
        self,
        positions: Dict[str, float],
        total_capital: float
    ) -> Dict:
        """
        Calculate concentration risk metrics.

        Args:
            positions: Dictionary of position_id -> position_value
            total_capital: Total portfolio capital

        Returns:
            Dictionary with concentration metrics
        """
        if not positions or total_capital == 0:
            return {
                'herfindahl_index': 0,
                'max_position_weight': 0,
                'num_positions': 0,
                'top_3_concentration': 0
            }

        # Calculate position weights
        weights = {pos: value / total_capital for pos, value in positions.items()}

        # Herfindahl-Hirschman Index (HHI)
        hhi = sum(w ** 2 for w in weights.values())

        # Maximum position weight
        max_weight = max(weights.values()) if weights else 0

        # Top 3 concentration
        sorted_weights = sorted(weights.values(), reverse=True)
        top_3_concentration = sum(sorted_weights[:3]) if len(sorted_weights) >= 3 else sum(sorted_weights)

        return {
            'herfindahl_index': hhi,
            'max_position_weight': max_weight,
            'num_positions': len(positions),
            'top_3_concentration': top_3_concentration,
            'position_weights': weights
        }

    def calculate_correlation_risk(
        self,
        returns_matrix: pd.DataFrame
    ) -> Dict:
        """
        Calculate correlation-based risk metrics.

        Args:
            returns_matrix: DataFrame with returns for each position

        Returns:
            Dictionary with correlation metrics
        """
        if returns_matrix.empty or len(returns_matrix.columns) < 2:
            return {
                'avg_correlation': 0,
                'max_correlation': 0,
                'correlation_matrix': None,
                'highly_correlated_pairs': []
            }

        # Calculate correlation matrix
        corr_matrix = returns_matrix.corr()

        # Get upper triangle (excluding diagonal)
        upper_triangle = corr_matrix.where(
            np.triu(np.ones(corr_matrix.shape), k=1).astype(bool)
        )

        # Average correlation
        avg_correlation = upper_triangle.stack().mean()

        # Maximum correlation
        max_correlation = upper_triangle.stack().max()

        # Find highly correlated pairs (> 0.7)
        highly_correlated = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr = corr_matrix.iloc[i, j]
                if corr > 0.7:
                    highly_correlated.append({
                        'pair': (corr_matrix.columns[i], corr_matrix.columns[j]),
                        'correlation': corr
                    })

        return {
            'avg_correlation': avg_correlation,
            'max_correlation': max_correlation,
            'correlation_matrix': corr_matrix,
            'highly_correlated_pairs': highly_correlated
        }

    def calculate_position_risk(
        self,
        current_prices: Dict[str, float],
        position_sizes: Dict[str, float],
        hedge_ratios: Dict[str, float]
    ) -> Dict:
        """
        Calculate risk metrics for current positions.

        Args:
            current_prices: Dictionary of symbol -> current price
            position_sizes: Dictionary of symbol -> position size
            hedge_ratios: Dictionary of pair_id -> hedge ratio

        Returns:
            Dictionary with position risk metrics
        """
        total_exposure = 0
        gross_exposure = 0
        net_exposure = 0

        for symbol, size in position_sizes.items():
            price = current_prices.get(symbol, 0)
            exposure = abs(size * price)
            gross_exposure += exposure
            net_exposure += size * price

        total_exposure = gross_exposure / 2  # Approximate total exposure

        return {
            'gross_exposure': gross_exposure,
            'net_exposure': net_exposure,
            'total_exposure': total_exposure,
            'leverage': gross_exposure / total_exposure if total_exposure > 0 else 0,
            'num_positions': len(position_sizes),
            'position_details': {
                symbol: {
                    'size': size,
                    'price': current_prices.get(symbol, 0),
                    'exposure': abs(size * current_prices.get(symbol, 0))
                }
                for symbol, size in position_sizes.items()
            }
        }

    def generate_risk_report(
        self,
        returns: pd.Series,
        positions: Optional[Dict[str, float]] = None,
        benchmark_returns: Optional[pd.Series] = None
    ) -> Dict:
        """
        Generate comprehensive risk report.

        Args:
            returns: Portfolio returns
            positions: Optional current positions
            benchmark_returns: Optional benchmark returns

        Returns:
            Dictionary with complete risk report
        """
        risk_metrics = self.calculate_portfolio_risk(returns, benchmark_returns)

        report = {
            'portfolio_risk': {
                'volatility': risk_metrics.volatility,
                'sharpe_ratio': risk_metrics.sharpe_ratio,
                'sortino_ratio': risk_metrics.sortino_ratio,
                'max_drawdown': risk_metrics.max_drawdown,
                'var_95': risk_metrics.var_95,
                'var_99': risk_metrics.var_99,
                'expected_shortfall_95': risk_metrics.expected_shortfall_95,
                'skewness': risk_metrics.skewness,
                'kurtosis': risk_metrics.kurtosis
            },
            'relative_risk': {
                'beta': risk_metrics.beta,
                'tracking_error': risk_metrics.tracking_error,
                'information_ratio': risk_metrics.information_ratio
            } if benchmark_returns is not None else None,
            'position_risk': None,
            'concentration_risk': None,
            'timestamp': datetime.now()
        }

        # Add position risk if positions provided
        if positions:
            total_capital = sum(abs(pos) for pos in positions.values())
            concentration = self.calculate_concentration_risk(positions, total_capital)
            report['concentration_risk'] = concentration

        return report

    def validate_risk_limits(
        self,
        risk_report: Dict,
        limits: Dict[str, float]
    ) -> Dict:
        """
        Validate that risk metrics are within specified limits.

        Args:
            risk_report: Risk report from generate_risk_report
            limits: Dictionary of metric -> limit

        Returns:
            Dictionary with validation results
        """
        violations = []
        warnings = []

        portfolio_risk = risk_report.get('portfolio_risk', {})

        # Check common risk limits
        if 'max_volatility' in limits:
            if portfolio_risk.get('volatility', 0) > limits['max_volatility']:
                violations.append(
                    f"Volatility {portfolio_risk['volatility']:.2f} exceeds limit {limits['max_volatility']}"
                )

        if 'max_drawdown' in limits:
            if abs(portfolio_risk.get('max_drawdown', 0)) > limits['max_drawdown']:
                violations.append(
                    f"Drawdown {abs(portfolio_risk['max_drawdown']):.2f} exceeds limit {limits['max_drawdown']}"
                )

        if 'min_sharpe' in limits:
            if portfolio_risk.get('sharpe_ratio', 0) < limits['min_sharpe']:
                warnings.append(
                    f"Sharpe ratio {portfolio_risk['sharpe_ratio']:.2f} below minimum {limits['min_sharpe']}"
                )

        if 'max_var_95' in limits:
            if abs(portfolio_risk.get('var_95', 0)) > limits['max_var_95']:
                violations.append(
                    f"VaR 95% {abs(portfolio_risk['var_95']):.2f} exceeds limit {limits['max_var_95']}"
                )

        # Check concentration limits
        concentration = risk_report.get('concentration_risk')
        if concentration and 'max_position_weight' in limits:
            if concentration.get('max_position_weight', 0) > limits['max_position_weight']:
                violations.append(
                    f"Max position weight {concentration['max_position_weight']:.2f} exceeds limit {limits['max_position_weight']}"
                )

        return {
            'is_compliant': len(violations) == 0,
            'violations': violations,
            'warnings': warnings,
            'timestamp': datetime.now()
        }
