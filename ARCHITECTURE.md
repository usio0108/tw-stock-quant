# 整體架構

> 本檔是「規劃中的整體架構」，每個部分標示現況：✅ 已完成　🟡 部分完成　⬜ 尚未開始。
> 目前進度與待辦見 [todo.md](todo.md)；決策原因、踩坑與慣例見 [NOTES.md](NOTES.md)；
> 專題規格與核對紀錄在 [docs/reference/](docs/reference/)。

**最終目標**：系統定期掃全市場，輸出「可以買哪檔股票、在什麼時機買賣」的可操作建議：
定期掃全市場 → 四層篩選候選股 → 投組優化配置 → GitHub Actions 定時執行 → Telegram 推播。
不依賴付費黑盒子，完全自控。

目標使用者是一般大眾（投資與程式皆入門），介面原則：每個數字旁有一句白話說明、結論優先、支援手機。

## 一、三層架構：中台 / 前端 / 後端

**中台是唯一向外部來源（yfinance／twstock／FinMind／…）抓資料的地方**，前端和後端都跟中台要資料。
理由：前端要顯示、後端要計算，兩邊要的是同一份 raw 資料，各自抓會延遲疊加、邏輯分岔。

| 層 | 位置 | 職責 | 狀態 |
|----|------|------|------|
| 中台 | `backend/data_service/` | FastAPI（port 8001），只回 raw 資料不算指標；記憶體 TTL＋SQLite 快取 | ✅ |
| 前端 | `frontend/` | Next.js 16 + Tailwind v4 + shadcn/ui（base-nova）+ lightweight-charts，只負責顯示；頁面 `/market`、`/stock/[ticker]`、`/watchlist`、`/screening`，另有 `/docs` 資料參考書（每個數字的來源、意義、TTL 與真實／估算／示範資料狀態，內容在 `frontend/src/lib/data-sources.ts`，與下方真實 vs mock 表同步維護） | ✅ 建皮；🟡 部分欄位仍 mock |
| 後端（計算層） | `backend/indicators/`、`backend/screening/`、`backend/api/` | 共用指標、選股規則、個股 JSON 組裝 | 🟡 |

中台 HTTP contract 是給後端隊友的穩定介面，改 endpoint 或回傳格式前一律先問使用者；endpoint 見 [中台文件](backend/data_service/README.md)。

### 1.1 目錄結構

```text
tw-stock-quant/
├── frontend/                 # Next.js 頁面、元件與 /api Route Handlers
│   └── src/
│       ├── app/
│       ├── components/       # 六層 K 線圖、指標說明與速查卡
│       └── lib/              # 中台 client、Python 子程序、指標判讀與合約型別
├── backend/                  # Python 程式，與前端共用根目錄的 uv 環境
│   ├── api/                  # get_stock_data.py（個股 JSON）、screen_stock.py、check_fundamentals.py、screen_fundamental.py
│   ├── data/                 # market_db.py（data/market.db）、securities_sync.py（ISIN 清單同步）、universe.py（清單與市場代碼解析）
│   ├── screening/            # technical.py、fundamental.py、fundamental_quality.py
│   ├── indicators/           # 共用數值指標、TA-Lib K 線型態、fundamental.py
│   └── data_service/         # FastAPI raw 資料 API
│       ├── main.py
│       ├── sources/          # yfinance／twstock／FinMind（fundamental.py）／官方年度財報
│       ├── cache.py          # 記憶體 TTL
│       └── store.py          # SQLite 歷史 K 線
├── data/                     # 執行期資料，data/cache.db 保留既有位置（gitignored）
├── tests/                    # 指標數值、離線合約、品質阻擋與資料位置驗證
├── scripts/                  # 本機啟動及部署 smoke check
├── docs/                     # MAINTAINERS.md、stock-data-audit.md、reference/
├── .github/workflows/        # CI 與 self-hosted runner 部署
├── Dockerfile
├── docker-compose.yaml
└── pyproject.toml / uv.lock
```

