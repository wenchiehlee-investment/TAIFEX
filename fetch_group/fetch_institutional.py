#!/usr/bin/env python3
"""抓 TAIFEX OpenAPI 的三大法人期貨交易/未平倉資料，逐日追加、永久保留：
- data/raw_taifex_institutional_futures.csv：依合約明細（重點列：ContractCode=臺股期貨、
  Item=外資及陸資 的 OpenInterest(Net)——外資台指期淨未平倉，開盤前判斷「外資今天可能
  方向」用；現貨買超＋期貨空單增加的背離日要特別小心）
- data/raw_taifex_institutional_general.csv：市場整體（全部契約合計，依交易人類別）

OpenAPI 只回傳最新一個交易日、無歷史查詢——「從現在開始累積」，每天排程抓、去重追加。
時間戳慣例：台北時間、帶「 CST」後綴（跟 GoodInfo/ConceptStocks 一致，見
fetch_daily_futures.py 的說明）。
"""
from __future__ import annotations

import csv
import io
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
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
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8-sig")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Some endpoints (e.g. ...GeneralBytheDate, since 2026-11) answer with a
        # Chinese-header CSV instead of JSON. Return rows keyed by those headers and
        # flag them so append_dedup maps them onto the existing English columns.
        rows = list(csv.reader(io.StringIO(raw)))
        if len(rows) < 2:
            return []
        header = [h.strip() for h in rows[0]]
        return [{"__csv_header__": header, "__csv_values__": r} for r in rows[1:] if any(c.strip() for c in r)]


def normalize_csv_rows(data, out_csv):
    """Map Chinese-header CSV rows positionally onto the existing file's English columns."""
    if not data or "__csv_header__" not in data[0]:
        return data
    header = data[0]["__csv_header__"]
    if not out_csv.exists():
        raise SystemExit(f"{out_csv.name}: API returned CSV and there is no existing file to map columns from")
    with open(out_csv, encoding="utf-8-sig", newline="") as f:
        existing = next(csv.reader(f))
    target = [c for c in existing if c not in ("download_timestamp", "process_timestamp")]
    if len(target) != len(header):
        raise SystemExit(f"{out_csv.name}: CSV has {len(header)} columns {header}, existing file has {len(target)} {target}; refusing to guess")
    print(f"{out_csv.name}: API 回傳 CSV（中文欄名），依欄位順序對應到既有英文欄名")
    return [dict(zip(target, [v.strip() for v in d["__csv_values__"]])) for d in data]


def append_dedup(url, out_csv, key_cols, ts):
    data = normalize_csv_rows(fetch_api(url), out_csv)
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
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S CST")
    for url, out_csv, key_cols in SOURCES:
        append_dedup(url, out_csv, key_cols, ts)


if __name__ == "__main__":
    main()
