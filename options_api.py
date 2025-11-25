"""
Massive.com API helpers for stocks and options.
"""

import datetime as dt
from typing import Dict, Any, List, Optional

import pandas as pd
import requests

from config import MASSIVE_API_KEY, MASSIVE_BASE_URL, LOOKBACK_DAYS, TIMEOUT_SECONDS, DEBUG


def _get(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if params is None:
        params = {}
    # Massive supports apiKey in query string
    params.setdefault("apiKey", MASSIVE_API_KEY)

    resp = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
    if DEBUG:
        print("GET", resp.url, "status", resp.status_code)
    resp.raise_for_status()
    return resp.json()


def get_stock_history_daily(ticker: str, days: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """Fetch daily OHLC data for a stock using Massive custom bars endpoint."""
    end_date = dt.date.today()
    # Pull a bit more history to account for weekends and holidays
    start_date = end_date - dt.timedelta(days=days * 2)

    url = f"{MASSIVE_BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}"
    data = _get(url, params={"adjusted": "true", "sort": "asc", "limit": 5000})

    results = data.get("results", [])
    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    df["timestamp"] = pd.to_datetime(df["t"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df.rename(columns={"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
    # Keep only the last `days` rows
    df = df.tail(days)
    return df


def get_option_chain_snapshot(ticker: str, contract_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch options chain snapshot for an underlying ticker.

    contract_type: "call", "put" or None for both.
    """
    url = f"{MASSIVE_BASE_URL}/v3/snapshot/options/{ticker}"
    params: Dict[str, Any] = {"limit": 250}
    if contract_type:
        params["contract_type"] = contract_type.lower()

    data = _get(url, params=params)
    return data.get("results", []) or []


def extract_underlying_price_from_chain(chain: List[Dict[str, Any]]) -> Optional[float]:
    """
    Try to read the underlying stock price from any option record.
    Massive returns an `underlying_asset` object per contract.
    """
    for contract in chain:
        underlying = contract.get("underlying_asset") or {}
        session = underlying.get("session") or {}
        close_price = session.get("close_price")
        if close_price is not None:
            return float(close_price)

        last_trade = underlying.get("last_trade") or {}
        price = last_trade.get("price")
        if price is not None:
            return float(price)
    return None


def parse_option_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a Massive option snapshot record into a simpler dict."""
    details = contract.get("details") or {}
    greeks = contract.get("greeks") or {}
    last_quote = contract.get("last_quote") or {}
    last_trade = contract.get("last_trade") or {}

    bid = last_quote.get("bid_price")
    ask = last_quote.get("ask_price")
    mark = None

    if bid is not None and ask is not None and ask > 0:
        mark = (bid + ask) / 2.0
    else:
        price = last_trade.get("price")
        if price is not None:
            mark = float(price)

    return {
        "symbol": details.get("ticker") or details.get("symbol"),
        "contract_type": details.get("contract_type"),
        "expiration_date": details.get("expiration_date"),
        "strike_price": float(details.get("strike_price")) if details.get("strike_price") is not None else None,
        "delta": float(greeks.get("delta")) if greeks.get("delta") is not None else None,
        "theta": float(greeks.get("theta")) if greeks.get("theta") is not None else None,
        "gamma": float(greeks.get("gamma")) if greeks.get("gamma") is not None else None,
        "vega": float(greeks.get("vega")) if greeks.get("vega") is not None else None,
        "implied_volatility": float(contract.get("implied_volatility"))
        if contract.get("implied_volatility") is not None
        else None,
        "open_interest": int(contract.get("open_interest") or 0),
        "mark": mark,
    }
