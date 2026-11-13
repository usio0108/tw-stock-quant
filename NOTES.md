# 開發筆記

> 只記「影響架構或未來會忘記原因」的決策、踩坑與慣例，且只留最終狀態，不寫流水帳。
> 規劃架構與真實／mock 對照見 [ARCHITECTURE.md](ARCHITECTURE.md)；進度與待辦見 [todo.md](todo.md)。

## 關鍵決策與原因

| 決策 | 原因 |
|------|------|
| 不用 FinLab | 付費，要完全自控 |
| 推播用 Telegram Bot | LINE Notify 已於 2025 停止服務 |
| 籌碼面用 FinMind | TWSE 官方 API 格式散，FinMind 整合好（免費 600 req/hr） |
| 事件研究自建（`statsmodels`+`scipy`） | PyPI 無現成台股套件，約 100 行 |
| Dashboard 用 Next.js（非 Streamlit） | 目標使用者是一般大眾，需手機支援與視覺公信力 |
| Docker Compose＋self-hosted runner 部署 | 同一 Node＋Python image 分別跑前端與中台，main CI 通過後部署指定 SHA；取代早期 Vercel／Railway／Render 規劃，設定見 [MAINTAINERS.md](docs/MAINTAINERS.md) |
| 資料中台獨立成 `backend/data_service/`（FastAPI） | 前後端都要 raw 資料；隊友需要穩定的 HTTP contract，不該讀 Next.js 內部細節 |
| 快取持久化選 SQLite 不選 Parquet | 每日補 K 棒、除權息覆寫都是逐列 upsert，SQLite 天生支援；Parquet 一次寫整檔不適合快取，降級為未來回測匯出格式（2026-07-23） |
| 指標共用入口在 `backend/indicators/`，個股 wrapper 在 `backend/api/get_stock_data.py` | 個股頁與未來批次掃描共用計算，JSON 組裝不混入資料中台 |
| 深色主題寫死 `<html className="dark">`，不用 next-themes | 本來就沒有亮色 variant、沒有 toggle UI；系統偏好偵測整套用不到 |
| 選股表排序手刻 `useState`，不裝 TanStack Table | 只有 3 欄要排序；表格複雜度提高再換 |
| 正式排程用 GitHub Actions，APScheduler 僅本機測試 | 雲端免費、電腦關著也能跑 |
| Route Handler 用 `uv run python` 不用系統 `python3` | Windows PATH 的 `python3` 會解析到 Store stub 靜默失敗；順帶讓前後端共用同一個 `.venv`，TA-Lib 兩邊都可用（2026-09-20） |
| Phase 維持水平順序推進（1→2→…→6），不改成先跑通最小管線 | 2026-09-22 討論後決定；Phase 3 回測是隊友範圍，跳過而非重排 |
| PTT 情緒分析直接呼叫 Claude API | 不跑本地 NLP 模型 |
| 圖表漲跌色與文字漲跌色不統一 | `--stock-up/--stock-down` 是圖表用色（#EF5350/#26A69A），文字用的 `text-red-400`/`text-emerald-400` 依 WCAG 對比度實測選定；硬統一會破壞無障礙合規。只集中重複的圖表色碼（`frontend/src/lib/chart-colors.ts`），兩邊都註記區別 |
| 證券清單存永久庫 `data/market.db`，不放 `cache.db`；用 `active`＋`last_seen_on`，不存下市日；同步有 5% 安全閥（2026-11） | cache.db 是可重建的行情快取，market.db 是不能隨手刪的永久資料（變動歷史 `securities_changes`、`fetch_log`）。ISIN 清單只列現存證券，沒有下市日，所以只能記「最後一次在清單上」；`isin_listed_on` 也不一定是首次掛牌日。頁面壞掉或改版時（某市場零股票列、或單市場一次下架超過 5%）整批中止、不寫任何資料，只記 `fetch_log` error，避免誤把全市場標成下市 |
| 單股技術篩選只放 Python／CLI，不新增 HTTP endpoint、不替換 `/api/screening` | technical-v1 權重是實驗設定，分數不代表勝率；中台 contract 改動需先問使用者 |

## API 合約原則（接後端時的關鍵）