### 1.2 資料流

瀏覽器向 Next.js 的 `/api` 請求資料。部分 Route Handler 直接代理中台 HTTP API；
個股 K 線與基本面研究則由 `frontend/src/lib/run-python.ts` 在前端容器以 `uv run python -m backend.api.…`
啟動 Python 模組，向中台要 raw 資料，用 `backend.indicators` 計算後透過 stdout 回傳 JSON。

- **K 線與指標** ✅：個股 JSON 含 `sma20`／`sma60`、`rsi`、`macd`、`kd`、`atr14`、均量與型態（TA-Lib，只回最近 5 根）；
  圖表六個 pane 依序是 K 線與 SMA、成交量、RSI、MACD、KD、ATR；速查與圖表使用同一份計算序列。
  中台回 `stale_adjust:true` 時 wrapper 在計算前停止，Route Handler 回 503，前端隱藏舊資料並自動重試。
  驗證見 [指標驗證](docs/reference/indicator-review.md)。
- **股票清單與市場別** ✅：`backend.data.universe` 優先讀 `data/market.db`（由證交所 ISIN 清單同步），
  沒有資料時退回 twstock 本機快照並記 warning（`universe_source()` 回報實際來源）；上市 `.TW`、上櫃 `.TWO`，
  K 線、前收盤、基本面、分時與 SQLite 鍵共用同一解析，未知代碼在網路抓取前回 404。
- **單股技術篩選** ✅：`backend.api.screen_stock` 向中台取一年日 K，排除當日後交給純計算的
  `evaluate_technical`；品質／來源問題回 null 分數。僅 Python／CLI 使用，不新增 HTTP endpoint，
  亦不替換 `/api/screening` 的示範合約。見 [技術篩選](docs/reference/technical-screening.md)。
- **基本面研究** 🟡：中台 `/stocks/{ticker}/fundamentals` 依類型取 FinMind 三張財報、月營收與股利
  （1800 秒記憶體快取，不另存 SQLite）；`backend.api.screen_fundamental` 組合
  `indicators/fundamental.py` 與 `screening/fundamental.py`；`check_fundamentals` 依
  `data/fundamental_references.json` 回品質摘要；`backend/data/fundamental_supplements.json`
  保存官方財報人工核對補充。整體 passed 保持 null，尚無已驗證候選名單。
  見 [基本面計算](docs/reference/fundamental-screening.md)、[基本面資料核對](docs/reference/fundamental-data-review.md)。
- **自選股** ✅：存瀏覽器 localStorage（單機）；多裝置同步成為實際需求時再評估後端保存。

### 1.3 部署

Docker image 同時包含 Node 與 Python，分成前端、中台與 `securities-sync` 三個服務（`docker-compose.yaml`）；
`securities-sync` 在容器啟動時與每天台北 02:00 各跑一次 `python -m backend.data.securities_sync`，寫入 `stock-data` volume 的 `data/market.db`。
對外僅發布前端 `BIND_ADDRESS:PORT`（預設 `127.0.0.1:3000`），中台透過 Compose 內網
`http://data-service:8001` 存取，模組路徑 `backend.data_service.main:app`；SQLite 掛 `stock-data` volume。
`.github/workflows/deploy.yml` 在雲端跑離線測試與 Docker build，main 通過後由
`[self-hosted, Linux, X64, tw-stock]` runner 部署到 `/mnt/ssd/self-proj/tw-stock-quant` 的精確 SHA（✅）。
操作步驟見 [MAINTAINERS.md](docs/MAINTAINERS.md)。每週選股的 GitHub Actions 排程 ⬜（骨架見 [todo.md](todo.md)）。

## 二、四層篩選架構（系統大腦）

```
第一層：總體環境過濾 ⬜
    ↓（大環境不對，全面縮手）
第二層：基本面初篩 🟡
    ↓（財務有問題的，直接排除）
第三層：籌碼面確認 ⬜
    ↓（沒有法人撐腰，跳過）
第四層：技術面擇時 🟡
    ↓（選對股，還要選對時機進出）
輸出：買賣訊號 + 配置比例 ⬜
```

