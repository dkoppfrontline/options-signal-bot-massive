"""
Signal logic - combine indicators and options data to generate trade ideas.
"""

import datetime as dt
from typing import Dict, Any, Optional

import pandas as pd

from config import (
    MA_SHORT,
    MA_LONG,
    RSI_PERIOD,
    MIN_DTE,
    MAX_DTE,
    TARGET_DELTA_CALL,
    TARGET_DELTA_PUT,
    MIN_OPEN_INTEREST,
)
from indicators import sma, rsi
from options_api import (
    get_stock_history_daily,
    get_option_chain_snapshot,
    extract_underlying_price_from_chain,
    parse_option_contract,
)


def analyze_stock_trend(ticker: str) -> Dict[str, Any]:
    """
    Compute basic trend indicators for a stock.
    Returns dict with trend and last values.
    """
    df = get_stock_history_daily(ticker)
    if df.empty or "close" not in df.columns:
        return {"trend": "no_data"}

    closes = df["close"]
    ma_short = sma(closes, MA_SHORT)
    ma_long = sma(closes, MA_LONG)
    rsi_vals = rsi(closes, RSI_PERIOD)

    latest = df.index[-1]
    latest_close = float(closes.iloc[-1])
    latest_sma_short = float(ma_short.iloc[-1])
    latest_sma_long = float(ma_long.iloc[-1])
    latest_rsi = float(rsi_vals.iloc[-1])

    if latest_sma_short > latest_sma_long and 40 <= latest_rsi <= 70:
        trend = "bullish"
    elif latest_sma_short < latest_sma_long and 30 <= latest_rsi <= 60:
        trend = "bearish"
    else:
        trend = "neutral"

    return {
        "trend": trend,
        "latest_close": latest_close,
        "sma_short": latest_sma_short,
        "sma_long": latest_sma_long,
        "rsi": latest_rsi,
        "as_of": latest,
    }


def _days_to_expiry(expiration_date: str) -> Optional[int]:
    try:
        exp = dt.datetime.strptime(expiration_date, "%Y-%m-%d").date()
        today = dt.date.today()
        return (exp - today).days
    except Exception:
        return None


def pick_option_for_trend(ticker: str, trend_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    For a bullish or bearish trend, pick a single options contract from Massive data.
    """
    trend = trend_info.get("trend")
    if trend not in {"bullish", "bearish"}:
        return None

    contract_type = "call" if trend == "bullish" else "put"
    chain = get_option_chain_snapshot(ticker, contract_type=contract_type)
    if not chain:
        return None

    underlying_price = extract_underlying_price_from_chain(chain) or trend_info.get("latest_close")

    # Normalize and filter contracts
    parsed = []
    for raw in chain:
        c = parse_option_contract(raw)
        if not c.get("expiration_date") or c.get("strike_price") is None:
            continue
        dte = _days_to_expiry(c["expiration_date"])
        if dte is None or dte < MIN_DTE or dte > MAX_DTE:
            continue
        if c["open_interest"] < MIN_OPEN_INTEREST:
            continue
        if c["delta"] is None or c["mark"] is None or c["mark"] <= 0:
            continue
        parsed.append({**c, "dte": dte})

    if not parsed:
        return None

    # Choose delta target
    target_delta = TARGET_DELTA_CALL if contract_type == "call" else TARGET_DELTA_PUT

    def delta_distance(c: Dict[str, Any]) -> float:
        return abs((c["delta"] or 0) - target_delta)

    parsed.sort(key=lambda c: (delta_distance(c), c["dte"]))

    best = parsed[0]

    # Simple projected profitability: assume 5 percent move in underlying
    move_pct = 0.05
    if trend == "bearish":
        move_pct = -0.05

    projected_underlying_change = underlying_price * move_pct if underlying_price is not None else None
    projected_option_change = None
    projected_return_pct = None

    if underlying_price is not None and best["mark"]:
        projected_option_change = (best["delta"] or 0) * projected_underlying_change
        projected_return_pct = (projected_option_change / best["mark"]) * 100.0

    return {
        "ticker": ticker,
        "trend": trend,
        "underlying_price": underlying_price,
        "option_symbol": best["symbol"],
        "contract_type": best["contract_type"],
        "strike_price": best["strike_price"],
        "expiration_date": best["expiration_date"],
        "delta": best["delta"],
        "open_interest": best["open_interest"],
        "mark": best["mark"],
        "dte": best["dte"],
        "projected_underlying_change": projected_underlying_change,
        "projected_option_change": projected_option_change,
        "projected_return_pct": projected_return_pct,
    }
