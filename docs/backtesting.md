# Backtesting Documentation

## Overview

This document explains the backtesting engine implementation in the StatArb-N50 platform, including methodology, performance metrics, and best practices for historical strategy validation.

## 1. Backtesting Engine Architecture

### Components

**Core Engine:**
- `BacktestEngine`: Main backtesting class
- `BacktestConfig`: Configuration parameters
- `Trade`: Trade record structure
- `PositionType`: Position state management

**Data Flow:**
```
Historical Data → Signal Generation → Trade Execution → P&L Calculation
→ Performance Metrics → Risk Analysis → Results Storage
```

### Configuration

**BacktestConfig Parameters:**
```python
@dataclass
class BacktestConfig:
    start_date: datetime
    end_date: datetime
    initial_capital: float
    entry_z_score: float
    exit_z_score: float
    stop_z_score: float
    max_holding_period: int
    transaction_cost: float
    slippage: float
    position_sizing: str
    correlation_threshold: float
    coint_p_value: float
```

**Default Values:**
- Entry Z-score: 2.0
- Exit Z-score: 0.0
- Stop Z-score: 4.0
- Max holding period: 30 days
- Transaction cost: 0.1%
- Slippage: 0.05%
- Position sizing: equal_weight

## 2. Signal Generation in Backtesting

### Historical Signal Calculation

**Step-by-Step Process:**

1. **Data Alignment:**
   - Align price series for both assets
   - Ensure same observation dates
   - Handle missing data

2. **Parameter Calculation:**
   - Calculate hedge ratio using historical data
   - Calculate rolling statistics
   - Use lookback windows only

3. **Spread Calculation:**
   - `Spread_t = Price_A_t - Hedge_Ratio × Price_B_t`
   - Calculate rolling mean and std
   - Compute Z-score

4. **Signal Generation:**
   - Compare Z-score to thresholds
   - Generate LONG/SHORT/EXIT signals
   - Track position state

**Implementation:**
```python
def generate_historical_signals(prices_a, prices_b, config):
    """
    Generate historical trading signals.
    """
    signals = []

    for date in prices_a.index:
        # Get historical data up to this date
        hist_a = prices_a[:date]
        hist_b = prices_b[:date]

        # Calculate parameters using only historical data
        hedge_ratio = calculate_hedge_ratio(hist_a, hist_b)
        spread = calculate_spread(hist_a, hist_b, hedge_ratio)
        z_score = calculate_z_score(spread)

        # Generate signal
        signal = signal_engine.generate_signal(
            z_score[-1],
            entry_threshold=config.entry_z_score,
            exit_threshold=config.exit_z_score
        )

        signals.append({
            'date': date,
            'z_score': z_score[-1],
            'signal': signal,
            'hedge_ratio': hedge_ratio
        })

    return signals
```

## 3. Trade Execution

### Position Management

**Position States:**
- `None`: No position
- `LONG`: Long spread (buy A, sell B)
- `SHORT`: Short spread (sell A, buy B)

**Entry Logic:**

**LONG SPREAD Entry:**
```python
if signal == "LONG SPREAD" and current_position is None:
    # Enter position
    position_a = calculate_position_size(capital, price_a, price_b, hedge_ratio)
    position_b = -position_a * hedge_ratio

    # Apply slippage
    price_a_slipped = apply_slippage(price_a, "LONG")
    price_b_slipped = apply_slippage(price_b, "SHORT")

    # Calculate transaction cost
    cost = calculate_transaction_cost(position_a, price_a_slipped, position_b, price_b_slipped)

    # Update capital
    capital -= cost

    # Record trade
    record_trade("ENTRY", "LONG", date, price_a_slipped, price_b_slipped, cost)
```

**SHORT SPREAD Entry:**
```python
if signal == "SHORT SPREAD" and current_position is None:
    # Enter position
    position_a = -calculate_position_size(capital, price_a, price_b, hedge_ratio)
    position_b = -position_a * hedge_ratio

    # Apply slippage
    price_a_slipped = apply_slippage(price_a, "SHORT")
    price_b_slipped = apply_slippage(price_b, "LONG")

    # Calculate transaction cost
    cost = calculate_transaction_cost(position_a, price_a_slipped, position_b, price_b_slipped)

    # Update capital
    capital -= cost

    # Record trade
    record_trade("ENTRY", "SHORT", date, price_a_slipped, price_b_slipped, cost)
```