### 第一層：總體環境 ⬜ — 現在適合操作嗎？

| 指標 | 觀察什麼 | 影響 |
|------|----------|------|
| 景氣燈號（國發會） | 紅燈=過熱、藍燈=衰退、綠燈=正常 | 藍燈區間降低持股比例 |
| 美債 10Y 殖利率 | 快速走升代表資金成本增加 | 成長股估值承壓，減少高本益比標的 |
| USD/TWD 匯率 | 外資匯率收益影響進出意願 | 台幣大幅貶值時，外資容易撤出 |
| 市場廣度（漲跌家數） | 多數股票在漲 vs 只有少數在漲 | 廣度萎縮是行情末段警訊 |

> USD/TWD 特別重要：台積電、聯發科收入以美元計價，USD/TWD 每動 1 元，台積電季 EPS 差約 0.3–0.5 元；USD 走強時外資傾向撤出新興市場。

**判斷結果**：多頭（景氣綠燈以上、美債穩定）→ 滿倉積極；盤整（訊號混雜）→ 半倉只選最強；空頭（藍燈、外資大賣）→ 縮手持現金。

### 第二層：基本面初篩 🟡 — 這家公司值得研究嗎？

**硬性門檻（不符合就排除）**：ROE > 12%；近 4 季 EPS 均為正；月營收近 3 個月 YoY > 0%；Piotroski F-score ≥ 6。
✅ 四項研究門檻已有純計算（`backend/screening/fundamental.py`）；缺值與品質限制下結果保持 null。

**加分項（提高排名）**：月營收 YoY > 10%；FCF 轉換率 > 80%；殖利率 > 4%；Altman Z-score > 2.99。
⬜ FCF 轉換率與 Altman Z-score 尚未實作，口徑待定。

### 第三層：籌碼面確認 ⬜ — 有大戶在買嗎？

| 籌碼訊號 | 意義 | 操作含義 |
|----------|------|----------|
| 外資連續買超 5 日以上 | 外資認同 | 加分 |
| 投信連續買超（月底前） | 基金建倉 | 加分，特別是季報前 |
| 外資 + 投信同步買 | 法人齊買 | 強力加分 |
| 融資餘額大幅攀升 | 散戶借錢追高 | 減分，小心反轉 |
| 融券大增 | 有人放空 | 注意，但回補也會拉升 |

**排除條件**：融資餘額佔流通股本 > 5%（過度散戶化，籌碼不穩定）。

### 第四層：技術面擇時 🟡 — 什麼時候進？什麼時候出？

**買進**（需同時符合）。單股 technical-v1 ✅ 已實作下列技術門檻，僅代表技術篩選通過；
分數權重、交叉定義、排除當日 K 的限制見 [技術篩選規格](docs/reference/technical-screening.md)。
尚未合併前三層資料，也未驗證為可獲利策略。
- 趨勢（必要）：站上 20MA 且 20MA > 60MA；MACD 零軸以上或金叉剛形成
- 動能（至少一）：RSI 40–70；KD 金叉且 K < 80
- 量能（必要）：本根成交量 > 前 5 根日 K 均量 1.5 倍（不含本根）；v1 不另宣稱突破事件
- K 線型態加分（選配）：晨星、錘子線、吞噬（TA-Lib）

**賣出**（後續持倉／回測模組 ⬜ 尚未實作；觸發任一）：
- 止損（優先）：跌破進場價 7%；跌破 20MA 且放量；ATR 停損（進場價 − 2×ATR）
- 獲利出場：RSI > 75 且回頭；MACD 死叉且放量；月營收連 3 個月 YoY 轉負

### 輸出格式 ⬜

每週五收盤後產出：

