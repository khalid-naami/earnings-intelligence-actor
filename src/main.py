"""
Main Apify Actor Entry Point for Stock Earnings Intelligence & Volatility Analysis.
"""

import asyncio
import logging
from apify import Actor
from src.constants import MAG_7_TICKERS
from src.fetcher import fetch_stock_raw_data, fetch_mag_7_peers
from src.analytics import build_earnings_intelligence_record

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    async with Actor:
        actor_input = await Actor.get_input() or {}

        # Parse stock symbols input (default: Mag 7)
        raw_symbols = actor_input.get("symbols", MAG_7_TICKERS)
        if isinstance(raw_symbols, str):
            symbols = [s.strip().upper() for s in raw_symbols.replace(",", "\n").splitlines() if s.strip()]
        elif isinstance(raw_symbols, list):
            symbols = [str(s).strip().upper() for s in raw_symbols if str(s).strip()]
        else:
            symbols = MAG_7_TICKERS

        if not symbols:
            symbols = MAG_7_TICKERS

        include_peers = actor_input.get("includePeerComparison", True)

        Actor.log.info(f"Starting Earnings Intelligence analysis for {len(symbols)} symbol(s)...")
        Actor.log.info(f"Target Symbols: {symbols}")

        # Fetch Mag 7 peer benchmark if requested
        mag_7_peers = []
        if include_peers:
            try:
                Actor.log.info("Fetching Magnificent Seven valuation benchmark...")
                mag_7_peers = fetch_mag_7_peers()
            except Exception as e:
                Actor.log.warning(f"Could not fetch Mag 7 peer data: {e}")

        dataset_items = []
        summary_records = []

        for symbol in symbols:
            Actor.log.info(f"Processing ticker: {symbol} ...")
            try:
                raw_data = fetch_stock_raw_data(symbol)
                if not raw_data:
                    Actor.log.warning(f"Could not fetch raw data for ticker '{symbol}'. Skipping.")
                    continue

                record = build_earnings_intelligence_record(raw_data, peers_data=mag_7_peers)
                if not record:
                    Actor.log.warning(f"Insufficient calculation data for '{symbol}'. Skipping.")
                    continue

                # Push record to Apify Dataset
                await Actor.push_data(record)
                dataset_items.append(record)

                summary_records.append({
                    "symbol": record["symbol"],
                    "company": record["companyName"],
                    "currentPrice": f"${record['headerOverview']['currentPrice']}",
                    "nextEarningsDate": record["headerOverview"]["nextScheduledEarnings"],
                    "daysUntil": record["headerOverview"]["daysUntilEarnings"],
                    "optionsImpliedMove": record["aiInsights"]["optionsImpliedMove"],
                    "gapFillProb": record["aiInsights"]["gapFillProbability"],
                    "beatRate": record["aiInsights"]["historicalBeatRate"],
                    "bias": record["aiInsights"]["postEarningsBias"]
                })

                Actor.log.info(f"Successfully processed {symbol} (Next Earnings: {record['headerOverview']['nextScheduledEarnings']}, Move: {record['aiInsights']['optionsImpliedMove']})")

            except Exception as e:
                Actor.log.error(f"Error processing {symbol}: {str(e)}")

        # Save High-Level Summary to Key-Value Store for AI / MCP consumption
        if dataset_items:
            output_summary = {
                "totalStocksAnalyzed": len(dataset_items),
                "analyzedTickers": [item["symbol"] for item in dataset_items],
                "mag7BenchmarkIncluded": len(mag_7_peers) > 0,
                "earningsSummaries": summary_records,
                "aiContextReady": True,
                "message": f"Successfully computed Earnings Intelligence for {len(dataset_items)} stock(s)."
            }
            await Actor.set_value("OUTPUT", output_summary)
            Actor.log.info(f"Saved summary report to Key-Value store 'OUTPUT'. Total items: {len(dataset_items)}")
        else:
            Actor.log.warning("No earnings intelligence records were generated.")


if __name__ == "__main__":
    asyncio.run(main())
