# 待辦

> 現況以本檔為準：上半是目前階段計畫，下半是任務清單。規劃架構見 [ARCHITECTURE.md](ARCHITECTURE.md)，決策與踩坑見 [NOTES.md](NOTES.md)。
> 分工（2026-07-23 與隊友確認）：隊友 branch 只做**回測系統**；技術指標、選股評分、投組優化歸本專案。

## 目前階段計畫

Dashboard 建皮（Step 0–5）已全部完成；目前在自建計算層（指標 → 評分 → 優化）。Phase 維持水平順序推進 1→2→…→6（2026-09-22 決定）。

| Phase | 內容（對應四層框架） | 狀態 |
|-------|---------------------|------|
| 1 資料管線 | 中台快取持久化、股票清單、`yahoo_symbol()`、FinMind 原始資料入口 ✅；批次掃描與頻率控制 ⬜ | 🟡 |
| 2 技術指標（第四層） | `backend.indicators.add_indicators`、KD／ATR、型態、還原失敗 503 已由 [PR #7](https://github.com/neilyonglu/tw-stock-quant/pull/7) 合併；券商逐筆比對 ⬜ | ✅（比對待做） |
| 3 策略回測 | 隊友範圍：`backend/strategies/`、`backend/backtest/`，必含交易成本 | ⬜（隊友 branch） |
| 4 基本面整合（第二層） | FinMind 原始資料、TTM ROE／營收 YoY／F-score、四項研究門檻與前端呈現 ✅；FCF／Altman、全市場完整名單 ⬜ | 🟡 |
| 5 籌碼面與總體環境（第一、三層） | 法人買賣超、融資券、景氣燈號、USD/TWD、美債、漲跌家數 → `macro/context.py`、`screening/chip.py` | ⬜ |
| 6 選股系統、投組優化與排程 | 單股技術篩選 ✅；批次掃描、綜合評分、`portfolio/optimizer.py`、`alerts/`、GitHub Actions 排程、Telegram 推播 ⬜ | 🟡 |
| 7 因子分析與事件研究 | alphalens-reloaded 看 IC/IR；自建事件研究（市場模型 OLS → AR → CAR → t 檢定），驗收如「外資連買 5 日後 10 日平均 CAR」 | ⬜ |
| 8 情緒面（選配） | pytrends 搜尋熱度；PTT 情緒用 Claude API 判斷正負；併入 scorer 低權重 | ⬜ |
| 9 Dashboard 接真資料與部署 | 前端 mock 欄位換真（依賴 Phase 1/4/5/6）；Docker Compose＋self-hosted runner 部署 ✅（見 [維護文件](docs/MAINTAINERS.md)） | 🟡 |

各 Phase 驗收：
- Phase 1：能穩定拿到資料、批次掃描不打爆外部 API（twstock 對 TWSE 每 5 秒最多 3 request，批次要 sleep；FinMind 免費 600 req/hr）。抓取一律經中台，`backend/` 不直打外部來源。
- Phase 3：2330 跑 2020–2025 回測，輸出交易紀錄與績效摘要；optimizer 小心 overfitting；手續費買賣各 0.1425%、賣出證交稅 0.3%（ETF 0.1%）。
- Phase 4：能從全市場篩出基本面合格的候選清單。
- Phase 5：同一支股票在不同總體環境下排名不同。
- Phase 6：一行指令輸出本週推薦清單＋配置比例（單股上限 20%），並推播 Telegram。

## 下一個任務

- [ ] **股票資料來源稽核落地**：依 [docs/stock-data-audit.md](docs/stock-data-audit.md) 的盤點與建議逐項處理，並在動手前先確認哪些來源要換、哪些維持（稽核報告本身不改）。
  - [x] S01 股票清單：改用證交所 ISIN 上市／上櫃清單，存 `data/market.db`（`securities`／`securities_changes`／`fetch_log`），`securities-sync` 服務每日更新，無資料時退回 twstock
  - [ ] S02 以後各項（日 K、分鐘 K、漲跌停、估值、財報、月營收、股利、指數）尚未處理；公司 API 名稱交叉核對與 live 同步驗收也待做

## 現在就可以做（不依賴隊友）

- [ ] 基於股票清單做批次掃描與頻率控制，批次套用已完成的單股技術規則；尚未產生全市場真實排行榜或多因子評分
- [ ] 選股評分與投組優化；完成後 `/api/screening` mock 換真、`frontend/src/lib/types.ts` 合約對齊
- [ ] 前端剩餘 mock 欄位換真實 API：三大法人、市場廣度、排行榜、籌碼 Tab 等（完整清單見 [ARCHITECTURE.md](ARCHITECTURE.md#五真實-vs-mock-資料對照)；依賴各 Phase 資料源接入）
- [ ] 指定券商畫面逐筆驗收：需同批 OHLCV、還原、週期、起始時間與參數；目前已記錄算法差異，不宣稱各平台預設值相同（見 [指標驗證](docs/reference/indicator-review.md)）
- [ ] 確認 PR #7、#9 合併版本的 main CI 與 server 部署結果（與功能測試分開驗收）；本機已合併的舊 technical-screening 分支尚待清理
- [ ] 決定 `.agents/`（架構圖 skill 本體）與 `skills-lock.json` 要進版控還是 `.gitignore`；架構圖已刪除，若不再使用可直接移除
- [ ] 基本面後續：擴大可靠年度資料來源與自動更新、金融業模型、全市場完整已驗證名單與 FCF 轉換率／Altman Z-score；公告自動追蹤目前只支援 2330／2409／6488／3481，Q3 業績摘要已公布但 FinMind 目前僅 Q2，最新期別條件仍暫不判定（見 [基本面資料核對](docs/reference/fundamental-data-review.md)）
- [ ] 找櫃買指數的替代資料源（TPEx OpenAPI）——yfinance `^TWOII` 已失效，目前中台回 `null`、UI 顯示「—」
- [ ] `main.py` 能單獨跑完整選股流程並推播 Telegram（依賴指標＋評分完成）
- [ ] GitHub Actions workflow 骨架：建 `.github/workflows/weekly_scan.yml`

  ```yaml
  name: 每週選股掃描
  on:
    schedule:
      - cron: '0 6 * * 5'   # UTC 06:00 = 台灣時間週五 14:00（收盤後）
    workflow_dispatch:        # 也可手動觸發
  jobs:
    scan:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: astral-sh/setup-uv@v3
        - run: uv sync
        - run: uv run python main.py
          env:
            FINMIND_TOKEN: ${{ secrets.FINMIND_TOKEN }}
            TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
            TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
  ```

- [ ] GitHub repo Settings → Secrets → Actions 新增：`FINMIND_TOKEN`、`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`
- [ ] `backend/alerts/scheduler.py`（Phase 6 建立時）定位為本機測試用，正式排程走 GitHub Actions
- [ ] GitHub Actions 手動觸發驗收（依賴 `main.py` 完整流程）

## 待隊友回測 branch merge（合回 main 時逐項核對）

> 2026-09-22 盤點：remote 上沒有隊友的 branch（只有自己的 `dashboard-ui`、`cache-persistence`、`watchlist-live-refresh`），回測進度不明——先問一下她推到哪裡了。

- [ ] 核對她的 branch 與 `backend/` 的指標／評分／優化模組**沒有重複實作**——有重疊先商量再 merge，不要兩份並存
- [ ] 回測模組接入選股流程（輸入輸出合約對齊；回測結果必含交易成本，費率見 [taiwan-market-notes](docs/reference/taiwan-market-notes.md)）

## 刻意不做（避免範圍無限擴大）

看盤平台常見但暫不跟進：同類股／概念股比較、注意股／處置股清單、社群討論／多空投票、警示燈號標記。另見 [ARCHITECTURE.md](ARCHITECTURE.md#七考量區參考尚未採用2026-10-16) 的考量區（尚未採用）。

## 已完成（摘要，細節在 git 歷史）

- 環境與 Dashboard 建皮：Python 3.12＋uv、TA-Lib、twstock；三頁介面、六層 K 線、7 種週期、個股 Tabs、五檔、選股表與 CSV、響應式（2026-06 ～ 07）；無障礙稽核修正（2026-07-04）。
- 中台拆分（2026-07-01）、前端 Dashboard 併入 main（PR #1，2026-07-22）、中台 SQLite 快取持久化（2026-07-23）。
- 自選股清單／自動刷新／App 風格列表／排行榜示範頁／查無代碼畫面／股票關鍵字搜尋（共用 `ticker-search.tsx`）（2026-07-29，PR #3 合併）。
- 全 repo 稽核（2026-07-29）：修掉三條「假資料看起來像真的」與其餘 11 項（漲跌停、Wilder RSI、白屏防護、race condition、缺值語意、快取加鎖等）；全庫審查與前端審查 FE-01–07 於 2026-10-21 完成。
- Route Handler 改用 `uv run` 執行 Python（2026-09-20）；Python 目錄統一為 `backend/api` 與 `backend/data_service`；PR #6 目錄整理已合併。
- Docker／CI／`tw-stock` runner 部署（PR #5 容器改名已合併，2026-10-13 main run 38337855813 成功）。
- 指標模組（PR #7）：KD／ATR、型態、`stale_adjust` 503／隱藏／恢復，23 項測試與公開算法／參考數值對照。
- 股票清單與 `.TW`／`.TWO` 解析（PR #8）：K 線／分時／基本面／快取鍵共用，31 項測試與兩市場 Docker smoke check。
- 單股技術篩選 technical-v1（PR #9）：55 項測試、2330／6488 真實中台與 Docker CLI 通過。
- 基本面（`feature/fundamental-data`）：中台接入 FinMind 五類原始資料；品質檢查 CLI、TTM ROE／四季 EPS／營收 YoY／F-score 研究計算；官方年度財報批次查證與 SQLite 原件快取；2330／6488／2409／3481 的 2025／2024 年度 F-score 缺項由官方合併財報人工核對補齊；公告自動追蹤四家；個股基本面前端接真實六個月營收／YoY、四季 EPS、ROE、F-score 與資料品質；整體 passed 仍為 null。