```
== 本週選股推薦（YYYY-MM-DD） ==
總體環境：多頭 ✅　推薦操作強度：積極

| 排名 | 股票 | 買進理由（三層）| 建議進場區間 | 停損 | 配置比例 |
| 1 | 2330 台積電 | 法人連買 7 日 / RSI 52 / MACD 金叉 | 900–920 | 860 | 20% |
...
風險提示：本清單僅為參考，不構成投資建議。
```

### 資料流（規劃）

```
【第一層：總體環境】 ⬜
data.gov.tw / yfinance / FRED / TWSE OpenAPI
        └── macro/context.py → 市場環境分類 → 決定本週操作強度

【第二層：基本面篩選】 🟡
FinMind → 中台 /stocks/{ticker}/fundamentals（五類 raw；✅ 已接入）
                └── indicators/fundamental.py（ROE／YoY／F-score ✅；FCF、Altman ⬜）
                └── screening/fundamental.py → 單股研究條件，品質與缺項仍限制判定

【第三層：籌碼面確認】 ⬜
FinMind（法人買賣超 / 融資券）
        └── screening/chip.py → 法人買超確認

【第四層：技術面擇時】 🟡
中台 raw candles → add_indicators()（TA-Lib）✅
        └── screening/technical.py → 單股規則／分數／理由 ✅
                └── ATR 停損／持倉／賣出訊號 ⬜

【整合輸出】 ⬜
scorer.py（四層加權評分）
    └── 每週 TOP 20 候選股
            └── pyportfolioopt → 配置比例
                    └── Telegram 推播（每週五收盤後）
```

## 三、資料儲存與資料表

| 項目 | 狀態 | 說明 |
|------|------|------|
| SQLite `data/cache.db`：`candles`（ticker, interval, ts, OHLCV, fetched_at） | ✅ | 日／週／月 K 持久化，增量補缺口並偵測除權息；分鐘 K 等即時資料不落地 |
| `source_meta`（ticker, interval, source_start） | ✅ | 記錄資料源最早日期，新上市股票避免反覆全抓 |
| `adjustment_pending`（ticker, interval） | ✅ | 待還原狀態，跨請求與重啟保留，完整區間重抓成功才清除 |
| `official_filings`（ticker, year, sha256, fetched_at, valid, raw） | ✅ | 官方年度財報原件與 SHA 版本，24 小時快取 |
| SQLite `data/market.db`：`securities`（ticker, name, isin, market, sec_type, industry, isin_listed_on, active, first_seen_on, last_seen_on, source, fetched_at） | ✅ | **永久資料**（與可重建的 cache.db 分開）。證交所 ISIN 上市／上櫃清單（不含權證）；下市不刪列，`active=0`＋`last_seen_on` 表示「自該日起不在清單上」 |
| `securities_changes`（ticker, field, old_value, new_value, detected_on, source） | ✅ | 名稱／ISIN／市場／類型／產業／上市日變動與 active 轉換的歷史 |
| `fetch_log`（source, endpoint, started_at, finished_at, status, row_count, error） | ✅ | 每次同步抓取結果（ok／empty／error），失敗時不改動其他表 |
| `securities-sync` 服務（`backend/data/securities_sync.py`） | ✅ | docker-compose 內於啟動時與每天台北 02:00 同步；任一市場抓取或解析失敗、某市場零股票列、或單市場將下架超過 5% 皆整批中止 |
| 記憶體 TTL 快取（`cache.py`） | ✅ | 五檔／分時／指數 30 秒、K 線 60 秒、基本面 1800 秒 |
| 人工核對 JSON（`fundamental_references.json`、`fundamental_supplements.json`） | ✅ | 公告參考值與官方財報補充，不覆寫 raw |
| `data/raw/`、`processed/`、`chip/`、`macro/`、`universe/`（Parquet） | ⬜ | 原藍圖的批次資料落地目錄；Parquet 降級為未來「回測批次匯出」的可選格式 |
| 籌碼、總體、選股結果等資料表 | ⬜ | 尚未設計 schema，待 Phase 5／6 資料源接入時才定 |

### 3.1 規劃中的資料表（⬜ 草案，對應 [stock-data-audit.md](docs/stock-data-audit.md) S01–S14）

