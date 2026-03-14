#!/usr/bin/env python3
"""
Verify /health and /api/v1/global-context (including multi-timeframe trend).
Usage: python scripts/verify_global_context.py [BASE_URL]
Default BASE_URL: http://localhost:8285 (staging)
"""
import json
import sys
import urllib.request

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8285").rstrip("/")


def main():
    errors = []

    # Health
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=10) as r:
            health = json.loads(r.read().decode())
        if health.get("status") != "healthy":
            errors.append(f"Health status: {health.get('status')}")
        else:
            print(f"Health: {health['status']} (yahoo_finance={health.get('yahoo_finance_available')})")
    except Exception as e:
        errors.append(f"Health request failed: {e}")
        print("Health: FAIL", file=sys.stderr)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            sys.exit(1)
        sys.exit(1)

    # Global context + trend structure
    try:
        with urllib.request.urlopen(f"{BASE_URL}/api/v1/global-context", timeout=60) as r:
            data = json.loads(r.read().decode())
    except Exception as e:
        errors.append(f"Global-context request failed: {e}")
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)

    required_keys = ["sp500", "nasdaq", "dow_jones", "vix", "gold", "usd_inr", "crude_oil", "timestamp"]
    for k in required_keys:
        if k not in data:
            errors.append(f"Missing key: {k}")

    def price_or_rate(obj, key):
        if key == "vix":
            return obj.get("value")
        if key == "usd_inr":
            return obj.get("rate")
        return obj.get("price")

    trend_fields = [
        "regime", "roc", "rsi", "volatility_regime", "slope_per_day", "r_squared",
        "volatility_annualized", "atr_pct", "sma_distance_pct", "candles_used",
    ]
    valid_regimes = [
        "strong_bullish", "bullish", "weak_bullish", "consolidating",
        "weak_bearish", "bearish", "strong_bearish",
    ]
    valid_vol = ["low", "normal", "high", "extreme"]

    for key in required_keys:
        if key == "timestamp":
            continue
        d = data[key]
        p = price_or_rate(d, key)
        if p is None:
            errors.append(f"{key}: missing value/rate/price")
        trend = d.get("trend")
        if not trend:
            errors.append(f"{key}: missing trend")
        else:
            for horizon in ["short_term", "medium_term", "long_term"]:
                t = trend.get(horizon)
                if t is None:
                    errors.append(f"{key}.trend.{horizon}: missing")
                else:
                    for f in trend_fields:
                        if f not in t:
                            errors.append(f"{key}.trend.{horizon}.{f}: missing")
                    if t.get("regime") not in valid_regimes:
                        errors.append(f"{key}.trend.{horizon}.regime invalid: {t.get('regime')}")
                    if t.get("volatility_regime") not in valid_vol:
                        errors.append(
                            f"{key}.trend.{horizon}.volatility_regime invalid: {t.get('volatility_regime')}"
                        )

    if errors:
        print("Verification FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    print("Global-context: OK (all keys and trend structure valid)")
    print("\n--- Trend summary ---")
    for key in ["sp500", "nasdaq", "dow_jones", "vix", "gold", "usd_inr", "crude_oil"]:
        d = data[key]
        p = price_or_rate(d, key)
        st = d["trend"]["short_term"]["regime"]
        mt = d["trend"]["medium_term"]["regime"]
        lt = d["trend"]["long_term"]["regime"]
        print(f"  {key}: value={p} | short={st}, medium={mt}, long={lt}")
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
