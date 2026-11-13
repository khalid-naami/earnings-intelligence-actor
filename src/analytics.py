"""
Complete Analytics and Mathematical Engine for Stock Earnings Intelligence.
Fully mirrors all 4 Tabs and UI Components of Dashboard Options:
- Tab 0: Options & Volatility (ATM Straddle, Skew, IV Crush Pathway)
- Tab 1: Gap-Fill & Price Drift (Ledger, 5D Drift, Pathways, EPS Beats, Quarterly Revenue/Income)
- Tab 2: Analyst Targets & Estimates (Targets, Recommendation History, EPS & Revenue Estimates, Upgrades)
- Tab 3: Key Statistics & Valuation (Valuation Measures, Financial Highlights, Mag 7 Peer Matrix)
"""

from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np


def compute_options_expected_move(ticker_obj, current_price: float) -> dict:
    """Calculate front-month ATM Straddle, IV skew, term structure, and modeled IV crush pathway."""
    if not ticker_obj or not current_price or current_price <= 0:
        return {}

    try:
        options = ticker_obj.options
        if not options or len(options) < 1:
            return {}

        near_exp = options[0]
        opt_chain = ticker_obj.option_chain(near_exp)
        calls = opt_chain.calls
        puts = opt_chain.puts
        if calls.empty or puts.empty:
            return {}

        # ATM Strike
        calls['strike_diff'] = (calls['strike'] - current_price).abs()
        atm_idx = calls['strike_diff'].idxmin()
        atm_strike = float(calls.loc[atm_idx]['strike'])

        call_rows = calls[calls['strike'] == atm_strike]
        put_rows = puts[puts['strike'] == atm_strike]
        if call_rows.empty or put_rows.empty:
            return {}

        call_row = call_rows.iloc[0]
        put_row = put_rows.iloc[0]
        call_ask = float(call_row.get('ask', 0.0) or call_row.get('lastPrice', 0.0))
        put_ask = float(put_row.get('ask', 0.0) or put_row.get('lastPrice', 0.0))
        straddle_price = round(call_ask + put_ask, 2)
        implied_move_pct = round((straddle_price / current_price) * 100.0, 2) if current_price > 0 else 0.0

        # Skew (5% OTM Put IV vs 5% OTM Call IV)
        otm_call_strike = atm_strike * 1.05
        otm_put_strike = atm_strike * 0.95
        otm_call_idx = (calls['strike'] - otm_call_strike).abs().idxmin()
        otm_put_idx = (puts['strike'] - otm_put_strike).abs().idxmin()
        call_iv_5 = float(calls.loc[otm_call_idx].get('impliedVolatility', 0.0) or 0.0)
        put_iv_5 = float(puts.loc[otm_put_idx].get('impliedVolatility', 0.0) or 0.0)
        skew_raw = put_iv_5 - call_iv_5
        skew_pct = round(skew_raw * 100.0, 2)

        if skew_raw > 0.05:
            skew_sentiment = "Bearish Sentiment"
            skew_desc = "Bearish Sentiment (Puts carry higher Implied Volatility premium)"
        elif skew_raw < -0.05:
            skew_sentiment = "Bullish Sentiment"
            skew_desc = "Bullish Sentiment (Calls carry higher Implied Volatility premium)"
        else:
            skew_sentiment = "Neutral"
            skew_desc = "Neutral / Balanced"

        # Term Structure
        atm_iv_1 = round(float(calls.loc[atm_idx].get('impliedVolatility', 0.0) or 0.0) * 100.0, 2)
        atm_iv_2 = 0.0
        second_exp = "N/A"
        if len(options) >= 2:
            try:
                second_exp = options[1]
                opt_chain_2 = ticker_obj.option_chain(second_exp)
                calls_2 = opt_chain_2.calls
                if not calls_2.empty:
                    calls_2['strike_diff'] = (calls_2['strike'] - current_price).abs()
                    atm_idx_2 = calls_2['strike_diff'].idxmin()
                    atm_iv_2 = round(float(calls_2.loc[atm_idx_2].get('impliedVolatility', 0.0) or 0.0) * 100.0, 2)
            except Exception:
                pass

        if atm_iv_2 == 0.0:
            atm_iv_2 = round(atm_iv_1 * 0.85, 2)

        iv_crush_spread = round(atm_iv_1 - atm_iv_2, 2)

        # Modeled IV Crush Pathway (-10 days to +5 days)
        modeled_pathway = []
        for d in range(-10, 6):
            if d < 0:
                w = 0.75 + 0.25 * ((10 + d) / 10.0)
                val = atm_iv_1 * w
            elif d == 0:
                val = atm_iv_1
            else:
                decay = np.exp(-0.4 * d)
                val = atm_iv_2 + (atm_iv_1 - atm_iv_2) * 0.25 * decay
            modeled_pathway.append({"day": f"Day {d}", "dayOffset": d, "modeledIVPct": round(float(val), 2)})

        return {
            "atmStrikePrice": atm_strike,
            "atmStraddlePrice": straddle_price,
            "atmCallAsk": call_ask,
            "atmPutAsk": put_ask,
            "impliedMovePct": implied_move_pct,
            "impliedMoveDollar": round(current_price * (implied_move_pct / 100.0), 2),
            "skew": {
                "value": skew_pct,
                "sentiment": skew_sentiment,
                "description": skew_desc
            },
            "termStructure": {
                "frontExpiration": near_exp,
                "frontATMIVPct": atm_iv_1,
                "backExpiration": second_exp,
                "backATMIVPct": atm_iv_2,
                "ivCrushSpreadPct": iv_crush_spread
            },
            "modeledIVCrushPathway": modeled_pathway
        }
    except Exception:
        return {}