設計原則：每列都記 `source` 與 `fetched_at`，另存來源自身的 `trade_date`／`as_of`；單位寫進欄位名（`volume_shares`／`volume_lots`／`*_twd`／`*_pct`）；NULL＝未知、0＝真的零，不設 `DEFAULT 0`；週月 K 由日 K 彙整、3／5／15 分 K 由 1 分 K 彙整，指標即時計算不落地。價格建議以 INTEGER 存 0.01 元，避免浮點誤差。

| 資料表 | 主鍵 | 主要欄位 | 對應 |
|------|------|------|------|
| `securities`（✅ 已上線於 market.db，欄位見上表） | ticker | 以 active／last_seen_on 取代 delisted_on | S01 |
| `daily_prices_raw` | ticker, trade_date | 官方未還原 OHLC、volume_shares、turnover_twd、trades | S02 |
| `daily_prices_adjusted` | ticker, trade_date | Fugle 還原 OHLC、volume_shares；事件後整檔重抓覆蓋 | S02 |
| `minute_bars` | ticker, ts | 只存 1 分 K、volume_lots（張）；無成交不補棒；ts 為來源標示時間，非精確成交時間 | S03 |
| `daily_limits` | ticker, trade_date | reference_price, limit_up, limit_down, has_price_limit | S04 |
| `valuation_daily` | ticker, trade_date, source | pe, pb, dividend_yield_pct, financial_period | S05 |
| `share_capital` | ticker, as_of | issued_shares, paid_in_capital_twd | S05 |
| `financial_items`（長表） | ticker, statement, period_end, period_type, item, source | value, scope, published_on；period_type 分 Q／YTD／FY | S10–S12 |
| `monthly_revenue` | ticker, revenue_month, source | revenue_twd, published_on（所屬月≠公告日） | S13 |
| `dividends` | — | fiscal_year, 現金／股票股利, 除權息日, 發放日, raw_json | S14 |
| `index_daily` | index_code, trade_date | close；國際指數用當地市場日期 | S08–S09 |
| `fetch_log`（✅ 已上線於 market.db，尚無 params 欄） | id | source, endpoint, started_at, finished_at, status（ok／empty／error）, row_count, error | 解 R05 |

五檔、盤中分時、盤中指數維持記憶體快取不落地。新表上線後再淘汰現有 `candles`。

## 四、`backend/` 目標目錄（Phase 逐步建立）

`frontend/` 與 `backend/data_service/` 已存在；以下是計算層藍圖，✅ 已有、⬜ 尚未建立：

```
backend/
├── api/         ✅ 個股與篩選入口（get_stock_data、screen_stock、screen_fundamental、check_fundamentals）
├── data_service/ ✅ 資料抓取、TTL、SQLite，中台唯一入口
├── data/        🟡 universe ✅；chip、macro ⬜（fetcher／store 已由中台取代）
├── indicators/  🟡 SMA/EMA/RSI/KD/MACD/ATR/均量、pattern、fundamental ✅；其餘有規則需要再加
├── strategies/  ⬜ base(台股邏輯), ma_cross, rsi_reversal, macd_trend（回測屬隊友範圍）
├── backtest/    ⬜ runner, optimizer, metrics（隊友 branch）
├── screening/   🟡 technical、fundamental、fundamental_quality ✅；chip、scorer ⬜
├── portfolio/   ⬜ optimizer（pyportfolioopt）
├── macro/       ⬜ context（第一層判斷）
├── sentiment/   ⬜ trends, nlp
├── events/      ⬜ study
├── alerts/      ⬜ scheduler, notify
└── report/      ⬜ chart, summary
```

## 五、真實 vs mock 資料對照

