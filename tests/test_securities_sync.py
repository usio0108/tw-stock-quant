import json
import logging
import sqlite3

import pytest

from backend.data import market_db, securities_sync, universe
from backend.data.securities_sync import SyncAbort, parse_isin, sync

D1, D2, D3 = "2026-11-13", "2026-11-14", "2026-11-15"
NOW = "T+08:00"

# (代號, 名稱, 區段, 市場, 產業)；填充股票讓 5% 安全閥有足夠分母（每市場約 30 檔）。
BASE = (
    [("1101", "台泥", "股票", "上市", "水泥工業"), ("2330", "台積電", "股票", "上市", "半導體業"),
     ("6488", "環球晶", "股票", "上櫃", ""), ("0050", "元大台灣50", "ETF", "上市", "")]
    + [(f"90{i:02d}", f"甲{i}", "股票", "上市", "其他") for i in range(30)]
    + [(f"80{i:02d}", f"乙{i}", "股票", "上櫃", "其他") for i in range(30)]
)


def _page(rows, warrants=True):
    """仿 ISIN 頁面：表頭列、單格區段標題列、資料列，最後轉 cp950 再解回來。"""
    out = ["<table><tr><td bgcolor=#D5FFD5 align=center>有價證券代號及名稱</td><td>國際證券辨識號碼(ISIN Code)</td>"
           "<td>上市日</td><td>市場別</td><td>產業別</td><td>CFICode</td><td>備註</td></tr>"]
    for title in dict.fromkeys(r[2] for r in rows):
        out.append(f"<tr><td bgcolor=#D5FFD5 colspan=7><B> {title} <B></td></tr>")
        for code, name, sec, market, industry in rows:
            if sec == title:
                out.append(f"<tr><td bgcolor=#FAFAD2>{code}　{name}</td><td>TW{code}</td><td>2000/01/05</td>"
                           f"<td>{market}</td><td>{industry}</td><td>ESVUFR</td><td></td></tr>")
    if warrants:
        out.append("<tr><td bgcolor=#D5FFD5 colspan=7><B> 認購(售)權證(不含牛熊證) <B></td></tr>"
                   "<tr><td>030001　測試購01</td><td>TW030001</td><td>2026/11/01</td><td>上市</td><td></td><td></td><td></td></tr>")
    out.append("</table>")
    return "".join(out).encode("cp950").decode("cp950")


def _pages(rows):
    return {"TWSE": _page([r for r in rows if r[3] == "上市"]), "TPEx": _page([r for r in rows if r[3] == "上櫃"])}


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(market_db, "DB_PATH", tmp_path / "market.db")
    connection = market_db.connect()
    yield connection
    connection.close()


def _dump(conn):
    return [conn.execute(f"SELECT * FROM {t} ORDER BY 1, 2").fetchall()
            for t in ("securities", "securities_changes", "fetch_log")]


def _changes(conn, ticker=None):
    sql = "SELECT ticker, field, old_value, new_value, detected_on FROM securities_changes"
    return conn.execute(sql + (" WHERE ticker=? ORDER BY id" if ticker else " ORDER BY id"),
                        (ticker,) if ticker else ()).fetchall()


def test_connect_creates_schema_idempotently(conn):
    market_db.connect().close()
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"securities", "securities_changes", "fetch_log"} <= names
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO fetch_log(source, endpoint, started_at, status) VALUES ('s','e','t','bogus')")


def test_parse_skips_warrants_headers_and_other_markets():
    rows = parse_isin(_page(BASE[:4] + [("9999", "興櫃股", "股票", "興櫃", "")]))
    assert [r["ticker"] for r in rows] == ["1101", "2330", "6488", "0050"]
    assert rows[0] == {"ticker": "1101", "name": "台泥", "isin": "TW1101", "market": "TWSE", "sec_type": "股票",
                       "industry": "水泥工業", "isin_listed_on": "2000-01-05"}
    assert rows[2]["market"] == "TPEx" and rows[2]["industry"] is None
    assert rows[3]["sec_type"] == "ETF"


def test_first_sync_then_changes_deactivation_and_reappearance(conn):
    first = sync(conn, _pages(BASE), D1, NOW)
    assert first["new"] == len(BASE) and first["rows"] == {"TWSE": 33, "TPEx": 31}
    assert _changes(conn, "2330") == [("2330", "active", None, "1", D1)]
    assert conn.execute("SELECT active, first_seen_on, last_seen_on, source FROM securities WHERE ticker='2330'"
                        ).fetchone() == (1, D1, D1, "twse_isin")

    # 第二天：台泥更名、環球晶改上市、9000 消失（1/33 < 5%）。
    day2 = [("1101", "台泥新", *BASE[0][2:])] + [("6488", "環球晶", "股票", "上市", "")] + BASE[1:2] + BASE[3:]
    day2 = [r for r in day2 if r[0] != "9000"]
    second = sync(conn, _pages(day2), D2, NOW)
    assert (second["new"], second["changed"], second["deactivated"]) == (0, 2, 1)
    assert _changes(conn, "1101")[1:] == [("1101", "name", "台泥", "台泥新", D2)]
    assert _changes(conn, "6488")[1:] == [("6488", "market", "TPEx", "TWSE", D2)]
    assert _changes(conn, "9000")[1:] == [("9000", "active", "1", "0", D2)]
    assert conn.execute("SELECT active, first_seen_on, last_seen_on FROM securities WHERE ticker='9000'"
                        ).fetchone() == (0, D1, D1)
    assert conn.execute("SELECT first_seen_on, last_seen_on FROM securities WHERE ticker='1101'"
                        ).fetchone() == (D1, D2)

    third = sync(conn, _pages(BASE), D3, NOW)
    assert third["reactivated"] == 1
    assert _changes(conn, "9000")[2:] == [("9000", "active", "0", "1", D3)]
    assert conn.execute("SELECT active, last_seen_on FROM securities WHERE ticker='9000'").fetchone() == (1, D3)
    assert conn.execute("SELECT name FROM securities WHERE ticker='1101'").fetchone() == ("台泥",)  # 改名改回也記錄


