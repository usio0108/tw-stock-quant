"""今日分時走勢（每分鐘價格＋累計均價＋成交量），個股與大盤共用。搬自舊 backend/api/get_intraday.py。"""
import calendar

import yfinance as yf

from backend.data_service.cache import ttl_cache


def _prev_session_close(daily, session_date) -> float | None:
    """分鐘資料所屬交易日「之前」最後一根日線的收盤價。

    不能固定取 daily 倒數第二根：盤中日線常還沒帶當日棒，倒數第二根會是前前日；
    日線也可能只有一根。用日期比對才不會錯拿基準，找不到就回 None，不拿今日價冒充。
    """
    earlier = daily[[ts.date() < session_date for ts in daily.index]]
    return float(earlier["Close"].iloc[-1]) if len(earlier) else None


@ttl_cache(seconds=30)
def fetch_intraday(symbol: str) -> dict:
    """symbol：完整 Yahoo 代碼，如 "2330.TW"、"6488.TWO" 或大盤 "^TWII"。"""
    ticker = yf.Ticker(symbol)
    intraday = ticker.history(period="1d", interval="1m").dropna(subset=["Close", "Volume"])
    if intraday.empty:
        return {"error": f"No intraday data for {symbol}"}

    # 1mo 而非 5d：連假（如春節）時 5 個日曆日內可能找不到前一交易日
    daily = ticker.history(period="1mo", interval="1d").dropna(subset=["Close"])
    prev_close = _prev_session_close(daily, intraday.index[-1].date())

    cum_pv = 0.0  # price * volume 累計，算累計均價線
    cum_vol = 0.0
    points = []
    for ts, row in intraday.iterrows():
        price = float(row["Close"])
        vol = float(row["Volume"])
        cum_pv += price * vol
        cum_vol += vol
        avg_price = (cum_pv / cum_vol) if cum_vol > 0 else price
        points.append({
            # 假 UTC：把台北壁鐘時間當 UTC 算 epoch，lightweight-charts 以 UTC 顯示就是台北時間。
            # 前端格式化這個值必須用 timeZone "UTC"（formatWallClockEpoch），不能用本地時區。
            "time": calendar.timegm(ts.timetuple()),
            "price": round(price, 2),
            "avg_price": round(avg_price, 2),
            "volume": vol,
        })

    return {"prev_close": round(prev_close, 2) if prev_close is not None else None, "points": points}
