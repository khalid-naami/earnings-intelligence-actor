# Stock Earnings Intelligence & Options Volatility Analytics Actor 📊

Analyze **stock earnings dates**, **options expected moves (ATM Straddle)**, **historical gap-fill probabilities**, **5-day post-earnings price drift**, **analyst price targets**, and **AI market biases** across US equities.

Pre-configured by default with the **Magnificent Seven (NVDA, AAPL, MSFT, AMZN, GOOGL, META, TSLA)**, and fully customizable for any US stock ticker.

---

## 🌟 Key Capabilities

- **Options Expected Move Calculation**: Computes the exact market-implied move (`+/- %` and `$`) using front-month At-The-Money (ATM) Straddle options pricing (`(Call Ask + Put Ask) / Current Price`).
- **Volatility Skew & Term Structure**: Analyzes Put vs Call IV skew (5% OTM) and front-month vs back-month IV to anticipate post-earnings volatility crush.
- **Historical Gap-Fill & Drift Analytics (Last 8 Quarters)**:
  - **Gap-Fill Probability (%)**: Percentage of historical quarters where price returned to pre-earnings close within 5 trading days.
  - **Post-Earnings Drift Bias**: Average 5-day price trajectory after market open reaction (`Bullish Drift` vs `Bearish Drift`).
  - **Relative Price Pathways**: Day-by-day normalized price trajectories from Day -1 to Day +5.
- **Analyst Targets & Consensus**:
  - Consensus recommendations (Strong Buy, Buy, Hold, Sell).
  - Target Price Mean, High, Low, and implied upside/downside percentages.
  - Historical EPS surprise percentages (Beat vs Miss history).
- **Magnificent Seven Benchmark Matrix**: Side-by-side valuation comparison (`P/E`, `Forward P/E`, `PEG`, `P/S`, `EV/EBITDA`).
- **AI Agent & MCP Ready**: Generates an executive summary with next earnings date countdown, implied moves, and win-rate biases ready for LLMs, Claude, ChatGPT, and LangChain.

---

## 📥 Input Configuration

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `symbols` | `Array<string>` | `["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA"]` | List of US stock tickers to analyze. |
| `includePeerComparison` | `Boolean` | `true` | Include Mag 7 side-by-side valuation benchmark table. |
| `quartersBack` | `Integer` | `8` | Number of previous earnings quarters to evaluate. |

### Example Input (`input.json`):
```json
{
  "symbols": ["NVDA", "AAPL", "TSLA", "AMD", "PLTR"],
  "includePeerComparison": true,
  "quartersBack": 8
}
```

---

## 📤 Output Dataset Format

Each dataset item provides deep quantitative and qualitative earnings intelligence:

```json
{
  "symbol": "NVDA",
  "companyName": "NVIDIA Corporation",
  "sector": "Technology",
  "industry": "Semiconductors",
  "currentPrice": 128.50,
  "nextEarningsDate": "2026-11-18",
  "daysUntilEarnings": 52,
  "aiInsights": {
    "nextEarningsDate": "2026-11-18",
    "daysUntilEarnings": 52,
    "optionsImpliedMove": "+/-7.85%",
    "gapFillProbability": "75.0%",
    "historicalBeatRate": "100.0%",
    "postEarningsBias": "Bullish Drift",
    "executiveSummary": "NVDA (NVIDIA Corporation) next earnings release is scheduled for 2026-11-18 (52 days away). Options market prices an expected move of +/-7.85%. Historically over the past 8 quarters, NVDA beats earnings estimates 100.0% of the time, fills its post-earnings opening gap 75.0% of the time, and displays a Bullish Drift with an average 5-day drift of 3.42%."
  },
  "optionsImpliedVolatility": {
    "frontExpiration": "2026-11-20",
    "atmStrike": 128.0,
    "straddlePrice": 10.08,
    "impliedMovePct": 7.85,
    "impliedMoveDollar": 10.08,
    "skewPct": 2.45,
    "frontMonthIVPct": 58.4,
    "backMonthIVPct": 46.2
  },
  "gapFillAnalytics": {
    "totalEarningsAnalyzed": 8,
    "gapFillProbabilityPct": 75.0,
    "beatRatePct": 100.0,
    "averageGapUpPct": 5.82,
    "averageGapDownPct": -2.15,
    "average5DDriftPct": 3.42,
    "postEarningsDriftBias": "Bullish Drift"
  },
  "analystTargets": {
    "recommendation": "STRONG BUY",
    "numberOfAnalysts": 55,
    "targetMeanPrice": 150.0,
    "impliedUpsidePct": 16.73
  }
}
```

---

## 🤖 AI Agent & MCP Integration

Because this Actor outputs clean, pre-calculated probabilities and executive summaries, it is 100% plug-and-play with **Apify Model Context Protocol (MCP)** servers, OpenAI GPTs, Claude Tools, and LangChain/CrewAI agents.

### Apify Python Client Example:
```python
from apify_client import ApifyClient

client = ApifyClient("<YOUR_API_TOKEN>")

run_input = {
    "symbols": ["NVDA", "AAPL", "AMD"],
    "quartersBack": 8
}

run = client.actor("khnaami/stock-earnings-intelligence-actor").call(run_input=run_input)

for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(f"{item['symbol']} | Expected Move: {item['aiInsights']['optionsImpliedMove']} | Gap Fill: {item['aiInsights']['gapFillProbability']}")
```

### Apify JavaScript / TypeScript Client Example:
```typescript
import { ApifyClient } from 'apify-client';

const client = new ApifyClient({
    token: '<YOUR_API_TOKEN>',
});

const run = await client.actor('khnaami/stock-earnings-intelligence-actor').call({
    symbols: ['NVDA', 'TSLA', 'PLTR'],
});

const { items } = await client.dataset(run.defaultDatasetId).listItems();
console.log(items);
```

---

## ⚖️ Disclaimer

*This Actor provides statistical, options implied moves, and historical price metrics for educational and analytical purposes only. It is not financial or investment advice.*
