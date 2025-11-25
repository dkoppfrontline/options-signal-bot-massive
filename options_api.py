"""
Massive.com API helpers for stocks and options.
"""

import datetime as dt
from typing import Dict, Any, List, Optional

import pandas as pd
import requests

from config import MASSIVE_API_KEY, MASSIVE_BASE_URL, LOOKBACK_DAYS, TIMEOUT_SECONDS, DEBUG


def _get(url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Internal helper to call Massive with the correct Authorization header.
    """
    if params is None:
        params = {}

    headers = {
        "Authorization": f"Bearer {MASSIVE_API_KEY}",
        "accept": "application/json",
    }

    resp = requests.get(url, params=params, headers=headers, timeout=TIMEOUT_SECONDS)
    if DEBUG:
        print("GET", resp.url, "status", resp.status_code)
        try:
            print("Body preview:", resp.text[:200])
        except Exception:
            pass
    resp.raise_for_status()
    return resp.json()


def get_stock_history_daily(ticker: str, days: int = LOOKBACK_DAYS) -> pd.DataFrame:
    """
    Fetch daily OHLC data for a stock using Massive aggregates endpoint.
    """
    end_date = dt.date.today()
    # Pull extra history to account for weekends and holidays
    start_date = end_date - dt.timedelta(days=days * 2)

    url = f"{MASSIVE_BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}"
    data = _get(url, params={"adjusted": "true", "sort": "asc", "limit": 5000})

    results = data.get("results", [])
    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)
    # "t" is the timestamp in ms since epoch
    df["timestamp"] = pd.to_datetime(df["t"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df.rename(
        columns={
            "o": "open",
            "h": "high",
            "l": "low",
            "c": "close",
            "v": "volume",
        }
    )
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
    Massive returns an `underlying_asset` object per contract in many responses.
    """
    for contract in chain:
        underlying = contract.get("underlying_asset") or {}
        session = underlying.get("session") or {}
        close_price = session.get("close_price")
        if close_price is not None:
            try:
                return float(close_price)
            except (TypeError, ValueError):
                pass

        last_trade = underlying.get("last_trade") or {}
        price = last_trade.get("price")
        if price is not None:
            try:
                return float(price)
            except (TypeError, ValueError):
                pass

    return None


def parse_option_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a Massive option snapshot record into a simpler dict.
    """
    details = contract.get("details") or {}
    greeks = contract.get("greeks") or {}
    last_quote = contract.get("last_quote") or {}
    last_trade = contract.get("last_trade") or {}

    bid = last_quote.get("bid_price")
    ask = last_quote.get("ask_price")
    mark = None

    if bid is not None and ask is not None and ask > 0:
        try:
            mark = (float(bid) + float(ask)) / 2.0
        except (TypeError, ValueError):
            mark = None
    else:
        price = last_trade.get("price")
        if price is not None:
            try:
                mark = float(price)
            except (TypeError, ValueError):
                mark = None

    try:
        strike_price = float(details.get("strike_price")) if details.get("strike_price") is not None else None
    except (TypeError, ValueError):
        strike_price = None

    try:
        oi = int(contract.get("open_interest") or 0)
    except (TypeError, ValueError):
        oi = 0

    def _float_or_none(val):
        try:
            return float(val) if val is not None else None
        except (TypeError, ValueError):
            return None

    return {
        "symbol": details.get("ticker") or details.get("symbol"),
        "contract_type": details.get("contract_type"),
        "expiration_date": details.get("expiration_date"),
        "strike_price": strike_price,
        "delta": _float_or_none(greeks.get("delta")),
        "theta": _float_or_none(greeks.get("theta")),
        "gamma": _float_or_none(greeks.get("gamma")),
        "vega": _float_or_none(greeks.get("vega")),
        "implied_volatility": _float_or_none(contract.get("implied_volatility")),
        "open_interest": oi,
        "mark": mark,
    }