**Exit Logic:**

**EXIT Signal:**
```python
if signal == "EXIT" and current_position is not None:
    # Exit position
    price_a_slipped = apply_slippage(price_a, "SHORT" if current_position == "LONG" else "LONG")
    price_b_slipped = apply_slippage(price_b, "LONG" if current_position == "LONG" else "SHORT")

    # Calculate P&L
    pnl = calculate_pnl(position_a, price_a, price_a_slipped, position_b, price_b, price_b_slipped)

    # Calculate transaction cost
    cost = calculate_transaction_cost(position_a, price_a_slipped, position_b, price_b_slipped)

    # Update capital
    capital += pnl - cost

    # Record trade
    record_trade("EXIT", current_position, date, price_a_slipped, price_b_slipped, cost, pnl)

    # Reset position
    current_position = None
```

**Stop-Loss Exit:**
```python
if abs(z_score) > stop_z_score and current_position is not None:
    # Exit due to stop-loss
    exit_with_reason("STOP-LOSS")
```

**Max Holding Period Exit:**
```python
if holding_period >= max_holding_period and current_position is not None:
    # Exit due to max holding period
    exit_with_reason("MAX_HOLDING_PERIOD")
```

## 4. P&L Calculation

### Mark-to-Market P&L

**Formula:**
```
MTM_PnL = Position_A × (Current_Price_A - Entry_Price_A) +
         Position_B × (Current_Price_B - Entry_Price_B)
```

**Implementation:**
```python
def calculate_mtm_pnl(position_a, entry_price_a, current_price_a,
                     position_b, entry_price_b, current_price_b):
    """
    Calculate mark-to-market P&L.
    """
    pnl_a = position_a * (current_price_a - entry_price_a)
    pnl_b = position_b * (current_price_b - entry_price_b)
    return pnl_a + pnl_b
```

### Realized P&L

**Formula:**
```
Realized_PnL = Exit_MTM_PnL - Transaction_Costs
```

**Implementation:**
```python
def calculate_realized_pnl(entry_trade, exit_trade):
    """
    Calculate realized P&L from closed position.
    """
    # Calculate MTM P&L at exit
    mtm_pnl = calculate_mtm_pnl(
        entry_trade.position_a, entry_trade.price_a, exit_trade.price_a,
        entry_trade.position_b, entry_trade.price_b, exit_trade.price_b
    )

    # Subtract transaction costs
    total_cost = entry_trade.cost + exit_trade.cost
    realized_pnl = mtm_pnl - total_cost

    return realized_pnl
```

## 5. Transaction Costs

### Cost Model

**Percentage-Based Cost:**
```
Cost = (|Position_A| × Price_A + |Position_B| × Price_B) × Cost_Percentage
```

**Implementation:**
```python
def calculate_transaction_cost(position_a, price_a, position_b, price_b, cost_pct):
    """
    Calculate transaction cost based on notional value.
    """
    notional_a = abs(position_a * price_a)
    notional_b = abs(position_b * price_b)
    total_notional = notional_a + notional_b
    cost = total_notional * cost_pct
    return cost
```

**Typical Costs:**
- Brokerage: 0.05-0.15%
- STT (Securities Transaction Tax): 0.025%
- Exchange fees: 0.003-0.005%
- GST: 18% on brokerage and fees
- Total: ~0.1-0.2%

## 6. Slippage Model

### Slippage Implementation

**Buy Slippage:**
```
Price_with_slippage = Price × (1 + Slippage_Percentage)
```

**Sell Slippage:**
```
Price_with_slippage = Price × (1 - Slippage_Percentage)
```

**Implementation:**
```python
def apply_slippage(price, direction, slippage_pct):
    """
    Apply slippage to price.
    """
    if direction == "LONG":
        return price * (1 + slippage_pct)
    else:  # SHORT
        return price * (1 - slippage_pct)
```

**Typical Slippage:**
- Liquid stocks: 0.01-0.05%
- Less liquid stocks: 0.05-0.15%
- Large orders: Higher slippage

## 7. Position Sizing

### Equal Weight

**Formula:**
```
Position_Size = Capital / Number_of_Active_Pairs
```

**Implementation:**
```python
def calculate_equal_weight_position(capital, num_pairs):
    """
    Calculate equal-weight position size.
    """
    return capital / num_pairs
```

