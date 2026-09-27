"""
Data Fetcher for Stock Earnings, Options Chains, Financial Estimates, and Peers.
"""

import logging
import pandas as pd
import numpy as np
import yfinance as yf
from src.constants import MAG_7_TICKERS

logger = logging.getLogger(__name__)


def fetch_stock_raw_data(ticker_symbol: str) -> dict | None:
    """Fetch complete ticker details, options, earnings dates, and financial estimates."""
    ticker_symbol = ticker_symbol.upper().strip()
    ticker = yf.Ticker(ticker_symbol)

    try:
        info = ticker.info
        if not info or len(info) < 5:
            fast = ticker.fast_info
            if not fast:
                return None
            info = {
                "symbol": ticker_symbol,
                "shortName": ticker_symbol,
                "currentPrice": fast.get("lastPrice", 0.0),
                "marketCap": fast.get("marketCap", 0)
            }
    except Exception as e:
        logger.debug(f"Error fetching info for {ticker_symbol}: {e}")
        info = {"symbol": ticker_symbol, "shortName": ticker_symbol}

    # Calendar
    calendar = {}
    try:
        cal = ticker.calendar
        if isinstance(cal, dict):
            calendar = cal
        elif isinstance(cal, pd.DataFrame) and not cal.empty:
            calendar = cal.to_dict()
    except Exception:
        pass

    # Earnings Dates History
    earnings_dates = pd.DataFrame()
    try:
        ed = ticker.earnings_dates
        if ed is not None and not ed.empty:
            earnings_dates = ed
    except Exception:
        pass

    # Analyst Recommendations
    recs = pd.DataFrame()
    try:
        r = ticker.recommendations
        if r is not None and not r.empty:
            recs = r
    except Exception:
        pass

    # Upgrades / Downgrades
    upgrades = pd.DataFrame()
    try:
        up = ticker.upgrades_downgrades
        if up is not None and not up.empty:
            upgrades = up
    except Exception:
        pass

    # Consensus Estimates
    eps_est = pd.DataFrame()
    try:
        ee = ticker.earnings_estimate
        if ee is not None and not ee.empty:
            eps_est = ee
    except Exception:
        pass

    rev_est = pd.DataFrame()
    try:
        re = ticker.revenue_estimate
        if re is not None and not re.empty:
            rev_est = re
    except Exception:
        pass

    # Quarterly Financials
    q_financials = pd.DataFrame()
    try:
        qf = ticker.quarterly_financials
        if qf is not None and not qf.empty:
            q_fin_t = qf.T
            cols = [c for c in ['Total Revenue', 'Net Income', 'Operating Income', 'Gross Profit'] if c in q_fin_t.columns]
            if cols:
                q_financials = q_fin_t[cols].dropna()
    except Exception:
        pass

    return {
        "ticker_obj": ticker,
        "symbol": ticker_symbol,
        "info": info,
        "calendar": calendar,
        "earnings_dates": earnings_dates,
        "recommendations": recs,
        "upgrades": upgrades,
        "eps_estimates": eps_est,
        "rev_estimates": rev_est,
        "quarterly_financials": q_financials
    }


def fetch_mag_7_peers() -> list[dict]:
    """Fetch complete valuation measures for the Magnificent Seven benchmark."""
    data = []
    for sym in MAG_7_TICKERS:
        try:
            t = yf.Ticker(sym)
            info = t.info
            data.append({
                "symbol": sym,
                "name": info.get("shortName", sym),
                "marketCap": info.get("marketCap"),
                "enterpriseValue": info.get("enterpriseValue"),
                "trailingPE": round(float(info.get("trailingPE", 0)), 2) if info.get("trailingPE") else None,
                "forwardPE": round(float(info.get("forwardPE", 0)), 2) if info.get("forwardPE") else None,
                "pegRatio": round(float(info.get("pegRatio", 0)), 2) if info.get("pegRatio") else None,
                "priceToSales": round(float(info.get("priceToSalesTrailing12Months", 0)), 2) if info.get("priceToSalesTrailing12Months") else None,
                "priceToBook": round(float(info.get("priceToBook", 0)), 2) if info.get("priceToBook") else None,
                "evToRevenue": round(float(info.get("enterpriseToRevenue", 0)), 2) if info.get("enterpriseToRevenue") else None,
                "evToEbitda": round(float(info.get("enterpriseToEbitda", 0)), 2) if info.get("enterpriseToEbitda") else None,
                "profitMargin": round(float(info.get("profitMargins", 0)) * 100, 2) if info.get("profitMargins") else None
            })
        except Exception:
            pass
    return data
