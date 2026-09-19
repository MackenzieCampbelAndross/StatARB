# Quantitative Methodology Documentation

## Overview

This document explains the mathematical and statistical methods used in the StatArb-N50 platform for statistical arbitrage research on Nifty 50 equities.

## 1. Statistical Arbitrage Strategy

### Core Concept

Statistical arbitrage is a quantitative trading strategy that identifies and exploits temporary price inefficiencies between related securities. The strategy is based on the mean-reversion property of asset pairs that historically move together.

**Key Assumptions:**
- Asset pairs exhibit cointegration (long-term equilibrium relationship)
- Short-term deviations from equilibrium will revert to the mean
- The relationship is statistically significant and stable over time

**Strategy Pipeline:**
```
Market Data → Data Cleaning → Pair Generation → Correlation Filter
→ Engle-Granger Cointegration → Hedge Ratio → Spread → Z-Score
→ Trading Signal → Backtesting → Risk Analytics
```

## 2. Correlation Analysis

### Pearson Correlation Coefficient

**Formula:**
```
ρ = Cov(X, Y) / (σ_X × σ_Y)
```

Where:
- `Cov(X, Y)` = Σ[(X_i - μ_X)(Y_i - μ_Y)] / (n - 1)
- `σ_X` = Standard deviation of X
- `σ_Y` = Standard deviation of Y
- `μ_X` = Mean of X
- `μ_Y` = Mean of Y
- `n` = Number of observations

**Interpretation:**
- `ρ = 1`: Perfect positive correlation
- `ρ = -1`: Perfect negative correlation
- `ρ = 0`: No linear correlation

**Implementation:**
```python
def calculate_pearson_correlation(series_a, series_b):
    """
    Calculate Pearson correlation coefficient between two series.
    """
    # Calculate covariance
    covariance = np.cov(series_a, series_b, ddof=1)[0, 1]

    # Calculate standard deviations
    std_a = np.std(series_a, ddof=1)
    std_b = np.std(series_b, ddof=1)

    # Calculate correlation
    correlation = covariance / (std_a * std_b)

    return correlation
```

**Usage in Platform:**
- Pre-filter pairs before expensive cointegration testing
- Default threshold: 0.70 (configurable)
- Lookback period: 30 days (configurable)
- Helps reduce computational load

## 3. Engle-Granger Cointegration

### Two-Step Procedure

**Step 1: OLS Regression**

**Formula:**
```
Y_t = α + βX_t + ε_t
```

Where:
- `Y_t` = Price of asset Y at time t
- `X_t` = Price of asset X at time t
- `α` = Intercept (constant term)
- `β` = Hedge ratio (slope coefficient)
- `ε_t` = Residual (spread) at time t

**Hedge Ratio (β):**
```
β = Cov(X, Y) / Var(X)
```

**Step 2: Augmented Dickey-Fuller (ADF) Test**

Test the residuals `ε_t` for stationarity using the ADF test.

**ADF Test Model:**
```
Δε_t = α + γε_{t-1} + Σ(δ_i Δε_{t-i}) + η_t
```

Where:
- `Δε_t` = First difference of residuals
- `γ` = Coefficient to test (γ < 0 indicates stationarity)
- `δ_i` = Lag coefficients
- `η_t` = White noise error term

**Null Hypothesis (H0):**
- γ = 0 (Residuals have a unit root, not stationary)

**Alternative Hypothesis (H1):**
- γ < 0 (Residuals are stationary)

**Decision Rule:**
- If p-value < significance level (e.g., 0.05): Reject H0
- Conclusion: Residuals are stationary → Pairs are cointegrated

**Implementation:**
```python
def engle_granger_cointegration(series_a, series_b, significance=0.05):
    """
    Perform Engle-Granger two-step cointegration test.
    """
    # Step 1: OLS regression
    X = sm.add_constant(series_b)
    model = sm.OLS(series_a, X).fit()
    alpha = model.params[0]
    beta = model.params[1]  # Hedge ratio
    residuals = model.resid

    # Step 2: ADF test on residuals
    adf_result = adfuller(residuals)

    # Determine cointegration
    is_cointegrated = adf_result[1] < significance

    return {
        'alpha': alpha,
        'hedge_ratio': beta,
        'residuals': residuals,
        'adf_statistic': adf_result[0],
        'adf_p_value': adf_result[1],
        'is_cointegrated': is_cointegrated
    }
```

**Critical Values:**
- Significance level: 0.05 (default, configurable)
- Critical values depend on sample size
- More stringent thresholds reduce false positives