1. 前端元件（`*-view.tsx`）只透過 `fetch('/api/...')` 拿資料，不 import mock 物件、不直接呼叫 Python。
2. **Route Handler 回傳的 JSON 形狀＝未來後端 API 的合約**，單一定義來源在 `frontend/src/lib/types.ts`（每個 interface 上方標註「[真實]/[mock]」＋資料來源）。
3. 換資料來源（mock → 真後端）只改 Route Handler 內部，JSON 形狀不變，前端元件零改動。
4. 選股結果（`/api/screening`）**不經過中台**：評分／進場停損／配置% 是計算產出（後端工作範圍），不是中台該抓的 raw 資料。
5. 中台 HTTP contract 是給後端隊友的穩定介面，改 endpoint 或回傳格式前一律先問使用者。中台只回 raw，不算指標。
6. 個股 JSON 合約擴充：新增 `kd`、`atr14`、`stale_adjust`；中台回 `stale_adjust:true` 時 wrapper 只回錯誤與旗標，Route Handler 回 503；成功回應帶 `stale_adjust:false`。

## 資料誠實三條規則

改動 mock 相關畫面時照這個做（2026-07-29 稽核後定案）：

1. **畫面上每個 mock 區塊都要掛視覺標記**，用共用元件 `frontend/src/components/mock-badge.tsx`：`<MockBadge reason="等什麼資料源" />` 是行內小標籤（`<StatCard>` 直接傳 `mock` / `mockReason` prop），`<MockNotice>` 是整區／整頁都 mock 時的橫幅。
2. **抓不到資料就回 `null`，不要回 `0` 或任何「看起來合法」的預設值**——呼叫端負責顯示成「—」。捏造的 0 比空白危險得多（櫃買指數就是踩過這個坑；`fetch_profile()` 缺值 `0` 也已改 `None`）。
3. **不要生成假的「訊號」或「判斷」**。純數字佔位加標記還能接受，但「錘子線／偏多」這種會被當成建議的假結論一律不做，寧可空白（K 線型態辨識就是為此改成沒訊號回空陣列）。

另：錯誤畫面不要直接渲染後端回傳的錯誤字串（會把技術訊息丟給使用者），一律顯示自己寫的中文提示。

## Python 環境

只有一個：`uv run` 的 `.venv`。中台 `backend/data_service/` 與 Next.js Route Handler 呼叫的 `backend/api/*` **都跑在專案 `.venv`**——`frontend/src/lib/run-python.ts` 用 `execFile("uv", ["run", "python", ...])`，不依賴系統 PATH 上的 `python3`。所以 TA-Lib 兩邊都可用。