### Volatility-Adjusted

**Formula:**
```
Position_Size = Capital × (Target_Volatility / Pair_Volatility)
```

**Implementation:**
```python
def calculate_volatility_adjusted_position(capital, pair_volatility, target_volatility):
    """
    Calculate volatility-adjusted position size.
    """
    return capital * (target_volatility / pair_volatility)
```

### Risk Parity

**Formula:**
```
Position_Size_i = Capital × (1 / σ_i²) / Σ(1 / σ_j²)
```

**Implementation:**
```python
def calculate_risk_parity_positions(capital, volatilities):
    """
    Calculate risk parity position sizes.
    """
    weights = [(1 / v**2) for v in volatilities]
    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]
    positions = [capital * w for w in normalized_weights]
    return positions
```

## 8. Performance Metrics

### Return Metrics

**Total Return:**
```python
def calculate_total_return(initial_capital, final_capital):
    """
    Calculate total return.
    """
    return (final_capital - initial_capital) / initial_capital
```

**CAGR:**
```python
def calculate_cagr(initial_capital, final_capital, years):
    """
    Calculate Compound Annual Growth Rate.
    """
    return (final_capital / initial_capital) ** (1 / years) - 1
```

### Risk Metrics

**Volatility:**
```python
def calculate_volatility(returns):
    """
    Calculate standard deviation of returns.
    """
    return np.std(returns)
```

**Sharpe Ratio:**
```python
def calculate_sharpe_ratio(returns, risk_free_rate=0.02):
    """
    Calculate Sharpe ratio.
    """
    excess_returns = returns - risk_free_rate / 252
    return np.mean(excess_returns) / np.std(excess_returns)
```

**Sortino Ratio:**
```python
def calculate_sortino_ratio(returns, risk_free_rate=0.02):
    """
    Calculate Sortino ratio (downside deviation).
    """
    excess_returns = returns - risk_free_rate / 252
    downside_returns = excess_returns[excess_returns < 0]
    downside_deviation = np.std(downside_returns)
    return np.mean(excess_returns) / downside_deviation
```

### Drawdown Metrics

**Maximum Drawdown:**
```python
def calculate_max_drawdown(equity_curve):
    """
    Calculate maximum drawdown.
    """
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    return drawdown.min()
```

**Drawdown Duration:**
```python
def calculate_drawdown_duration(equity_curve):
    """
    Calculate maximum drawdown duration.
    """
    peak = equity_curve.cummax()
    drawdown = equity_curve < peak
    drawdown_duration = 0
    max_duration = 0

    for dd in drawdown:
        if dd:
            drawdown_duration += 1
            max_duration = max(max_duration, drawdown_duration)
        else:
            drawdown_duration = 0

    return max_duration
```

### VaR and Expected Shortfall

**VaR:**
```python
def calculate_var(returns, confidence=0.95):
    """
    Calculate Value at Risk.
    """
    return np.percentile(returns, (1 - confidence) * 100)
```

**Expected Shortfall:**
```python
def calculate_expected_shortfall(returns, confidence=0.95):
    """
    Calculate Expected Shortfall (CVaR).
    """
    var = calculate_var(returns, confidence)
    tail_returns = returns[returns <= var]
    return np.mean(tail_returns)
```

## 9. Trade Metrics

### Win Rate

**Formula:**
```
Win_Rate = Number_of_Winning_Trades / Total_Number_of_Trades
```

**Implementation:**
```python
def calculate_win_rate(trades):
    """
    Calculate win rate.
    """
    winning_trades = sum(1 for t in trades if t.pnl > 0)
    return winning_trades / len(trades)
```

### Profit Factor

**Formula:**
```
Profit_Factor = Total_Profit / Total_Loss
```

**Implementation:**
```python
def calculate_profit_factor(trades):
    """
    Calculate profit factor.
    """
    profits = sum(t.pnl for t in trades if t.pnl > 0)
    losses = abs(sum(t.pnl for t in trades if t.pnl < 0))
    return profits / losses if losses > 0 else float('inf')
```

### Average Trade Return

**Formula:**
```
Avg_Trade_Return = Sum_of_All_Trade_PnL / Number_of_Trades
```

**Implementation:**
```python
def calculate_avg_trade_return(trades):
    """
    Calculate average trade return.
    """
    return np.mean([t.pnl for t in trades])
```

### Average Holding Period