## 4. Spread Calculation

### Spread Formula

**Definition:**
The spread is the residual from the OLS regression, representing the deviation from the long-term equilibrium relationship.

**Formula:**
```
S_t = Y_t - (α + βX_t)
```

Simplified (assuming α ≈ 0):
```
S_t = Y_t - βX_t
```

Where:
- `S_t` = Spread at time t
- `Y_t` = Price of asset Y at time t
- `X_t` = Price of asset X at time t
- `β` = Hedge ratio

**Interpretation:**
- `S_t > 0`: Asset Y is overvalued relative to X
- `S_t < 0`: Asset Y is undervalued relative to X
- `S_t ≈ 0`: Assets are in equilibrium

**Rolling Statistics:**

**Rolling Mean:**
```
μ_t = (1/n) × Σ(S_{t-i}) for i = 0 to n-1
```

**Rolling Standard Deviation:**
```
σ_t = √[(1/n) × Σ(S_{t-i} - μ_t)²] for i = 0 to n-1
```

**Implementation:**
```python
def calculate_spread(series_a, series_b, hedge_ratio):
    """
    Calculate spread using hedge ratio.
    """
    spread = series_a - hedge_ratio * series_b
    return spread

def calculate_rolling_statistics(spread, window=20):
    """
    Calculate rolling mean and standard deviation.
    """
    rolling_mean = spread.rolling(window=window).mean()
    rolling_std = spread.rolling(window=window).std()
    return pd.DataFrame({
        'rolling_mean': rolling_mean,
        'rolling_std': rolling_std
    })
```

## 5. Z-Score Calculation

### Z-Score Formula

**Definition:**
The Z-score standardizes the spread to indicate how many standard deviations it is from its mean.

**Formula:**
```
Z_t = (S_t - μ_t) / σ_t
```

Where:
- `Z_t` = Z-score at time t
- `S_t` = Spread at time t
- `μ_t` = Rolling mean of spread
- `σ_t` = Rolling standard deviation of spread

**Interpretation:**
- `Z_t > +2`: Spread is significantly high → Short spread opportunity
- `Z_t < -2`: Spread is significantly low → Long spread opportunity
- `Z_t ≈ 0`: Spread is at equilibrium → Exit position

**Signal Generation:**
```python
def generate_signal(z_score, entry_threshold=2.0, exit_threshold=0.0):
    """
    Generate trading signal based on Z-score.
    """
    if z_score > entry_threshold:
        return "SHORT SPREAD"
    elif z_score < -entry_threshold:
        return "LONG SPREAD"
    elif abs(z_score) < exit_threshold:
        return "EXIT"
    else:
        return "WATCH"
```

**Implementation:**
```python
def calculate_z_score(spread, rolling_mean, rolling_std):
    """
    Calculate Z-score of spread.
    """
    # Avoid division by zero
    rolling_std = rolling_std.replace(0, np.nan)

    # Calculate Z-score
    z_score = (spread - rolling_mean) / rolling_std

    # Handle infinity
    z_score = z_score.replace([np.inf, -np.inf], np.nan)

    return z_score
```

## 6. Half-Life of Mean Reversion

### Ornstein-Uhlenbeck Process

**Stochastic Differential Equation:**
```
dS_t = -λ(S_t - μ)dt + σdW_t
```

Where:
- `S_t` = Spread at time t
- `μ` = Long-term mean of spread
- `λ` = Speed of mean reversion
- `σ` = Volatility
- `W_t` = Wiener process (Brownian motion)

**Discrete Version:**
```
S_{t+1} - S_t = -λ(S_t - μ) + ε_t
```

**Half-Life Formula:**
```
Half-Life = ln(2) / λ
```

**Estimation via Regression:**
```
ΔS_t = α + βS_{t-1} + ε_t
```

Where:
- `β = -λ`
- `Half-Life = -ln(2) / β`

**Interpretation:**
- Shorter half-life = Faster mean reversion = Better trading opportunity
- Longer half-life = Slower mean reversion = Higher holding period risk

**Implementation:**
```python
def calculate_half_life(spread, method="regression"):
    """
    Calculate half-life of mean reversion.
    """
    if method == "regression":
        # Calculate first differences
        delta_spread = spread.diff().dropna()
        lagged_spread = spread.shift(1).dropna()

        # Align data
        delta_spread = delta_spread[1:]
        lagged_spread = lagged_spread[1:]

        # Regression: ΔS_t = α + βS_{t-1} + ε_t
        X = sm.add_constant(lagged_spread)
        model = sm.OLS(delta_spread, X).fit()
        beta = model.params[1]

        # Calculate half-life
        half_life = -np.log(2) / beta

        return {
            'half_life': half_life,
            'lambda': -beta,
            'beta': beta
        }
```

