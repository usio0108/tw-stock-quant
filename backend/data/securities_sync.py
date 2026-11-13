"""證交所 ISIN 上市／上櫃證券清單 → data/market.db 的 securities（S01）。

python -m backend.data.securities_sync：印 JSON 摘要，失敗 exit 1。
兩個市場一起抓、一個 transaction 寫入，任何一邊失敗都不寫半套資料。
"""
import html as html_lib
import json
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from backend.data.market_db import connect

SOURCE = "twse_isin"
ENDPOINTS = {"TWSE": "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2",
             "TPEx": "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"}
MARKETS = {"上市": "TWSE", "上櫃": "TPEx"}
DEACTIVATE_LIMIT = 0.05  # 單一市場一次下架超過 5% 視為頁面壞掉，整批中止
_COMPARED = ("name", "isin", "market", "sec_type", "industry", "isin_listed_on")

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<td([^>]*)>(.*?)</td>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


class SyncAbort(Exception):
    """安全閥觸發：不寫入任何資料。"""


def _text(cell: str) -> str:
    return html_lib.unescape(_TAG.sub("", cell)).strip()


def parse_isin(html: str) -> list[dict]:
    """解析 ISIN 頁面；跳過權證區段、非上市／上櫃列與表頭。"""
    rows, sec_type = [], None
    for tr in _ROW.finditer(html):
        cells = _CELL.findall(tr.group(1))
        if len(cells) == 1 and "colspan" in cells[0][0].lower():
            sec_type = _text(cells[0][1])  # 區段標題列，例如「股票」
            continue
        if sec_type is None or "權證" in sec_type or len(cells) < 5:
            continue
        code, sep, name = _text(cells[0][1]).partition("　")  # 代號與名稱以全形空白隔開
        market = MARKETS.get(_text(cells[3][1]))
        if not sep or market is None:
            continue
        listed = _text(cells[2][1]).replace("/", "-")
        rows.append({"ticker": code.strip(), "name": name.strip(), "isin": _text(cells[1][1]) or None,
                     "market": market, "sec_type": sec_type, "industry": _text(cells[4][1]) or None,
                     "isin_listed_on": listed or None})
    return rows


def sync(conn: sqlite3.Connection, pages: dict[str, str], today: str, now: str) -> dict:
    """pages: {'TWSE': html, 'TPEx': html}。全部寫入在同一個 transaction。"""
    fetched: dict[str, dict] = {}
    for market, page in pages.items():
        parsed = parse_isin(page)
        if not any(r["market"] == market and r["sec_type"] == "股票" for r in parsed):
            raise SyncAbort(f"{market} 頁面沒有任何股票列，疑似頁面格式改變，已中止")
        fetched.update({r["ticker"]: r for r in parsed})

    stored = {r[0]: r for r in conn.execute(
        "SELECT ticker, name, isin, market, sec_type, industry, isin_listed_on, active FROM securities")}
    gone = [t for t, r in stored.items() if r[7] == 1 and t not in fetched]
    for market in pages:
        active = sum(1 for r in stored.values() if r[7] == 1 and r[3] == market)
        lost = sum(1 for t in gone if stored[t][3] == market)
        if lost > active * DEACTIVATE_LIMIT:
            raise SyncAbort(f"{market} 將下架 {lost}/{active} 檔，超過 {DEACTIVATE_LIMIT:.0%}，已中止")

    counts = {"new": 0, "changed": 0, "deactivated": 0, "reactivated": 0}
    with conn:
        def change(ticker, field, old, new):
            conn.execute("INSERT INTO securities_changes(ticker, field, old_value, new_value, detected_on, source)"
                         " VALUES (?,?,?,?,?,?)", (ticker, field, old, new, today, SOURCE))

        for ticker, r in fetched.items():
            old = stored.get(ticker)
            if old is None:
                counts["new"] += 1
                change(ticker, "active", None, "1")
                conn.execute("INSERT INTO securities VALUES (?,?,?,?,?,?,?,1,?,?,?,?)",
                             (ticker, r["name"], r["isin"], r["market"], r["sec_type"], r["industry"],
                              r["isin_listed_on"], today, today, SOURCE, now))
                continue
            diffs = [(f, old[i], r[f]) for i, f in enumerate(_COMPARED, start=1) if old[i] != r[f]]
            for field, was, new in diffs:
                change(ticker, field, was, new)
            counts["changed"] += bool(diffs)
            if old[7] == 0:
                counts["reactivated"] += 1
                change(ticker, "active", "0", "1")
            conn.execute("UPDATE securities SET name=?, isin=?, market=?, sec_type=?, industry=?,"
                         " isin_listed_on=?, active=1, last_seen_on=?, source=?, fetched_at=? WHERE ticker=?",
                         (r["name"], r["isin"], r["market"], r["sec_type"], r["industry"],
                          r["isin_listed_on"], today, SOURCE, now, ticker))
        for ticker in gone:
            counts["deactivated"] += 1
            change(ticker, "active", "1", "0")
            conn.execute("UPDATE securities SET active=0 WHERE ticker=?", (ticker,))  # last_seen_on 保留
    counts["rows"] = {m: sum(1 for r in fetched.values() if r["market"] == m) for m in pages}
    return counts


def _fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "tw-stock-quant securities-sync"})
    with urllib.request.urlopen(request, timeout=120) as resp:
        return resp.read().decode("cp950", errors="replace")


def _log(conn: sqlite3.Connection, endpoint: str, started: str, finished: str,
         status: str, rows: int | None, error: str | None) -> None:
    conn.execute("INSERT INTO fetch_log(source, endpoint, started_at, finished_at, status, row_count, error)"
                 " VALUES (?,?,?,?,?,?,?)", (SOURCE, endpoint, started, finished, status, rows, error))


def _now() -> datetime:
    return datetime.now(timezone(timedelta(hours=8))).replace(microsecond=0)


def main() -> int:
    conn = connect()
    started = _now().isoformat()
    try:
        pages = {}
        for market, url in ENDPOINTS.items():
            try:
                pages[market] = _fetch(url)
            except Exception as error:
                raise RuntimeError(f"{url} 抓取失敗：{error}") from error
        now = _now()
        summary = sync(conn, pages, now.date().isoformat(), now.isoformat())
    except Exception as error:
        message = f"{type(error).__name__}: {error}"
        with conn:
            for url in ENDPOINTS.values():
                _log(conn, url, started, _now().isoformat(), "error", None, message)
        print(json.dumps({"status": "error", "error": message}, ensure_ascii=False))
        return 1
    with conn:
        for market, url in ENDPOINTS.items():
            _log(conn, url, started, _now().isoformat(), "ok", summary["rows"][market], None)
    print(json.dumps({"status": "ok", **summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