**Formula:**
```
Avg_Holding_Period = Sum_of_Holding_Periods / Number_of_Trades
```

**Implementation:**
```python
def calculate_avg_holding_period(trades):
    """
    Calculate average holding period.
    """
    return np.mean([t.holding_period for t in trades])
```

## 10. Equity Curve

**Construction:**
```python
def construct_equity_curve(trades, initial_capital):
    """
    Construct equity curve from trades.
    """
    equity = [initial_capital]

    for trade in trades:
        if trade.type == "EXIT":
            equity.append(equity[-1] + trade.pnl - trade.cost)

    return pd.Series(equity)
```

**Visualization:**
- Plot equity curve over time
- Show drawdown periods
- Compare to benchmark
- Show cumulative returns

## 11. Look-Ahead Bias Prevention

### Critical Rules

**1. Use Only Historical Data:**
```python
# WRONG: Uses future data
hedge_ratio = calculate_hedge_ratio(all_data_a, all_data_b)

# RIGHT: Uses only historical data
hedge_ratio_t = calculate_hedge_ratio(data_a[:t], data_b[:t])
```

**2. Apply Signals to Next Period:**
```python
# WRONG: Signal applied to same period
signal_t = generate_signal(z_score_t)
execute_trade(signal_t, price_t)

# RIGHT: Signal applied to next period
signal_t = generate_signal(z_score_t)
execute_trade(signal_t, price_{t+1})
```

**3. No Training on Future Data:**
```python
# WRONG: Parameters trained on full dataset
params = optimize_parameters(all_data)

# RIGHT: Parameters trained on historical data only
params_t = optimize_parameters(data[:t])
```

### Validation

**Checklist:**
- [ ] All calculations use rolling windows
- [ ] Parameters estimated from historical data only
- [ ] Signals applied to next period
- [ ] No future information in feature engineering
- [ ] Backtest reproduces with same seed

## 12. Data Leakage Prevention

### Common Sources of Leakage

**1. Global Statistics:**
- Using mean/std of entire dataset
- Using min/max of entire dataset
- Using global correlations

**2. Preprocessing Leakage:**
- Normalization using global parameters
- Imputation using global statistics
- Feature selection using entire dataset

**3. Target Leakage:**
- Including future prices in features
- Using target-derived features
- Look-ahead in target calculation

### Prevention Strategies

**1. Strict Temporal Splitting:**
```python
def temporal_split(data, split_date):
    """
    Split data by date.
    """
    train = data[data.index < split_date]
    test = data[data.index >= split_date]
    return train, test
```

**2. Rolling Window Calculations:**
```python
def rolling_calculate(data, func, window):
    """
    Apply function using rolling window.
    """
    return data.rolling(window=window).apply(func)
```

**3. Pipeline Validation:**
```python
def validate_no_leakage(train, test):
    """
    Validate no data leakage.
    """
    assert train.index.max() < test.index.min()
    assert not any(train.index.isin(test.index))
```

## 13. Monte Carlo Simulation

### Purpose

- Test strategy robustness
- Generate confidence intervals
- Assess parameter sensitivity

### Implementation

```python
def monte_carlo_simulation(returns, num_simulations=1000):
    """
    Perform Monte Carlo simulation on returns.
    """
    simulated_returns = []

    for _ in range(num_simulations):
        # Randomly sample returns with replacement
        simulated = np.random.choice(returns, size=len(returns), replace=True)
        simulated_returns.append(simulated)

    return simulated_returns
```

### Analysis

```python
def analyze_simulations(simulated_returns):
    """
    Analyze Monte Carlo simulation results.
    """
    final_returns = [sim.sum() for sim in simulated_returns]

    mean_return = np.mean(final_returns)
    std_return = np.std(final_returns)
    percentile_5 = np.percentile(final_returns, 5)
    percentile_95 = np.percentile(final_returns, 95)

    return {
        'mean': mean_return,
        'std': std_return,
        'percentile_5': percentile_5,
        'percentile_95': percentile_95
    }
```

## 14. Sensitivity Analysis

### Parameter Sensitivity

**Test Parameter Ranges:**
- Entry Z-score: 1.5 to 3.0
- Exit Z-score: -0.5 to 0.5
- Stop Z-score: 3.0 to 5.0
- Holding period: 10 to 60 days
- Transaction cost: 0.05% to 0.3%