## 7. Signal Generation

### Signal Types

**LONG SPREAD:**
- Z-score falls below negative entry threshold (e.g., -2)
- Buy asset Y, sell asset X
- Expect spread to increase toward mean

**SHORT SPREAD:**
- Z-score rises above positive entry threshold (e.g., +2)
- Sell asset Y, buy asset X
- Expect spread to decrease toward mean

**EXIT:**
- Z-score crosses exit threshold (e.g., 0)
- Close position
- Take profit or stop loss

**WATCH:**
- Z-score between thresholds
- No action
- Monitor for signal changes

### Entry Thresholds

**Default Configuration:**
- Entry Z-score: ±2.0 (configurable)
- Exit Z-score: ±0.0 (configurable)
- Stop-loss Z-score: ±4.0 (configurable)
- Maximum holding period: 30 days (configurable)

**Risk-Adjusted Thresholds:**
- Higher thresholds = Fewer signals, higher confidence
- Lower thresholds = More signals, lower confidence
- Thresholds should be optimized via backtesting

### Confidence Scoring

**Confidence Factors:**
- Z-score magnitude (stronger deviation = higher confidence)
- Correlation strength (higher correlation = higher confidence)
- Cointegration p-value (lower p-value = higher confidence)
- Half-life (shorter half-life = higher confidence)

**Implementation:**
```python
def calculate_confidence(z_score, correlation, coint_p_value, half_life):
    """
    Calculate signal confidence score.
    """
    # Normalize factors
    z_confidence = min(abs(z_score) / 2.0, 1.0)
    corr_confidence = abs(correlation)
    coint_confidence = 1.0 - coint_p_value
    hl_confidence = 1.0 / (1.0 + half_life / 10.0)

    # Weighted average
    confidence = (
        0.3 * z_confidence +
        0.2 * corr_confidence +
        0.3 * coint_confidence +
        0.2 * hl_confidence
    )

    return confidence
```

## 8. Performance Metrics

### Return Metrics

**Total Return:**
```
Total Return = (Final Value - Initial Value) / Initial Value
```

**Compound Annual Growth Rate (CAGR):**
```
CAGR = (Final Value / Initial Value)^(1/n) - 1
```
Where `n` = number of years

**Daily Return:**
```
Daily Return_t = (Equity_t - Equity_{t-1}) / Equity_{t-1}
```

### Risk Metrics

**Volatility (Standard Deviation):**
```
σ = √[(1/n) × Σ(R_t - μ_R)²]
```
Where `R_t` = Daily return, `μ_R` = Mean daily return

**Annualized Volatility:**
```
σ_annual = σ_daily × √252
```

### Risk-Adjusted Returns

**Sharpe Ratio:**
```
Sharpe = (μ_R - R_f) / σ
```
Where:
- `μ_R` = Mean daily return
- `R_f` = Risk-free rate (e.g., 0.02/252 for 2% annual)
- `σ` = Daily volatility

**Annualized Sharpe:**
```
Sharpe_annual = Sharpe_daily × √252
```

**Sortino Ratio:**
```
Sortino = (μ_R - R_f) / σ_downside
```
Where `σ_downside` = Standard deviation of negative returns only

### Drawdown Metrics

**Drawdown:**
```
Drawdown_t = (Peak_t - Equity_t) / Peak_t
```

**Maximum Drawdown:**
```
Max Drawdown = max(Drawdown_t)
```

**Drawdown Duration:**
```
Duration = Time from peak to recovery
```

### Value at Risk (VaR)

**Historical VaR:**
```
VaR_α = α-quantile of historical returns
```

For 95% VaR:
```
VaR_95 = 5th percentile of daily returns
```

**Expected Shortfall (CVaR):**
```
ES_α = Mean of returns below VaR_α
```

## 9. Backtesting Methodology

### Look-Ahead Bias Prevention

**Principle:**
A model must never use information from the future to generate historical signals.

**Implementation:**
1. Use rolling windows for all calculations
2. Calculate parameters using only historical data
3. Apply signals to next period only
4. No training on future data

**Example:**
```
# INCORRECT: Uses entire dataset for hedge ratio
beta = calculate_hedge_ratio(all_data_a, all_data_b)

# CORRECT: Uses only historical data for hedge ratio
beta_t = calculate_hedge_ratio(data_a[:t], data_b[:t])
```