@pytest.mark.parametrize("broken", ["many_gone", "no_stocks"])
def test_guard_aborts_without_any_write(conn, broken):
    sync(conn, _pages(BASE), D1, NOW)
    before = _dump(conn)
    if broken == "many_gone":
        rows = [r for r in BASE if not r[0].startswith("900")]  # 一次消失 10 檔，約 30%
        pages = _pages(rows)
    else:
        pages = {**_pages(BASE), "TPEx": _page([r for r in BASE if r[2] == "ETF"])}  # 沒有任何股票列
    with pytest.raises(SyncAbort):
        sync(conn, pages, D2, NOW)
    assert _dump(conn) == before


def test_main_logs_error_and_writes_nothing_else_on_guard_abort(conn, monkeypatch, capsys):
    sync(conn, _pages(BASE), D1, NOW)
    before = _dump(conn)
    broken = _pages([r for r in BASE if not r[0].startswith("900")])
    monkeypatch.setattr(securities_sync, "_fetch", lambda url: broken["TWSE" if "strMode=2" in url else "TPEx"])
    assert securities_sync.main() == 1
    after = _dump(conn)
    assert after[:2] == before[:2]
    errors = after[2][len(before[2]):]
    assert len(errors) == 2 and {r[5] for r in errors} == {"error"} and "超過" in errors[0][7]
    assert json.loads(capsys.readouterr().out)["status"] == "error"


def test_main_fetch_failure_logs_error_and_writes_nothing_else(conn, monkeypatch):
    def fetch(url):
        if "strMode=4" in url:
            raise OSError("boom")
        return _pages(BASE)["TWSE"]

    monkeypatch.setattr(securities_sync, "_fetch", fetch)
    assert securities_sync.main() == 1
    assert conn.execute("SELECT COUNT(*) FROM securities").fetchone() == (0,)
    assert conn.execute("SELECT COUNT(*) FROM securities_changes").fetchone() == (0,)
    log = conn.execute("SELECT status, row_count, error FROM fetch_log").fetchall()
    assert len(log) == 2 and all(r[0] == "error" and r[1] is None and "boom" in r[2] for r in log)


def test_main_success_logs_ok_with_row_counts(conn, monkeypatch, capsys):
    pages = _pages(BASE)
    monkeypatch.setattr(securities_sync, "_fetch", lambda url: pages["TWSE" if "strMode=2" in url else "TPEx"])
    assert securities_sync.main() == 0
    assert json.loads(capsys.readouterr().out)["new"] == len(BASE)
    assert conn.execute("SELECT status, row_count FROM fetch_log ORDER BY id").fetchall() == [("ok", 33), ("ok", 31)]


def test_universe_reads_market_db_and_falls_back_to_twstock(conn, caplog):
    # 空庫（或檔案不存在）→ twstock，且只警告一次
    universe._warned = False
    with caplog.at_level(logging.WARNING):
        assert universe.universe_source() == "twstock"
        assert universe.security("2330")["name"] == "台積電"
        assert universe.security("6488")["market"] == "上櫃"
    assert len([r for r in caplog.records if "twstock" in r.getMessage()]) == 1

    # 6488 在 market.db 標成上市（與 twstock 不同），可證明讀的是 DB
    rows = [r for r in BASE if r[0] != "6488"] + [("6488", "環球晶", "股票", "上市", "半導體業")]
    sync(conn, _pages(rows), D1, NOW)
    sync(conn, _pages([r for r in rows if r[0] != "9000"]), D2, NOW)
    assert universe.universe_source() == "market.db"
    assert universe.security("6488") == {"name": "環球晶", "market": "上市", "sec_type": "股票", "industry": "半導體業"}
    assert universe.security("0050")["sec_type"] == "ETF"
    assert universe.yahoo_symbol("6488") == "6488.TW"
    assert universe.yahoo_symbol("0050") == "0050.TW"
    assert universe.security("9000") is None  # 已下架
    with pytest.raises(ValueError):
        universe.yahoo_symbol("9000")
    stocks = universe.stock_universe()
    tickers = [s["ticker"] for s in stocks]
    assert tickers == sorted(tickers) and "0050" not in tickers and "9000" not in tickers
    assert {"ticker": "6488", "name": "環球晶", "market": "上市", "symbol": "6488.TW"} in stocks
    assert len(stocks) == 62  # 63 檔股票扣掉已下架的 9000
