---
source: https://raw.githubusercontent.com/wenchiehlee-investment/TAIFEX/refs/heads/main/raw_column_definition_TAIFEX.md
destination: downstream definitions/raw_column_definition_TAIFEX.md
---

# Raw CSV Column Definitions - TAIFEX

## raw_taifex_daily_futures.csv (TAIFEX Daily Futures Quotes incl. After-hours Session, Long Format)

**Source:** `data/raw_taifex_daily_futures.csv`
**Data Source:** TAIFEX OpenAPI `https://openapi.taifex.com.tw/v1/DailyMarketReportFut`
**Update Frequency:** Twice daily (05:30 Taipei after the 05:00 night-session close; 15:30 Taipei after the day session)
**Extraction Strategy:** The OpenAPI returns the latest trading day only (no historical query), so this is an accumulate-forward pipeline: each run appends rows deduplicated by `(Date, Contract, ContractMonth(Week), TradingSession)`; existing rows are never rewritten and the file keeps full history. Historical backfill would require scraping the website query forms (future enhancement). Key consumer: `GoogleSheet.Banks/fugle_stock_advisor.py --pre-market` — the TX (臺股期貨) near-month "盤後 (night session) close vs 一般 (day session) close" spread is the single most important pre-open indicator (institutions anchor next-day orders to the night close).

### Columns

All API columns are kept verbatim; two timestamps are appended.

| Column | Type | Description | Notes |
|---|---|---|---|
| `Date` | string | Trading date `YYYYMMDD` | |
| `Contract` | string | Contract code, e.g. `TX` (臺股期貨), `MTX`, `TE` | |
| `ContractMonth(Week)` | string | Delivery month `YYYYMM` (or weekly code) | Near month = smallest value for the date |
| `Open` / `High` / `Low` / `Last` | string | Session OHLC | |
| `Change` / `%` | string | Change vs previous session close (points / percent) | |
| `Volume` | string | Contracts traded in the session | |
| `SettlementPrice` | string | Settlement price (day session only; `NULL`-ish for after-hours) | |
| `OpenInterest` | string | Open interest (day session rows) | |
| `BestBid` / `BestAsk` | string | Closing best bid/ask | |
| `HistoricalHigh` / `HistoricalLow` | string | Contract lifetime high/low | |
| `TradingHalt` | string | Trading-halt flag | |
| `TradingSession` | string | `一般` = day session (08:45–13:45); `盤後` = after-hours/night session (15:00–next 05:00) | The night session labeled Date D covers D 15:00 → D+1 05:00 and is the freshest price before D+1's TW open |
| `Volume(ExecutionsAmongSpreadOrderAndSingleOrderOnly)` | string | Spread/single-order execution volume | |
| `download_timestamp` / `process_timestamp` | datetime | Run timestamps | UTC, no suffix |

## raw_taifex_institutional_futures.csv (Major Institutional Traders, Futures by Contract)

**Source:** `data/raw_taifex_institutional_futures.csv`
**Data Source:** TAIFEX OpenAPI `/v1/MarketDataOfMajorInstitutionalTradersDetailsOfFuturesContractsBytheDate`
**Update Frequency:** Daily (15:30 Taipei run; TAIFEX publishes ~15:00)
**Extraction Strategy:** Accumulate-forward with dedup key `(Date, ContractCode, Item)`. Key rows: `ContractCode=臺股期貨`, `Item=外資及陸資` — foreign-institution net TX open interest (`OpenInterest(Net)`), used pre-open to judge "外資今天可能方向"; a day where foreign investors buy cash equities but add futures shorts is a caution divergence.

### Columns

| Column | Type | Description | Notes |
|---|---|---|---|
| `Date` | string | Trading date `YYYYMMDD` | |
| `ContractCode` | string | Contract name in Chinese, e.g. `臺股期貨` | |
| `Item` | string | Trader type: `自營商` / `投信` / `外資及陸資` | |
| `TradingVolume(Long)` / `(Short)` / `(Net)` | string | Contracts traded | |
| `TradingValue(Long/Short/Net)(Thousands)` | string | Traded value | |
| `OpenInterest(Long)` / `(Short)` / `(Net)` | string | Open interest positions | `(Net)` on 臺股期貨/外資及陸資 is the headline number |
| `ContractValueofOpenInterest(...)(Thousands)` | string | OI value | |
| `download_timestamp` / `process_timestamp` | datetime | Run timestamps | UTC, no suffix |

## raw_taifex_institutional_general.csv (Major Institutional Traders, Market-wide)

Same source family (`/v1/MarketDataOfMajorInstitutionalTradersGeneralBytheDate`), one row per trader type per date across all futures contracts combined; dedup key `(Date, Item)`. Columns mirror the by-contract file with `(Millions)` value units.
