#!/usr/bin/env python3
"""抓 TAIFEX OpenAPI 的三大法人期貨交易/未平倉資料，逐日追加、永久保留：
- data/raw_taifex_institutional_futures.csv：依合約明細（重點列：ContractCode=臺股期貨、
  Item=外資及陸資 的 OpenInterest(Net)——外資台指期淨未平倉，開盤前判斷「外資今天可能
  方向」用；現貨買超＋期貨空單增加的背離日要特別小心）
- data/raw_taifex_institutional_general.csv：市場整體（全部契約合計，依交易人類別）

OpenAPI 只回傳最新一個交易日、無歷史查詢——「從現在開始累積」，每天排程抓、去重追加。
時間戳慣例：UTC、無時區後綴（跟 Yahoo.Finance repo 一致）。
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[1]

SOURCES = [
    (
        "https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersDetailsOfFuturesContractsBytheDate",
        REPO_ROOT / "data" / "raw_taifex_institutional_futures.csv",
        ("Date", "ContractCode", "Item"),
    ),
    (
        "https://openapi.taifex.com.tw/v1/MarketDataOfMajorInstitutionalTradersGeneralBytheDate",
        REPO_ROOT / "data" / "raw_taifex_institutional_general.csv",
        ("Date", "Item"),
    ),
]


def fetch_api(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def append_dedup(url, out_csv, key_cols, ts):
    data = fetch_api(url)
    if not data:
        print(f"{out_csv.name}: API 回傳空，跳過")
        return
    api_cols = list(data[0].keys())
    columns = api_cols + ["download_timestamp", "process_timestamp"]

    existing_keys, existing_rows = set(), []
    if out_csv.exists():
        with open(out_csv, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                existing_rows.append(row)
                existing_keys.add(tuple(row.get(k, "") for k in key_cols))

    added = 0
    for r in data:
        key = tuple(str(r.get(k, "")) for k in key_cols)
        if key in existing_keys:
            continue
        row = {c: str(r.get(c, "")) for c in api_cols}
        row["download_timestamp"] = ts
        row["process_timestamp"] = ts
        existing_rows.append(row)
        existing_keys.add(key)
        added += 1

    existing_rows.sort(key=lambda x: tuple(x.get(k, "") for k in key_cols))
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing_rows)
    print(f"寫入 {out_csv.name}：總 {len(existing_rows)} 列（本次新增 {added}）")


def main():
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    for url, out_csv, key_cols in SOURCES:
        append_dedup(url, out_csv, key_cols, ts)


if __name__ == "__main__":
    main()
