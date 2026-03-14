"""
Trend Analyzer
==============

Pure computation module: takes OHLCV DataFrame, returns ML-ready trend metrics.
No API calls, no side effects. All trend horizons computed from a single candle dataset.

Metrics per timeframe:
  - ROC (Rate of Change)
  - Linear regression slope (normalized %/day)
  - R-squared (trend consistency)
  - RSI (momentum oscillator)
  - Volatility (annualized)
  - ATR % (average true range as % of price)
  - SMA distance % (price position vs moving average)
  - Regime bin (categorical: strong_bullish → strong_bearish + consolidating)
  - Volatility regime bin (low / normal / high / extreme)
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

# Regime classification thresholds
ROC_STRONG_THRESHOLD = 8.0
ROC_WEAK_THRESHOLD = 2.0
R2_CLEAN_TREND = 0.5

HORIZONS = {
    "short_term": 5,
    "medium_term": 22,
    "long_term": None,
}


def _adaptive_period(window_size: int, default: int = 14) -> int:
    """Scale indicator period to window size so short windows still produce values."""
    return max(2, min(default, window_size - 1))


def compute_rsi(close: pd.Series, period: int = 14) -> float:
    period = _adaptive_period(len(close), period)
    if len(close) < period + 1:
        return 50.0

    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))

    avg_gain = gain.rolling(window=period, min_periods=period).mean().iloc[-1]
    avg_loss = loss.rolling(window=period, min_periods=period).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def compute_atr_pct(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    period = _adaptive_period(len(close), period)
    if len(close) < period + 1:
        hl_range = (high - low).mean()
        current = close.iloc[-1]
        return round((hl_range / current) * 100, 4) if current > 0 else 0.0

    hl = high - low
    hc = (high - close.shift()).abs()
    lc = (low - close.shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean().iloc[-1]

    current = close.iloc[-1]
    if current == 0:
        return 0.0
    return round((atr / current) * 100, 4)


def compute_linear_regression(close: pd.Series) -> tuple[float, float]:
    """Returns (slope_pct_per_day, r_squared)."""
    if len(close) < 3:
        return 0.0, 0.0

    y = close.values.astype(float)
    x = np.arange(len(y), dtype=float)

    slope, intercept = np.polyfit(x, y, 1)

    y_pred = slope * x + intercept
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    mean_price = y.mean()
    slope_pct = (slope / mean_price) * 100 if mean_price > 0 else 0.0

    return round(slope_pct, 4), round(max(0.0, r_squared), 4)


def classify_regime(roc: float, r_squared: float, rsi: float) -> str:
    """
    Classify into one of 7 regimes for ML consumption:
      strong_bullish, bullish, weak_bullish,
      consolidating,
      weak_bearish, bearish, strong_bearish
    """
    abs_roc = abs(roc)

    if abs_roc < ROC_WEAK_THRESHOLD and r_squared < R2_CLEAN_TREND:
        return "consolidating"

    if roc > 0:
        if abs_roc >= ROC_STRONG_THRESHOLD and r_squared >= R2_CLEAN_TREND:
            return "strong_bullish"
        elif abs_roc >= ROC_WEAK_THRESHOLD:
            return "bullish"
        else:
            return "weak_bullish"
    else:
        if abs_roc >= ROC_STRONG_THRESHOLD and r_squared >= R2_CLEAN_TREND:
            return "strong_bearish"
        elif abs_roc >= ROC_WEAK_THRESHOLD:
            return "bearish"
        else:
            return "weak_bearish"


def classify_volatility(annualized_vol: float) -> str:
    if annualized_vol < 10:
        return "low"
    elif annualized_vol < 25:
        return "normal"
    elif annualized_vol < 45:
        return "high"
    return "extreme"


def analyze_horizon(candles: pd.DataFrame, n_days: Optional[int], current_price: float) -> Dict[str, Any]:
    """Compute all trend metrics for one timeframe window."""
    if n_days is not None and len(candles) > n_days:
        window = candles.tail(n_days).copy()
    else:
        window = candles.copy()

    if len(window) < 2:
        return {"error": "insufficient_data", "candles_used": len(window)}

    close = window["Close"]
    high = window["High"]
    low = window["Low"]

    start_price = float(close.iloc[0])
    end_price = float(close.iloc[-1])

    roc = ((end_price - start_price) / start_price) * 100
    slope_pct, r_squared = compute_linear_regression(close)

    daily_returns = close.pct_change().dropna()
    vol_daily = float(daily_returns.std()) if len(daily_returns) > 1 else 0.0
    vol_annualized = vol_daily * np.sqrt(252) * 100

    rsi = compute_rsi(close)
    atr_pct = compute_atr_pct(high, low, close)

    sma = float(close.mean())
    sma_distance_pct = ((current_price - sma) / sma) * 100 if sma > 0 else 0.0

    regime = classify_regime(roc, r_squared, rsi)
    vol_regime = classify_volatility(vol_annualized)

    return {
        "roc": round(roc, 2),
        "slope_per_day": slope_pct,
        "r_squared": r_squared,
        "rsi": rsi,
        "volatility_annualized": round(vol_annualized, 2),
        "atr_pct": atr_pct,
        "sma": round(sma, 2),
        "sma_distance_pct": round(sma_distance_pct, 2),
        "period_high": round(float(high.max()), 2),
        "period_low": round(float(low.min()), 2),
        "regime": regime,
        "volatility_regime": vol_regime,
        "candles_used": len(window),
    }


def analyze_candles(candles: pd.DataFrame, current_price: float) -> Optional[Dict[str, Dict[str, Any]]]:
    """
    Main entry point: compute trend analysis for all horizons from one candle set.

    Args:
        candles: DataFrame with columns Open, High, Low, Close, Volume (3mo daily)
        current_price: latest price from quote data

    Returns:
        Dict with keys short_term, medium_term, long_term — each containing
        raw metrics + categorical bins for ML consumption. None if data is unusable.
    """
    if candles is None or candles.empty or len(candles) < 3:
        return None

    result = {}
    for horizon_name, n_days in HORIZONS.items():
        analysis = analyze_horizon(candles, n_days, current_price)
        if "error" in analysis:
            result[horizon_name] = None
        else:
            result[horizon_name] = analysis

    return result
