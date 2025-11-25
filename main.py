"""
Main entry point - runs the scan and emails any signals.
"""

from typing import List

from config import TICKERS
from emailer import send_email
from signals import analyze_stock_trend, pick_option_for_trend


def build_email(signals: List[dict]) -> str:
    rows = []
    for s in signals:
        proj_return = (
            f"{s['projected_return_pct']:.1f}%" if s.get("projected_return_pct") is not None else "n/a"
        )
        row = f"""
        <tr>
          <td>{s['ticker']}</td>
          <td>{s['trend']}</td>
          <td>{s.get('underlying_price', 'n/a')}</td>
          <td>{s['option_symbol']}</td>
          <td>{s['contract_type']}</td>
          <td>{s['strike_price']}</td>
          <td>{s['expiration_date']}</td>
          <td>{s['delta']:.2f}</td>
          <td>{s['open_interest']}</td>
          <td>{s['mark']:.2f}</td>
          <td>{proj_return}</td>
        </tr>
        """
        rows.append(row)

    rows_html = "\n".join(rows)
    html = f"""
    <html>
      <body>
        <h2>Options Signal Bot</h2>
        <p>Here are the latest candidates from the Massive.com data scan.</p>
        <table border="1" cellpadding="4" cellspacing="0">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Trend</th>
              <th>Underlying</th>
              <th>Option</th>
              <th>Type</th>
              <th>Strike</th>
              <th>Expiry</th>
              <th>Delta</th>
              <th>Open Interest</th>
              <th>Mark</th>
              <th>Projected Return</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </body>
    </html>
    """
    return html


def run() -> None:
    signals_found = []

    for ticker in TICKERS:
        trend_info = analyze_stock_trend(ticker)
        if trend_info.get("trend") not in {"bullish", "bearish"}:
            continue
        best_contract = pick_option_for_trend(ticker, trend_info)
        if best_contract:
            signals_found.append(best_contract)

    if not signals_found:
        return

    subject = "Options Signal Bot - Massive scan"
    body = build_email(signals_found)
    send_email(subject, body)


if __name__ == "__main__":
    run()