def compute_historical_gap_fill_analytics(ticker_obj, earnings_dates_df: pd.DataFrame, quarters_back: int = 8) -> tuple[list[dict], dict, dict, list[dict]]:
    """Compute detailed historical ledger, drift stats, relative price pathways, and EPS surprise history."""
    if earnings_dates_df is None or earnings_dates_df.empty or not ticker_obj:
        return [], {}, {}, []

    results = []
    today = datetime.now(timezone.utc).date()
    past_dates = [d for d in earnings_dates_df.index if d.date() < today]
    dates = past_dates[:quarters_back]
    pathways = {}

    for earnings_dt in dates:
        earn_date = earnings_dt.date()
        start_str = (earn_date - timedelta(days=6)).strftime('%Y-%m-%d')
        end_str = (earn_date + timedelta(days=14)).strftime('%Y-%m-%d')
        try:
            hist = ticker_obj.history(start=start_str, end=end_str)
            if hist.empty:
                continue
            hist.index = pd.to_datetime(hist.index.date)
            earn_datetime = pd.to_datetime(earn_date)

            if earn_datetime in hist.index:
                earn_idx = hist.index.get_loc(earn_datetime)
            else:
                future_dates = hist.index[hist.index >= earn_datetime]
                if not future_dates.empty:
                    earn_idx = hist.index.get_loc(future_dates[0])
                else:
                    continue

            if earn_idx > 0 and (earn_idx + 5) <= len(hist):
                prev_close = float(hist.iloc[earn_idx - 1]['Close'])
                open_react = float(hist.iloc[earn_idx]['Open'])
                close_react = float(hist.iloc[earn_idx]['Close'])
                gap_pct = round(((open_react - prev_close) / prev_close) * 100.0, 2)
                gap_dir = "UP" if gap_pct >= 0 else "DOWN"

                filled = False
                fill_day = -1
                for day_offset in range(0, 6):
                    idx = earn_idx + day_offset
                    day_low = float(hist.iloc[idx]['Low'])
                    day_high = float(hist.iloc[idx]['High'])
                    if gap_dir == "UP":
                        if day_low <= prev_close:
                            filled = True
                            fill_day = day_offset
                            break
                    else:
                        if day_high >= prev_close:
                            filled = True
                            fill_day = day_offset
                            break

                day_5_close = float(hist.iloc[earn_idx + 5]['Close'])
                drift_pct = round(((day_5_close - open_react) / open_react) * 100.0, 2)
                date_str = earn_date.strftime('%Y-%m-%d')

                # Pathway points
                path_pts = []
                for do in range(-1, 6):
                    p_close = float(hist.iloc[earn_idx + do]['Close'])
                    path_pts.append(round((p_close / prev_close) * 100.0, 2))
                pathways[date_str] = path_pts

                exp_eps = float(earnings_dates_df.loc[earnings_dt].get("EPS Estimate") or 0.0)
                rep_eps = float(earnings_dates_df.loc[earnings_dt].get("Reported EPS") or 0.0)
                surprise_pct = float(earnings_dates_df.loc[earnings_dt].get("Surprise(%)") or 0.0)

                results.append({
                    "earningsDate": date_str,
                    "expectedEPS": exp_eps,
                    "reportedEPS": rep_eps,
                    "surprisePct": round(surprise_pct, 2),
                    "beatStatus": "BEAT" if rep_eps >= exp_eps else "MISS",
                    "prevClose": round(prev_close, 2),
                    "openReaction": round(open_react, 2),
                    "postClose": round(close_react, 2),
                    "gapPct": gap_pct,
                    "gapDirection": gap_dir,
                    "gapFillStatus": "Filled" if filled else "Unfilled",
                    "fillReactionDay": f"Day {fill_day}" if filled else "N/A",
                    "drift5DPct": drift_pct
                })
        except Exception:
            continue

    stats = {}
    if results:
        tot = len(results)
        filled_count = sum(1 for r in results if r["gapFillStatus"] == "Filled")
        beats_count = sum(1 for r in results if r["beatStatus"] == "BEAT")
        up_gaps = [r["gapPct"] for r in results if r["gapDirection"] == "UP"]
        down_gaps = [r["gapPct"] for r in results if r["gapDirection"] == "DOWN"]
        drifts = [r["drift5DPct"] for r in results]

        avg_drift = round(float(np.mean(drifts)), 2) if drifts else 0.0
        stats = {
            "totalEarningsAnalyzed": tot,
            "gapFillProbabilityPct": round((filled_count / tot) * 100.0, 1),
            "beatRatePct": round((beats_count / tot) * 100.0, 1),
            "averageGapUpPct": round(float(np.mean(up_gaps)), 2) if up_gaps else 0.0,
            "averageGapDownPct": round(float(np.mean(down_gaps)), 2) if down_gaps else 0.0,
            "average5DDriftPct": avg_drift,
            "postEarningsDriftBias": "Bullish Drift" if avg_drift >= 0 else "Bearish Drift"
        }

    # EPS Surprise History Scatter
    eps_surprise_history = []
    for r in results[:6]:
        eps_surprise_history.append({
            "earningsDate": r["earningsDate"],
            "expectedEPS": r["expectedEPS"],
            "reportedEPS": r["reportedEPS"],
            "surprisePct": r["surprisePct"],
            "beatStatus": r["beatStatus"]
        })

    return results, stats, pathways, eps_surprise_history