### Transaction Costs

**Cost Model:**
```
Cost = (Position_A × Price_A + Position_B × Price_B) × Cost_Percentage
```

**Implementation:**
```python
def calculate_transaction_cost(position_a, price_a, position_b, price_b, cost_pct):
    """
    Calculate transaction cost.
    """
    notional = abs(position_a * price_a) + abs(position_b * price_b)
    cost = notional * cost_pct
    return cost
```

**Slippage:**
```
Price_with_slippage = Price × (1 ± Slippage_Percentage)
```
- Buy: `+` (worse price)
- Sell: `-` (worse price)

### Position Sizing

**Equal Weight:**
```
Position_Size = Capital / Number_of_Pairs
```

**Volatility-Adjusted:**
```
Position_Size = Capital × (Target_Volatility / Pair_Volatility)
```

**Risk Parity:**
```
Position_Size = Capital × (1 / Volatility²) / Σ(1 / Volatility²)
```

## 10. Walk-Forward Validation

### Window Structure

**Training Window:**
- Parameter estimation period
- Used to calculate hedge ratio, thresholds, etc.
- Not used for performance evaluation

**Testing Window:**
- Out-of-sample period
- Uses parameters from training window
- Performance evaluation period

**Rolling Window:**
```
Window 1: Train [0-100], Test [100-125]
Window 2: Train [25-125], Test [125-150]
Window 3: Train [50-150], Test [150-175]
...
```

**Step Size:**
- Can be equal to testing window (no overlap)
- Can be smaller (overlap windows)

### Performance Comparison

**In-Sample vs Out-of-Sample:**
```
Performance_Degradation = (IS_Return - OS_Return) / IS_Return
```

**Overfitting Detection:**
- Large degradation → Overfitting
- Small degradation → Robust model
- Negative degradation → Out-of-sample outperforms (unlikely)

## 11. Risk Limit Validation

### Volatility Limit

```
if Portfolio_Volatility > Max_Volatility:
    Reduce_Positions or Add_Hedge
```

### Drawdown Limit

```
if Current_Drawdown > Max_Drawdown:
    Stop_Trading or Reduce_Exposure
```

### Concentration Limit

```
if Max_Position_Weight > Max_Weight:
    Diversify_Positions
```

### Correlation Limit

```
if Portfolio_Correlation > Max_Correlation:
    Reduce_Exposure or Add_Hedge
```

## 12. Assumptions and Limitations

### Key Assumptions

1. **Cointegration Stability:**
   - Cointegration relationship remains stable over time
   - May break down during market regime changes

2. **Mean Reversion:**
   - Spreads will revert to mean
   - May not hold during market stress

3. **Stationarity:**
   - Statistical properties remain constant
   - May not hold in changing market conditions

4. **No Transaction Costs in Tests:**
   - Costs are modeled but may underestimate real costs
   - Slippage may be higher in practice

### Limitations

1. **Survivorship Bias:**
   - Current Nifty 50 universe used for historical testing
   - Does not account for dropped constituents
   - Historical constituent data not yet implemented

2. **Look-Ahead Bias Risk:**
   - Rolling windows mitigate but do not eliminate risk
   - Parameter leakage possible if not careful

3. **Market Impact:**
   - Assumes no market impact from trades
   - May not hold for large positions

4. **Liquidity Assumptions:**
   - Assumes sufficient liquidity for all pairs
   - May not hold for less liquid stocks

5. **Model Risk:**
   - Statistical models may not capture all market dynamics
   - Black swan events not modeled

## 13. References

**Academic Sources:**
- Engle, R. F., & Granger, C. W. (1987). "Co-integration and error correction: representation, estimation, and testing." Econometrica.
- Johansen, S. (1988). "Statistical analysis of cointegration vectors." Journal of Economic Dynamics and Control.
- Banerjee, A., et al. (1993). "Cointegration, Error Correction, and the Econometric Analysis of Non-Stationary Data." Oxford University Press.

**Practical References:**
- Chan, E. P. (2013). "Algorithmic Trading: Winning Strategies and Their Rationale." Wiley.
- Lopez de Prado, M. (2018). "Advances in Financial Machine Learning." Wiley.
- Ehrman, D. (2006). "The Handbook of Pairs Trading." Wiley.

## Conclusion

The quantitative methodology is based on well-established statistical techniques. The platform implements these methods with careful attention to avoiding look-ahead bias, proper parameter estimation, and honest performance evaluation. All assumptions and limitations are documented transparently for academic evaluation.