- Windows 上 PATH 的 `python3` 常解析到 Microsoft Store 的 app-execution-alias stub，跑起來沒 stdout 也沒錯誤，只讓呼叫端 `JSON.parse` 失敗——不要改回 `python3`。
- pytest 的 `tmp_path` 預設寫 `%TEMP%\pytest-of-<user>`，沙箱／隔離 worktree 用受限身分會被 Windows 拒絕存取。`pyproject.toml` 已用 `addopts = "--basetemp=.pytest_tmp"` 固定放 repo 內（已 gitignore），不要移除；也不要改系統 `TEMP` 來繞。
- twstock 股票代碼表會過期（新掛牌股票查不到名稱／產業別），需要時跑 `uv run python -c "import twstock; twstock.codes.fetch.__update_codes()"` 更新一次。twstock 用 PyPI 版（`>=1.5.1`），原本的本地 editable fork 已刪除。
- 本機啟動：`./scripts/dev.sh` 同時啟動中台＋前端；中台單獨跑 `uv run uvicorn backend.data_service.main:app --reload --port 8001`（`/docs` 有互動文件）。
- 本機預覽避開 Forge 的 3000，使用 3107，指令見 [MAINTAINERS.md](docs/MAINTAINERS.md#本機預覽與重新建置)。
- 呼叫 FinMind 需 token 時本機用 `uv run --env-file .env`；Compose 會把根目錄 `.env` 傳給中台。token 只放 header。

## 資料層踩坑

**行情**
- yfinance 未收盤當天會多一筆 OHLC 全 NaN 的列，抓完立刻 `dropna`——NaN 進 JSON 會讓前端 `JSON.parse` 直接炸掉。
- yfinance 還原價尾數會抖 ±0.01（同一支 API 隔幾分鐘再打就可能變一位），是 Yahoo 端行為不是 bug；除權息偵測門檻 0.1%（增量時重疊抓 5 根比對 close，相對差 >0.1% 即整段重抓覆寫）遠大於抖動（約 0.001%），不會誤觸發。
- yfinance period 的左緣語意（SQLite 快取 serve 起點照這個做，2330 基準實測）：日線＝首根 >= 切點；週線＝含切點那週的週一；月線＝切點後下一個月初（切點是 1 號則含當月）。
- 指數 ticker（`^TWII` 等）分鐘線 Volume 全 0，`IntradayChart` 偵測到就不畫成交量子圖。
- 漲跌停是「日」的概念：必須固定用日線前收盤（`_prev_daily_close()`）算，不能拿輸出清單的倒數第二根，否則同一天選不同週期會得到不同漲跌停價；取不到回 `null`。
- RSI 用 Wilder's smoothing（種子＝前 14 根簡單平均，之後遞迴平滑），簡單移動平均會與 TradingView／券商對不上。資料不足一個 window 時退回中性值 50，不可 `IndexError`。
- 除權息重抓失敗回 `stale_adjust` 並持久化待還原狀態（SQLite，跨請求與重啟不解除，完整區間重抓成功才原子清除，同時失效其他週期行情快取）。
- `ttl_cache` 以固定 64 把分段鎖合併同 key 請求，最多保存 256 筆，不同 key 碰撞時可能串行。
- 市場資料與歷史 K 快取不提交；`data/cache.db*`、`data/raw/` 皆 gitignored。
- 同一支腳本遇到「已處理的已知錯誤」（如查無代碼）要 `sys.exit(0)` 並印 JSON，因為 `run-python.ts` 的 `execFile` 遇非 0 exit code 會丟掉 stdout。

**股票清單**
- `backend/data/universe.py` 優先讀 `data/market.db`（`securities_sync` 從證交所 ISIN 清單同步），沒有資料才退回已安裝的 twstock 代碼表（快照，曾為上市 1045、上櫃 880；與 ISIN 清單差距見稽核報告），退回時記一次 warning。
- ETF／權證／特別股不進選股清單，但已知 ETF 等直接查詢保留；未知或不支援市場回 HTTP 404，不猜上市櫃別。舊的錯誤後綴快取不自動刪除或挪用。

**基本面（FinMind 與官方財報）**
- 月營收 `date` 與所屬月不同；`create_time` 是 FinMind 入庫日而非正式公告日，報表期末也不是公告日，所以 `end_date` 不能當歷史回測的「當時可知資料」保證。
- 單季損益與累計現金流不能直接混算；科目必須以資料表區分（如 `EquityAttributableToOwnersOfParent` 在損益表是歸母淨利）。
- 保留 0／負值／null 與 UTC 抓取時間；錯誤明確回 404／422／502／503／504，失敗不快取、不補 mock。每次只查一類資料。
- ROE 口徑固定為四季合併淨利／期初期末平均合併權益，不混歸母口徑；EPS 分季判斷不加總；營收 YoY 保留三個所屬月與去年同月本值。
- F-score 採完整前兩年度，九項輸入齊備才回總分，缺長債與普通股發行時不湊分；長債＝非流動公司債＋長期借款＋非流動租賃（排除流動部分與非借款負債），不由股本變動推測發行。一般產業版本不套金融業。
- 人工核對補充（`fundamental_supplements.json`）逐筆保留來源 SHA、頁碼與核對日期；新資料不改寫舊日期；未補年度的股票不沿用。原始 XBRL 缺值不自動改零。
- 品質結果只有 `can_screen:false`（已知落後／差異／缺值）或 `null`（尚未全面驗證），**永不回 true**；整體與各 rule.passed 保持 null，不宣稱完成已驗證候選清單。
- 公告自動追蹤只支援 2330／2409／6488／3481 的官方近期來源（每類最多兩份季業績摘要／四筆月營收，近期頁不保證歷史或月報連續完整）；環球晶聯合新聞須在正文確認 GWC 6488，不混用 SAS 5483；3481 用官方 EN/ir 新聞 API 首頁；每頁讀取上限 4,000,000 bytes、逾時 5 秒；僅納入公告日不晚於查詢截止日者。其他股票仍 unsupported。
- 2330 業績摘要（尚未經董事會通過）與完整核閱財報以 `source_kind` 區分；來源只有 Q2 時最新期別條件暫不判定。
- 依指定的 clsung/tw-stock-agent 核對實際程式的結論：它只提供行情／公司基本資料與技術分析，沒有可核對財報的工具，不能當財報來源。
- 詳細資料差異、來源與待查項目見 [基本面資料核對](docs/reference/fundamental-data-review.md)；計算規格見 [基本面計算](docs/reference/fundamental-screening.md)。

**技術篩選（technical-v1）**
- 權重固定為趨勢 30／MACD 25／動能 25／量能 15／當根偏多型態 5，前四項必須全過，分數不代表勝率；金叉比較相鄰兩根。
- CLI 保守排除台北日期的當日 K（含已收盤情況），輸出實際 `as_of`，不冒充今日訊號；資料不足、異常或還原失敗回 null 分數及原因。規則見 [技術篩選規格](docs/reference/technical-screening.md)。

## 前端慣例與踩坑

**色彩**
- **紅漲綠跌**（台股慣例，與美股相反）：所有「代表漲跌方向」的顏色——K 線、成交量柱、MACD 柱、漲跌文字、法人買賣超、多空橫幅、SignalBadge——漲／多頭=紅、跌／空頭=綠（token：`--stock-up` 紅／`--stock-down` 綠）。非方向性顏色（RSI 門檻線、景氣燈號五色、amber 警示）不套這條。
- 說明文字用語意 token `text-muted-foreground`（對比 6.9:1），**不要**寫 raw `text-zinc-500`（只有 3.7:1，WCAG AA 不過）。
- 品牌強調色 emerald：`--primary`=emerald-700（白字 5.49:1）、`--ring`=emerald-500、sidebar active 用 `--sidebar-primary`=emerald-400。這些是對比實測選的值，不要換成 emerald-600（3.77:1 不夠）。

**互動與無障礙**
- 使用者反覆點的控制項至少 44×44px（`h-11`）：代碼搜尋、週期／區間 ToggleGroup、sidebar 收合鈕。
- icon-only 按鈕加 `aria-label`；輸入框用 `<label htmlFor>`；可排序表頭加動態 `aria-sort`。
- 日期時間一律用 `lib/utils.ts` 的 `formatDateTime`／`formatTimeShort`／`formatDate`，不要直接 `toLocaleString("zh-TW")`（預設 12 小時制帶上午／下午、不補零）。
- 依 ticker 抓資料的元件要有 AbortController；非背景刷新的 fetch 一開始就清空 `data`，避免切換代碼時殘留上一支股票資料；背景自動刷新不清空（避免閃爍），並保留 K 線可視區間。
- 所有 fetch 都檢查 `res.ok` 並有錯誤畫面。

**shadcn/ui 4.12（底層 @base-ui，非 Radix）**
- ToggleGroup：`value` 是 `string[]`、單選是 `multiple={false}`（無 `type="single"`）、選中樣式用 `aria-pressed:` 前綴（無 `data-[state=on]:`）。

**lightweight-charts v5**
- 單一 chart 多 pane：`chart.addSeries(Series, opts, paneIndex)`＋`chart.panes()[i].setHeight()`，crosshair 自動同步。
- 標記用 `createSeriesMarkers(series, markers)`（不是舊版 `series.setMarkers`）。
- 時間軸一律以 **UTC** 顯示：分鐘線用「假 UTC」技巧 `calendar.timegm(ts.timetuple())`（把台北壁鐘時間欄位當 UTC 算 epoch），顯示出來才是台北時間。日／週／月線用日期字串不受影響。圖表以外要把這種 epoch 轉成文字時一律用 `formatWallClockEpoch`（UTC 解碼），用 `new Date()` 本地格式化會多 8 小時。
- 縮放下限用 `lib/chart-zoom-bound.ts` 的 `boundChartZoom()` 依資料筆數動態算 `minBarSpacing`（不能寫死常數）＋`fixLeftEdge`／`fixRightEdge`。

**開發環境**
- Turbopack persistent cache（Next 16.1+ 預設開）：dev 時出現詭異 hydration 警告且 overlay 帶 `(stale)` 標籤 → 是快取跟編輯中程式碼對不上，`pkill -f "next dev"` + `rm -rf .next` 重開即可，不要在程式碼裡找 bug。
- recharts `Pie` 要加 `isAnimationActive={false}`，否則 headless 截圖驗證會拍到動畫第一格（空圖）。
- 環境沒有 `chromium-cli`：驗證用 scratchpad `npm install playwright --no-save`（`~/.cache/ms-playwright` 已有 Chromium），不進專案 `package.json`。

## 部署與流程備忘

- main 設有 branch protection ruleset：改 main 一律走 PR（禁直接 push）、禁 force-push、禁刪除，不強制 review。日常流程＝branch → push → PR → merge。
- 分支 push 只跑 CI；合併 main 後通過 CI 才部署到 server，不能以本機驗證代替部署成功紀錄。
- 正式環境排除 research／dev 依賴，本機 `uv sync` 仍裝原有工具。Docker 的 SQLite volume 與既有 API、port、容器名稱維持原樣。
- 設定與驗收見 [MAINTAINERS.md](docs/MAINTAINERS.md)；中台 endpoint 見 [中台文件](backend/data_service/README.md)。

## 領域速查

台股費率、漲跌停與慣例見 [taiwan-market-notes](docs/reference/taiwan-market-notes.md)。回測必含交易成本：手續費買賣各 0.1425%、賣出證交稅 0.3%（ETF 0.1%）。