def build_earnings_intelligence_record(raw_data: dict, peers_data: list[dict] = None, quarters_back: int = 8) -> dict | None:
    """Build complete JSON record matching all 4 tabs and summary cards of Dashboard Options."""
    if not raw_data:
        return None

    symbol = raw_data["symbol"]
    info = raw_data["info"]
    ticker_obj = raw_data["ticker_obj"]

    # Current Price & Previous Close
    current_price = round(float(info.get("currentPrice") or info.get("regularMarketPrice") or 0.0), 2)
    if current_price <= 0 and ticker_obj:
        try:
            current_price = round(float(ticker_obj.fast_info.get("lastPrice", 0.0)), 2)
        except Exception:
            current_price = 0.0

    prev_close = round(float(info.get("previousClose", current_price) or current_price), 2)
    price_change = round(current_price - prev_close, 2)
    price_change_pct = round((price_change / prev_close) * 100.0, 2) if prev_close > 0 else 0.0

    # Upcoming Earnings Calendar
    calendar = raw_data["calendar"]
    next_earnings_date = "TBD"
    days_until_earnings = None
    if isinstance(calendar, dict) and "Earnings Date" in calendar and calendar["Earnings Date"]:
        first_dt = calendar["Earnings Date"][0]
        if hasattr(first_dt, 'year'):
            next_earnings_date = first_dt.strftime('%Y-%m-%d')
            try:
                target_d = first_dt.date() if hasattr(first_dt, 'date') else first_dt
                days_until_earnings = (target_d - datetime.now(timezone.utc).date()).days
            except Exception:
                pass
        elif isinstance(first_dt, str):
            next_earnings_date = first_dt[:10]
            try:
                target_d = datetime.strptime(next_earnings_date, '%Y-%m-%d').date()
                days_until_earnings = (target_d - datetime.now(timezone.utc).date()).days
            except Exception:
                pass

    # Consensus Recommendations
    recommendation = info.get("recommendationKey", "N/A").replace("_", " ").upper()
    analyst_opinions = info.get("numberOfAnalystOpinions")

    # TAB 0: Options & Volatility Analytics
    tab0_options = compute_options_expected_move(ticker_obj, current_price)

    # TAB 1: Gap-Fill & Price Drift Analytics
    historical_ledger, drift_stats, pathways, eps_surprise_history = compute_historical_gap_fill_analytics(
        ticker_obj, raw_data["earnings_dates"], quarters_back=quarters_back
    )

    # Quarterly Revenue & Net Income (Last 4 quarters)
    q_fin_df = raw_data["quarterly_financials"]
    quarterly_financials = []
    if q_fin_df is not None and not q_fin_df.empty:
        for dt_idx, row in q_fin_df.tail(4).iterrows():
            d_str = dt_idx.strftime('%Y-%m-%d') if hasattr(dt_idx, 'strftime') else str(dt_idx)[:10]
            quarterly_financials.append({
                "date": d_str,
                "totalRevenue": float(row.get('Total Revenue', 0) or 0),
                "netIncome": float(row.get('Net Income', 0) or 0),
                "grossProfit": float(row.get('Gross Profit', 0) or 0) if 'Gross Profit' in row else None
            })

    # TAB 2: Analyst Targets & Estimates
    target_mean = info.get("targetMeanPrice")
    target_median = info.get("targetMedianPrice")
    target_high = info.get("targetHighPrice")
    target_low = info.get("targetLowPrice")
    implied_upside = round(((float(target_mean) - current_price) / current_price) * 100.0, 2) if current_price > 0 and target_mean else None

    # Recommendation History
    recs_df = raw_data["recommendations"]
    recommendation_history = []
    if recs_df is not None and not recs_df.empty:
        for _, row in recs_df.iterrows():
            recommendation_history.append({
                "period": str(row.get("period", "")),
                "strongBuy": int(row.get("strongBuy", 0) or 0),
                "buy": int(row.get("buy", 0) or 0),
                "hold": int(row.get("hold", 0) or 0),
                "sell": int(row.get("sell", 0) or 0),
                "strongSell": int(row.get("strongSell", 0) or 0)
            })

    # EPS & Revenue Estimates
    eps_estimates_table = {}
    eps_est_df = raw_data["eps_estimates"]
    if eps_est_df is not None and not eps_est_df.empty:
        for idx, row in eps_est_df.iterrows():
            eps_estimates_table[str(idx)] = {
                "avg": float(row.get("avg", 0.0) or 0.0) if pd.notna(row.get("avg")) else None,
                "low": float(row.get("low", 0.0) or 0.0) if pd.notna(row.get("low")) else None,
                "high": float(row.get("high", 0.0) or 0.0) if pd.notna(row.get("high")) else None,
                "growth": float(row.get("growth", 0.0) or 0.0) if pd.notna(row.get("growth")) else None
            }

    rev_estimates_table = {}
    rev_est_df = raw_data["rev_estimates"]
    if rev_est_df is not None and not rev_est_df.empty:
        for idx, row in rev_est_df.iterrows():
            rev_estimates_table[str(idx)] = {
                "avg": float(row.get("avg", 0.0) or 0.0) if pd.notna(row.get("avg")) else None,
                "low": float(row.get("low", 0.0) or 0.0) if pd.notna(row.get("low")) else None,
                "high": float(row.get("high", 0.0) or 0.0) if pd.notna(row.get("high")) else None,
                "growth": float(row.get("growth", 0.0) or 0.0) if pd.notna(row.get("growth")) else None
            }

    # Upgrades / Downgrades Ledger
    upgrades_df = raw_data["upgrades"]
    upgrades_history = []
    if upgrades_df is not None and not upgrades_df.empty:
        for dt_idx, row in upgrades_df.head(15).iterrows():
            d_str = dt_idx.strftime('%Y-%m-%d') if hasattr(dt_idx, 'strftime') else str(dt_idx)[:10]
            upgrades_history.append({
                "date": d_str,
                "firm": str(row.get("Firm", "")),
                "action": str(row.get("Action", "")).upper(),
                "toGrade": str(row.get("ToGrade", "")),
                "fromGrade": str(row.get("FromGrade", "")),
                "currentPriceTarget": float(row.get("currentPriceTarget", 0)) if pd.notna(row.get("currentPriceTarget")) else None,
                "priorPriceTarget": float(row.get("priorPriceTarget", 0)) if pd.notna(row.get("priorPriceTarget")) else None
            })

    # TAB 3: Key Statistics & Valuation
    valuation_measures = {
        "marketCap": info.get("marketCap"),
        "enterpriseValue": info.get("enterpriseValue"),
        "trailingPE": round(float(info.get("trailingPE", 0)), 2) if info.get("trailingPE") else None,
        "forwardPE": round(float(info.get("forwardPE", 0)), 2) if info.get("forwardPE") else None,
        "pegRatio": round(float(info.get("pegRatio", 0)), 2) if info.get("pegRatio") else None,
        "priceToSales": round(float(info.get("priceToSalesTrailing12Months", 0)), 2) if info.get("priceToSalesTrailing12Months") else None,
        "priceToBook": round(float(info.get("priceToBook", 0)), 2) if info.get("priceToBook") else None,
        "evToRevenue": round(float(info.get("enterpriseToRevenue", 0)), 2) if info.get("enterpriseToRevenue") else None,
        "evToEbitda": round(float(info.get("enterpriseToEbitda", 0)), 2) if info.get("enterpriseToEbitda") else None
    }

    financial_highlights = {
        "profitMargins": round(float(info.get("profitMargins", 0)) * 100, 2) if info.get("profitMargins") else None,
        "operatingMargins": round(float(info.get("operatingMargins", 0)) * 100, 2) if info.get("operatingMargins") else None,
        "returnOnAssets": round(float(info.get("returnOnAssets", 0)) * 100, 2) if info.get("returnOnAssets") else None,
        "returnOnEquity": round(float(info.get("returnOnEquity", 0)) * 100, 2) if info.get("returnOnEquity") else None,
        "totalRevenue": info.get("totalRevenue"),
        "grossProfits": info.get("grossProfits"),
        "ebitda": info.get("ebitda"),
        "totalCash": info.get("totalCash"),
        "totalDebt": info.get("totalDebt"),
        "operatingCashflow": info.get("operatingCashflow"),
        "freeCashflow": info.get("freeCashflow"),
        "beta": round(float(info.get("beta", 0)), 2) if info.get("beta") else None,
        "fiftyDayAverage": round(float(info.get("fiftyDayAverage", 0)), 2) if info.get("fiftyDayAverage") else None,
        "twoHundredDayAverage": round(float(info.get("twoHundredDayAverage", 0)), 2) if info.get("twoHundredDayAverage") else None
    }

    # Peer Matrix (Mag 7 + Current Ticker)
    peer_matrix = []
    if peers_data:
        peer_matrix = list(peers_data)
        is_in_peers = any(p.get("symbol") == symbol for p in peer_matrix)
        if not is_in_peers:
            peer_matrix.insert(0, {
                "symbol": symbol,
                "name": info.get("shortName", symbol),
                "marketCap": valuation_measures["marketCap"],
                "enterpriseValue": valuation_measures["enterpriseValue"],
                "trailingPE": valuation_measures["trailingPE"],
                "forwardPE": valuation_measures["forwardPE"],
                "pegRatio": valuation_measures["pegRatio"],
                "priceToSales": valuation_measures["priceToSales"],
                "priceToBook": valuation_measures["priceToBook"],
                "evToRevenue": valuation_measures["evToRevenue"],
                "evToEbitda": valuation_measures["evToEbitda"],
                "profitMargin": financial_highlights["profitMargins"]
            })

    # AI Insights Executive Summary
    implied_move_str = f"+/-{tab0_options.get('impliedMovePct')}%" if tab0_options.get("impliedMovePct") else "N/A"
    gap_fill_str = f"{drift_stats.get('gapFillProbabilityPct')}%" if drift_stats.get("gapFillProbabilityPct") is not None else "N/A"
    beat_rate_str = f"{drift_stats.get('beatRatePct')}%" if drift_stats.get("beatRatePct") is not None else "N/A"

    ai_insights = {
        "nextEarningsDate": next_earnings_date,
        "daysUntilEarnings": days_until_earnings,
        "optionsImpliedMove": implied_move_str,
        "gapFillProbability": gap_fill_str,
        "historicalBeatRate": beat_rate_str,
        "postEarningsBias": drift_stats.get("postEarningsDriftBias", "NEUTRAL"),
        "executiveSummary": (
            f"{symbol} ({info.get('shortName', symbol)}) next earnings release is scheduled for {next_earnings_date} "
            f"({f'{days_until_earnings} days away' if days_until_earnings is not None else 'TBD'}). "
            f"Options market prices an expected move of {implied_move_str}. "
            f"Historically over the past {quarters_back} quarters, {symbol} beats earnings estimates {beat_rate_str} of the time, "
            f"fills its post-earnings opening gap {gap_fill_str} of the time, and exhibits a {drift_stats.get('postEarningsDriftBias', 'neutral')} "
            f"with an average 5-day drift of {drift_stats.get('average5DDriftPct', 0.0)}%."
        )
    }

    # Consolidated JSON Item Output
    return {
        "symbol": symbol,
        "companyName": info.get("longName") or info.get("shortName") or symbol,
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        "headerOverview": {
            "currentPrice": current_price,
            "previousClose": prev_close,
            "priceChange": price_change,
            "priceChangePct": price_change_pct,
            "nextScheduledEarnings": next_earnings_date,
            "daysUntilEarnings": days_until_earnings,
            "impliedExpectedMove": implied_move_str,
            "impliedMoveDollar": tab0_options.get("impliedMoveDollar"),
            "analystConsensus": recommendation,
            "analystOpinionsCount": analyst_opinions
        },
        "aiInsights": ai_insights,
        "tab0_optionsAndVolatility": tab0_options,
        "tab1_gapFillAndPriceDrift": {
            "gapFillStats": drift_stats,
            "normalizedPricePathways": pathways,
            "detailedHistoricalLedger": historical_ledger,
            "epsSurpriseHistory": eps_surprise_history,
            "quarterlyFinancials": quarterly_financials
        },
        "tab2_analystTargetsAndEstimates": {
            "priceTargetSummary": {
                "targetMean": target_mean,
                "targetMedian": target_median,
                "targetHigh": target_high,
                "targetLow": target_low,
                "impliedUpsidePct": implied_upside
            },
            "recommendationHistory": recommendation_history,
            "consensusEPSEstimates": eps_estimates_table,
            "revenueEstimates": rev_estimates_table,
            "topRatingsActions": upgrades_history
        },
        "tab3_keyStatisticsAndValuation": {
            "valuationMeasures": valuation_measures,
            "financialHighlights": financial_highlights,
            "peerValuationComparisonMatrix": peer_matrix
        }
    }