**mock 絕對不能看起來像真的**——本系統產出投資決策，錯誤數據是安全問題。判斷標準：yfinance／twstock 免金鑰拿得到的就接真的，拿不到的用 mock 佔位但型別合約先定好。具體做法見 [NOTES.md](NOTES.md#資料誠實三條規則)。面向使用者的白話版見前端 `/docs`（資料參考書），改動下表時一併更新 `frontend/src/lib/data-sources.ts`。

| 資料 | 狀態 | 來源 / 等什麼 |
|------|------|--------------|
| 加權指數、國際指數 | ✅ 真實 | yfinance `^TWII`／`^DJI`／`^IXIC`／`^N225`／`000001.SS` |
| 櫃買指數 | ⬜ 無資料源 | yfinance `^TWOII` 已查不到（2026-07-29 實測 `^TWOII`／`^TWO`／`^TPEX` 全回 0 筆）。中台回 `null`、UI 顯示「—」，不捏造 0；要接真的得另找 TPEx OpenAPI |
| 個股／大盤分時走勢（今日 1 分 K） | ✅ 真實 | yfinance `period=1d interval=1m` |
| 個股 K 線（7 種週期） | ✅ 真實 | 中台 ← yfinance |
| 個股 PE／PB／殖利率／市值／EPS／52 週高低／目標價 | ✅ 真實 | yfinance `Ticker.info` |
| 產業別、上市／上櫃 | ✅ 真實 | market.db（證交所 ISIN 清單），無資料時退回 twstock 本地查表 |
| 五檔報價 | ✅ 真實 | `twstock.realtime.get()`（盤後 asks／bids 可能空陣列） |
| 漲跌停價 | ✅ 真實計算 | 前收盤 ±10% 依跳動單位取整 |
| K 線型態辨識 | ✅ 真實計算 | `backend/indicators/pattern.py` 用 TA-Lib 辨識晨星／黃昏星／錘子線／上吊線／吞噬，只回最近 5 根；沒有訊號時回空陣列 |
| 月營收／三張財報／股利原始資料 | 🟡 真實，前端月營收已換真 | FinMind fundamentals 入口＋計算層；部分年度 F-score 輸入由官方財報人工核對，非全市場自動更新 |
| USD/TWD、美債 10Y | ⬜ mock | yfinance 其實拿得到（`USDTWD=X`、`^TNX`），等 `/api/market` 其他欄位一起換 |
| 景氣燈號、市場廣度、三大法人 | ⬜ mock | Phase 1 + Phase 5（FinMind／data.gov.tw） |
| 個股籌碼（法人／融資券／大戶） | ⬜ mock | Phase 5 FinMind |
| 台指期貨、外資未平倉 | ⬜ mock | 無免費來源，要另找（券商 API） |
| 排行榜（類股／成交值／漲跌幅） | ⬜ mock | 需全市場掃描，Phase 1 + 6 |
| 新聞（個股／大盤） | ⬜ mock | 全市場新聞牆要另找來源 |
| 選股結果、投組配置（`/api/screening`） | ⬜ mock | 自建計算層（評分／優化）；單股技術篩選與基本面研究已有 Python／CLI，但尚未接進此頁 |

## 六、工具索引

### 資料來源

| 工具 | 用途 | 備註 |
|------|------|------|
| `twstock` | 台股 K 線、即時報價、五檔 | PyPI 版；代碼表更新見 [NOTES.md](NOTES.md#python-環境) |
| `yfinance` | K 線、指數、匯率（`USDTWD=X`）、美債（`^TNX`）、`Ticker.info` | 免金鑰；NaN 坑見 [NOTES.md](NOTES.md#資料層踩坑) |
| `CasualMarket` | 選用 MCP 研究工具 | 執行期基本面改用 FinMind HTTP，不需另部署 MCP |
| FinMind HTTP／`finmind` | 原始財報、月營收、股利已接入；三大法人、融資券、股東結構待 Phase 5 | 中台用標準函式庫，SDK 僅 research；免費額度約 600 req/hr，依帳號及來源政策 |
| `fredapi` | 美債備援 | 需 `FRED_API_KEY` |
| TWSE OpenAPI／data.gov.tw #6099 | 漲跌家數／景氣燈號 | `requests` 直打；Phase 5 |
| `feedparser` | TWSE 重大訊息 RSS | Phase 6 |

### 分析／基礎設施

| 工具 | 用途 |
|------|------|
| `TA-Lib` | 技術指標、61 種 K 線型態（source 編譯；`make` 單執行緒不加 `-j`；只在 uv venv） |
| `backtesting.py` | 策略回測（Phase 3，隊友範圍） |
| `alphalens-reloaded`／`pyportfolioopt` | 因子分析（Phase 7）／投組優化（Phase 6） |
| `statsmodels`／`scipy`／`scikit-learn` | 事件研究、統計檢定（Phase 7+） |
| `pyarrow` | Parquet 匯出（回測資料集，需要時再用；快取已定案用 SQLite） |
| `apscheduler`／`python-telegram-bot` | 本機測試排程／推播（Phase 6） |
| `pytrends` | Google Trends 情緒（Phase 8） |

## 七、考量區（參考，尚未採用；2026-10-16）

參考 [Open-Dev-Society/OpenStock](https://github.com/Open-Dev-Society/OpenStock)。以下記錄可借鏡的產品設計，不視為新增需求或已排定開發，也不替代目前技術篩選的回測驗證。

| 可參考項目 | 對本專案的考量 |
|---|---|
| 個股資訊分區 | 圖表、技術摘要、財務、公司介紹分區，讓使用者容易找到數字與來源；整體選股接真資料時再評估摘要配置。 |
| 全域快捷搜尋 | OpenStock 提供 Cmd/Ctrl+K、搜尋防抖與預設熱門股票。現有代碼／名稱搜尋可先沿用，有跨頁操作需求時再考慮快捷入口。 |
| 個人自選股 | OpenStock 使用帳號與資料庫保存自選股；本專案目前為 localStorage，多裝置同步成為實際需求時再評估後端保存。 |
| 資料可用性呈現 | 依市場、資料商能力顯示可用資訊，圖表不可嵌入時提供外部連結；可借鏡其延遲行情、來源限制與缺資料狀態說明。 |

來源：[功能與架構](https://github.com/Open-Dev-Society/OpenStock#readme)、[個股頁實作](https://github.com/Open-Dev-Society/OpenStock/blob/main/app/%28root%29/stocks/%5Bsymbol%5D/page.tsx)、[市場限制](https://github.com/Open-Dev-Society/OpenStock/blob/main/MARKET_SUPPORT.md)。檢查的是目前 main，後續採用前仍需核對版本。

OpenStock 的技術面摘要使用 TradingView 的嵌入 widget，不是可直接沿用的 Python 選股引擎。它的市場支援文件也列出台灣嵌入 K 線及 Finnhub 免費報價限制。程式庫目前標示 [AGPL-3.0](https://github.com/Open-Dev-Society/OpenStock/blob/main/LICENSE)；本專案為 MIT，搬用程式前需確認授權相容性，介面構想參考與複製程式分開評估。

**TradingView 名詞區分**：

- [TradingView 網站](https://www.tradingview.com/)：線上看盤與分析平台，提供圖表、指標、篩選與社群。
- [Lightweight Charts](https://www.tradingview.com/lightweight-charts/)：TradingView 提供的圖表程式庫，本專案用它繪圖；行情由本專案中台供應，指標與分數由 Python 計算。
- TradingView widget：外部服務提供的可嵌入元件；OpenStock 個股頁使用它呈現圖表與技術摘要。
- [Technical Ratings](https://www.tradingview.com/support/solutions/43000614331-technical-ratings/)：公開的多指標評級規格，可考慮作評分對照基準；尚未採用。完整規格包含 26 項，不可用本專案現有少數指標就宣稱已完整對齊，也不等於已驗證的交易策略。

目前 technical-v1 的自訂權重仍是實驗設定。後續評估先比較規則來源、台股資料可取得性及回測方式，再決定是否保留、調整或採用其他評級；沒有因這次調查直接更換算法。
