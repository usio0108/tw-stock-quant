"""上市／上櫃證券清單：優先讀 data/market.db（securities_sync 寫入），沒有資料時退回 twstock 本機快照。

不發出網路請求。market.db 不存在或 securities 是空的才退回 twstock，退回時記一次 warning。
"""

import json
import logging
from collections import Counter
from contextlib import closing

import twstock

from backend.data import market_db

MARKET_SUFFIXES = {"上市": ".TW", "上櫃": ".TWO"}
_DB_MARKETS = {"TWSE": "上市", "TPEx": "上櫃"}  # market.db 的市場代碼 → 對外沿用的中文名
_warned = False


def _query(sql: str, params: tuple = ()) -> list[tuple] | None:
    """market.db 有資料時回查詢結果，否則回 None（呼叫端退回 twstock）。"""
    global _warned
    if market_db.DB_PATH.exists():
        with closing(market_db.connect()) as conn:
            if conn.execute("SELECT 1 FROM securities LIMIT 1").fetchone() is not None:
                return conn.execute(sql, params).fetchall()
    if not _warned:
        _warned = True
        logging.warning("market.db 沒有證券資料，退回 twstock 本機快照；請執行 python -m backend.data.securities_sync")
    return None


def universe_source() -> str:
    """目前實際使用的來源：'market.db' 或 'twstock'。"""
    return "market.db" if _query("SELECT 1 FROM securities LIMIT 1") is not None else "twstock"


def security(ticker: str) -> dict | None:
    """單一證券資料 {name, market('上市'/'上櫃'), sec_type, industry}；查無或市場不支援回 None。"""
    rows = _query("SELECT name, market, sec_type, industry FROM securities WHERE ticker=? AND active=1", (ticker,))
    if rows is not None:
        return ({"name": rows[0][0], "market": _DB_MARKETS[rows[0][1]], "sec_type": rows[0][2],
                 "industry": rows[0][3]} if rows else None)
    info = twstock.codes.get(ticker)
    if info is None or info.market not in MARKET_SUFFIXES:
        return None
    return {"name": info.name, "market": info.market, "sec_type": info.type,
            "industry": getattr(info, "group", None)}


def yahoo_symbol(ticker: str) -> str:
    """裸代碼 → Yahoo 代碼；查不到市場時不猜測後綴。已知 ETF 等仍可直接查詢。"""
    info = security(ticker)
    if info is None:
        raise ValueError(f"查無上市／上櫃代碼「{ticker}」，請先執行 securities_sync 或確認代碼")
    return ticker + MARKET_SUFFIXES[info["market"]]


def stock_universe() -> list[dict[str, str]]:
    """只含一般股票；排除 ETF、權證、特別股與不支援的市場，按代碼排序。"""
    rows = _query("SELECT ticker, name, market FROM securities WHERE active=1 AND sec_type='股票' ORDER BY ticker")
    if rows is not None:
        return [{"ticker": t, "name": n, "market": _DB_MARKETS[m], "symbol": t + MARKET_SUFFIXES[_DB_MARKETS[m]]}
                for t, n, m in rows]
    return [
        {"ticker": code, "name": info.name, "market": info.market,
         "symbol": code + MARKET_SUFFIXES[info.market]}
        for code, info in sorted(twstock.codes.items())
        if info.type == "股票" and info.market in MARKET_SUFFIXES
    ]


if __name__ == "__main__":
    stocks = stock_universe()
    print(json.dumps({"source": universe_source(), "total": len(stocks),
                      "markets": dict(Counter(s["market"] for s in stocks))}, ensure_ascii=False))
