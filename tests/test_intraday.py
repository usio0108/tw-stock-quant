import pandas as pd
import pytest

from backend.data_service.sources import intraday


def _minutes(day: str) -> pd.DataFrame:
    index = pd.date_range(f"{day} 09:00", periods=3, freq="min", tz="Asia/Taipei")
    return pd.DataFrame({"Close": [101.0, 102.0, 103.0], "Volume": [10.0, 0.0, 5.0]}, index=index)


def _daily(closes: dict[str, float]) -> pd.DataFrame:
    index = pd.DatetimeIndex(list(closes), tz="Asia/Taipei")
    return pd.DataFrame({"Close": list(closes.values())}, index=index)


class _Ticker:
    def __init__(self, minutes, daily):
        self.minutes, self.daily = minutes, daily

    def history(self, period, interval):
        return self.minutes if interval == "1m" else self.daily


@pytest.mark.parametrize("daily,expected", [
    # 盤中日線還沒帶當日棒：基準是最後一根（11/11），不是倒數第二根
    ({"2026-11-10": 99.0, "2026-11-11": 100.0}, 100.0),
    # 日線已含當日棒：跳過當日
    ({"2026-11-10": 99.0, "2026-11-11": 100.0, "2026-11-12": 103.0}, 100.0),
    # 找不到更早交易日：不拿今日價冒充
    ({"2026-11-12": 103.0}, None),
])
def test_prev_close_is_the_session_before_the_minute_data(monkeypatch, daily, expected):
    intraday.fetch_intraday.cache_clear()
    monkeypatch.setattr(intraday.yf, "Ticker", lambda symbol: _Ticker(_minutes("2026-11-12"), _daily(daily)))
    result = intraday.fetch_intraday("2330.TW")
    assert result["prev_close"] == expected
    # 假 UTC：台北 09:00 編成 UTC 09:00 的 epoch
    assert result["points"][0]["time"] == int(pd.Timestamp("2026-11-12 09:00", tz="UTC").timestamp())
