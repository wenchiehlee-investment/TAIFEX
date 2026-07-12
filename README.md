# TAIFEX

台灣期貨交易所（TAIFEX）公開資料管線：期貨每日行情（含盤後/夜盤時段）與三大法人
期貨交易/未平倉，經 TAIFEX OpenAPI 每日抓取、逐日累積（OpenAPI 只提供最新交易日，
無歷史查詢），同步到 GoogleSheet.Banks（開盤前簡報 --pre-market）與 biztrends.TW。

| 檔案 | 內容 | 排程 |
|---|---|---|
| `data/raw_taifex_daily_futures.csv` | 全合約每日行情，`TradingSession` 分一般/盤後 | 台北 05:30、15:30 |
| `data/raw_taifex_institutional_futures.csv` | 三大法人依合約（重點：臺股期貨×外資淨未平倉） | 台北 15:30 |
| `data/raw_taifex_institutional_general.csv` | 三大法人市場合計 | 台北 15:30 |

欄位定義見 `raw_column_definition_TAIFEX.md`。
