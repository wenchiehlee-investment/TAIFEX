#!/usr/bin/env python3
"""抓 TAIFEX OpenAPI 的期貨每日行情（含一般/盤後兩時段），逐日追加到
data/raw_taifex_daily_futures.csv，永久保留。

重點消費者：GoogleSheet.Banks/fugle_stock_advisor.py --pre-market 開盤前簡報——
臺股期貨（TX）「盤後（夜盤）收盤 vs 一般（日盤）收盤」是開盤前最重要的單一指標
（很多法人依夜盤價格掛隔日的單）。

OpenAPI（https://openapi.taifex.com.tw）只回傳最新一個交易日、無歷史查詢——所以這支
是「從現在開始累積」的管線：每天排程抓一次、依 (Date, Contract, ContractMonth(Week),
TradingSession) 去重後追加，舊列永不改寫。歷史回填要另外爬官網查詢表單，列為後續增強。

時間戳慣例：台北時間、帶「 CST」後綴（跟 GoodInfo/ConceptStocks 一致）——
GoogleSheet.Banks 與 biztrends.TW 的新鮮度檢查都認得 CST 後綴；無後綴的舊列
GoogleSheet.Banks 當 UTC、biztrends.TW 當 CST，會差 8 小時，所以新列一律標明。
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = REPO_ROOT / "data" / "raw_taifex_daily_futures.csv"
API_URL = "https://openapi.taifex.com.tw/v1/DailyMarketReportFut"

# OpenAPI 回傳的原始欄位（原樣保留）＋我們附加的兩個時間戳
API_COLUMNS = [
    "Date", "Contract", "ContractMonth(Week)", "Open", "High", "Low", "Last",
    "Change", "%", "Volume", "SettlementPrice", "OpenInterest", "BestBid",
    "BestAsk", "HistoricalHigh", "HistoricalLow", "TradingHalt", "TradingSession",
    "Volume(ExecutionsAmongSpreadOrderAndSingleOrderOnly)",
]
COLUMNS = API_COLUMNS + ["download_timestamp", "process_timestamp"]
KEY_COLS = ("Date", "Contract", "ContractMonth(Week)", "TradingSession")


def fetch_api(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def main():
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST")
    data = fetch_api(API_URL)
    print(f"OpenAPI 回傳 {len(data)} 列（日期 {sorted({r.get('Date') for r in data})}）")

    existing_keys = set()
    existing_rows = []
    if OUT_CSV.exists():
        with open(OUT_CSV, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                existing_rows.append(row)
                existing_keys.add(tuple(row.get(k, "") for k in KEY_COLS))

    added = 0
    for r in data:
        key = tuple(str(r.get(k, "")) for k in KEY_COLS)
        if key in existing_keys:
            continue
        row = {c: str(r.get(c, "")) for c in API_COLUMNS}
        row["download_timestamp"] = ts
        row["process_timestamp"] = ts
        existing_rows.append(row)
        existing_keys.add(key)
        added += 1

    existing_rows.sort(key=lambda x: (x.get("Date", ""), x.get("Contract", ""),
                                      x.get("ContractMonth(Week)", ""), x.get("TradingSession", "")))
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(existing_rows)
    print(f"寫入 {OUT_CSV}：總 {len(existing_rows)} 列（本次新增 {added}）")


if __name__ == "__main__":
    main()