**Implementation:**
```python
def sensitivity_analysis(config, parameter_ranges):
    """
    Perform sensitivity analysis on parameters.
    """
    results = {}

    for param, values in parameter_ranges.items():
        param_results = []

        for value in values:
            test_config = config.copy()
            setattr(test_config, param, value)
            result = run_backtest(test_config)
            param_results.append(result)

        results[param] = param_results

    return results
```

### Heatmap Visualization

**Performance Heatmap:**
- X-axis: Entry Z-score
- Y-axis: Exit Z-score
- Color: Sharpe ratio or total return

## 15. Benchmark Comparison

### Benchmarks

**Nifty 50 Index:**
- Buy and hold Nifty 50
- Same period as backtest
- Calculate returns and risk metrics

**Random Strategy:**
- Random entry/exit signals
- Same transaction costs
- Performance baseline

**Buy and Hold:**
- Hold constituent stocks
- Equal-weight portfolio
- No trading

### Comparison Metrics

```python
def compare_to_benchmark(strategy_returns, benchmark_returns):
    """
    Compare strategy to benchmark.
    """
    strategy_metrics = calculate_metrics(strategy_returns)
    benchmark_metrics = calculate_metrics(benchmark_returns)

    comparison = {
        'excess_return': strategy_metrics['total_return'] - benchmark_metrics['total_return'],
        'information_ratio': calculate_information_ratio(strategy_returns, benchmark_returns),
        'tracking_error': calculate_tracking_error(strategy_returns, benchmark_returns)
    }

    return comparison
```

## 16. Backtesting Best Practices

### Do's

1. **Use realistic transaction costs**
   - Include all fees and taxes
   - Model slippage appropriately
   - Consider market impact for large orders

2. **Prevent look-ahead bias**
   - Use rolling windows
   - Apply signals to next period
   - Validate with out-of-sample data

3. **Test multiple parameter sets**
   - Perform sensitivity analysis
   - Test robustness across regimes
   - Avoid overfitting to in-sample data

4. **Use sufficient data**
   - Minimum 3-5 years of data
   - Include different market conditions
   - Ensure statistical significance

5. **Document assumptions**
   - Clearly state all assumptions
   - Document parameter choices
   - Explain calculation methods

### Don'ts

1. **Don't overfit parameters**
   - Don't optimize to death
   - Don't use too many parameters
   - Don't ignore out-of-sample performance

2. **Don't ignore transaction costs**
   - Don't assume zero-cost trading
   - Don't underestimate slippage
   - Don't ignore market impact

3. **Don't use future information**
   - Don't train on full dataset
   - Don't use global statistics
   - Don't apply signals to same period

4. **Don't cherry-pick periods**
   - Don't select only profitable periods
   - Don't ignore drawdown periods
   - Don't exclude market crashes

5. **Don't overstate results**
   - Don't claim guaranteed profits
   - Don't ignore risk metrics
   - Don't hide limitations

## 17. Interpretation of Results

### What Good Results Look Like

**Return:**
- Positive total return
- Higher than benchmark
- Consistent across periods

**Risk:**
- Acceptable volatility
- Limited drawdowns
- Reasonable Sharpe ratio (>1.0)

**Robustness:**
- Stable across parameter ranges
- Works in different market conditions
- Not sensitive to specific periods

### What Bad Results Look Like

**Return:**
- Negative total return
- Lower than benchmark
- Inconsistent across periods

**Risk:**
- High volatility
- Large drawdowns
- Low Sharpe ratio (<0.5)

**Robustness:**
- Unstable across parameters
- Fails in certain conditions
- Sensitive to specific periods

## 18. Reporting

### Backtest Report Structure

**1. Summary:**
- Strategy description
- Test period
- Key metrics (return, Sharpe, drawdown)

**2. Performance:**
- Equity curve
- Return metrics
- Risk metrics
- Benchmark comparison

**3. Trades:**
- Number of trades
- Win rate
- Profit factor
- Average holding period

**4. Analysis:**
- Sensitivity analysis
- Monte Carlo results
- Parameter robustness

**5. Limitations:**
- Assumptions
- Known issues
- Potential improvements

## Conclusion

The backtesting engine provides a robust framework for historical strategy validation. By following best practices for look-ahead bias prevention, transaction cost modeling, and performance measurement, the platform generates honest and reproducible backtest results suitable for academic evaluation and strategy development.
