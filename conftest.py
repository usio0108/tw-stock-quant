"""pytest 暫存目錄：每次執行在 repo 內開一個專屬資料夾，結束就刪。

Codex 沙箱帳號建立的檔案只有自己能存取：固定路徑（%TEMP%\\pytest-of-<user>、
.pytest_tmp）只要被別的帳號（另一個沙箱、或使用者本人）先建立過，後來的人就刪不掉
也讀不到，用到 tmp_path 的測試會在設定階段 ERROR。沙箱又寫不進 %TEMP%，所以放 repo 內、
每次用不同名字。.pytest_cache 同理，已在 pyproject 用 -p no:cacheprovider 關掉。
"""
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    if config.option.basetemp is None:
        config.option.basetemp = tempfile.mkdtemp(prefix=".pytest_tmp-", dir=config.rootpath)
        config.stash[_OWN_BASETEMP] = Path(config.option.basetemp)


def pytest_unconfigure(config: pytest.Config) -> None:
    own = config.stash.get(_OWN_BASETEMP, None)
    if own is not None:
        shutil.rmtree(own, ignore_errors=True)


_OWN_BASETEMP = pytest.StashKey[Path]()


@pytest.fixture(autouse=True)
def _isolated_market_db(tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    """market.db 指到不存在的暫存路徑，測試不會讀到開發者真正的證券清單（會退回 twstock）。"""
    from backend.data import market_db
    monkeypatch.setattr(market_db, "DB_PATH", tmp_path_factory.getbasetemp() / "no-market" / "market.db")
