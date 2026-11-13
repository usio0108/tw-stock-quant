"""永久資料庫 data/market.db（與可重建的快取 data/cache.db 分開，不可隨意清掉）。

約定：NULL＝未知；日期 'YYYY-MM-DD'；時間戳為帶 +08:00 的 ISO 字串。
isin_listed_on 是 ISIN 清單上印的日期，不一定是首次掛牌日（稽核結論）。
沒有下市日欄位：ISIN 清單只列現存證券，active=0 加 last_seen_on 的意思是
「從該日之後不在清單上」。
"""
import sqlite3
from pathlib import Path

# repo 根目錄下的 data/market.db（測試以 monkeypatch 換掉，見根目錄 conftest.py）
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "market.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS securities (
    ticker          TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    isin            TEXT,
    market          TEXT NOT NULL CHECK(market IN ('TWSE','TPEx')),
    sec_type        TEXT NOT NULL,
    industry        TEXT,
    isin_listed_on  TEXT,
    active          INTEGER NOT NULL CHECK(active IN (0,1)),
    first_seen_on   TEXT NOT NULL,
    last_seen_on    TEXT NOT NULL,
    source          TEXT NOT NULL,
    fetched_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS securities_changes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,
    field       TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT,
    detected_on TEXT NOT NULL,
    source      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fetch_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT NOT NULL,
    endpoint    TEXT NOT NULL,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT CHECK(status IN ('ok','empty','error')),
    row_count   INTEGER,
    error       TEXT
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(_SCHEMA)
    return conn
