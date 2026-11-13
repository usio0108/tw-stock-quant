| Data | Example | Where | Notes |
|---|---|---|---|
| 股票代碼、名稱、市場別、證券類型、產業（S01） | `2330`、台積電、上市、股票、半導體業 | 預計以證交所 ISIN 上市及上櫃證券清單為主要來源，TWSE／TPEx OpenAPI 公司基本資料補充及交叉核對；正式程式仍使用 twstock 本機快照，尚未修改 | [universe.py:11](../backend/data/universe.py#L11)、`:19`；`stock.py:301` 搜尋。code、name、market、type、group → ticker/name/market/symbol、industry/listed_market；一般股票限 `type==股票` 且上市／上櫃，依代碼排序；`.TW`／`.TWO`；搜尋完全符合→前綴→名稱，最多 8 筆。供搜尋、各來源代碼解析、個股名稱、基本面產業分類及 `audit --all` 使用；直接查詢可包含已知 ETF，不限一般股。2026-11-13 逐筆比較 ISIN 當日清單與 twstock 1.5.1 快照：上市一般股票 1058 vs 1045，共同 1043、最新多 15、本機多 2，名稱差 2、產業差 2；上櫃 897 vs 880，共同 873、最新多 24、本機多 7，名稱差 10、產業差 13；差異不是全為新上市或下市。5236、8908 本機上櫃但官方清單上市；2867、6806 已確認下市。公司 API 上櫃與 ISIN 名稱有 12 筆差異，3489 公司名稱更名情況尚須核對證券簡稱生效日。ISIN 文件日期不一定是首次掛牌日；來源更新頻率、快取失敗及過舊處理待確認。server 應共用批次快照並保留上次完整結果；TWSE 專案限速每 5 秒最多 3 次，非官方統一規定。 |
| 日、週、月 K：日期、開盤、最高、最低、收盤、成交股數、成交金額、成交筆數（S02） | 2330，2026-10-01：開 2,490、高 2,510、低 2,485、收 2,510 元；20,666,092 股、51,702,445,610 元、57,634 筆 | 預計直接使用 TWSE／TPEx 官方未還原日行情；還原日價暫定直接使用 Fugle 歷史行情 API `adjusted=true`；週、月 K 由對應日資料彙整 | **尚未實作：目前仍使用 yfinance。** 官方最新日可整批取 OpenAPI，歷史按日期查官方網站行情；上櫃選含等價、零股、盤後及鉅額交易的行情。成交股數、金額與筆數採官方實際值；週月開盤取首個有價日、最高最低取期間極值、收盤取最後有價日，量值及筆數加總；未還原和還原分別彙整。**Fugle 非官方，還原價可能有誤、未全面驗證；用於指標、策略或其他運算時須特別留意資料品質。**富果表示會還原現金及股票股利、減資、面額變更、ETF 分割與反分割，不還原現金增資；價格至小數第 2 位。僅抽查 3680（2026-11-11，除息前）、5529（2026-05-27，除權前）、8093（2025-12-30，減資前）、6830（2026-09-15，現增前），不代表其他股票、日期或事件皆正確。尚未找到已確認完整的官方還原 K 成品，事件資料及還原口徑仍待核對。Fugle 歷史行情每分鐘 60 次，日 K 與 S03 分 K 須共用額度，單股每次區間小於一年；既有比對工具的限速不保護所有請求，server 須集中限速與共用快取，事件後須更新受影響的歷史還原價。TWSE 每 5 秒最多 3 次為本專案要求，非宣稱官方統一規定。跨上市櫃歷史拼接、無 OHLC 但有成交量、歷史缺漏、盤後更新時點、資料使用授權均待核實。 |
| 上市櫃歷史分鐘 K（S03，暫定使用富果 Fugle） | `2330`，2026-05-18 13:30 收 2,240 元、4,606 張 | 富果歷史行情 API；其日內行情與歷史分鐘 K 是不同 API | **暫定使用富果；正式程式尚未修改，目前仍使用 yfinance。** 富果歷史分鐘資料自 2023-05-23 起，單次查詢區間須小於一年；盤後 16:30 前更新；支援 1／3／5／10／15／30／60 分。上市櫃整股成交量以張計，不含零股、盤後等交易，不能直接和日 K 的股數比較；無成交的分鐘不產生 K 棒，缺棒不能一概視為資料缺失或補零，暫緩收盤等例外仍待更多驗證。富果稱即時行情上游為 TWSE／TPEx；歷史分鐘 K 的具體上游與處理方式未明。**重要時間疑點：櫃買中心 2026-11-12 暫緩收盤名單含 `2734`、`2941`，規則暫緩至 13:33；富果兩檔歷史 1 分 K 最後棒均標 13:30，收盤各為 14、25.7 元，與官方日收盤一致。富果是否刻意標準化時間或標記錯誤未知。精確成交時間運算不可直接採用富果棒時間，須另找獨立逐筆資料；資料可能有誤，用於指標或策略運算須留意。** 抽樣範圍有限：`2330`（2026-05-18、06-01、11-10）、`2317`、`0050`（11-10）共 270 根 5 分 K，以富果同源 1 分彙整，OHLCV 全同，只證明同源內部一致。另 `6488`（2026-11-12）54 根 5 分 K 與同源 1 分彙整一致。少量獨立抽樣為永豐 Shioaji `2330`（2026-05-18）09:01–09:03 右端時間棒對應富果 09:00–09:02 左端時間棒，OHLCV 相同；收盤棒亦核對一致，非逐分鐘或全面驗證。`2734`、`2941` 暫緩收盤案例僅兩檔、一天，仍待擴大驗證；不可稱資料已獨立驗證或全部正確。富果歷史行情 API 上限 60 次／分鐘，與 S02 富果還原日 K 共用規劃額度；日內 API 上限依方案，且須另行限速。現有分鐘比對工具的 2 秒間隔只保護該工具請求，不涵蓋其他歷史或日內請求；server 應集中限速及共用快取。FinMind `TaiwanStockKBar` 為候選：官網稱資料自 2018-12-07 起、Sponsor 付費、單次一檔股票一天；已知歷史缺漏，並稱暫緩收盤保留 13:33，本次未實測。TWSE／TPEx OpenAPI 及已安裝 `twstock` 調查未找到現成歷史分鐘 K，這不表示官方沒有逐筆歷史資料。公開網站使用權限待核實。 |
| 當日參考價、漲停價、跌停價（S04） | 2330，2026-11-12：參考價 2,395、漲停 2,630、跌停 2,160 元 | 預計使用 Fugle 日內個股資料 API | 尚未實作，目前仍用 Yahoo 前收盤估算漲跌停。須核驗回應日期；3680 除息日 2026-11-12 Fugle previousClose 為 425.5，但前日未還原收盤為 435.5，不可直接視為未還原前收；前日實際收盤預計由 S02 twstock 未還原日 K 取得。無漲跌幅限制的表示方式及特殊情況尚待核對；00646 曾回傳漲停 9999.95、跌停 0.01，不可直接視為一般實際漲跌停。日內 API 上限 60 次／分鐘；既有分鐘 K 比對工具限速不涵蓋此 API，server 須另行控速。twstock 原始行情 u/w 對特殊案例可靠性尚未確認。 |
| 個股本益比、股價淨值比、殖利率（S05） | 2026-11-12：2330 分別為 27.12、9.43、0.94%；6488 為 35.02、2.25、1.24% | 暫定上市用 TWSE OpenAPI `exchangeReport/BWIBBU_ALL`，上櫃用 TPEx OpenAPI `tpex_mainboard_peratio_analysis`，均可整批取得 | **尚未實作**：現行 `/profile` 仍使用 Yahoo `trailingPE`、`priceToBook`、`dividendYield`，每檔快取 1800 秒；PE、PB 到小數 2 位，PE 的 UI 顯示 1 位，PB 零轉 null；殖利率到 2 位直接加 `%`，零保留，Yahoo 回傳是百分數還是小數尚未確認，不能認定有 100 倍錯誤。Yahoo 所用 EPS、淨值期間及負 EPS 處理待查。2026-11-13 實查兩市場 API 最新日期均為 2026-11-12，上列僅兩檔抽樣，不代表全部股票或日期正確。指標應標示行情日期與採用財報季度；財報季度可能較舊，實際計算口徑及異常值仍須核對。server 應分市場整批更新並供多使用者共用快取，保留來源日期；TWSE 每 5 秒最多 3 次是本專案要求，非官方統一限制。twstock 套件本身提供這三項指標尚未證實。 |
| 公司發行股數及實收資本額（S05） | 上櫃 6488：2026-11-12 發行股數 528,113,725 股，實收資本額 5,281,137,250 元 | TWSE／TPEx OpenAPI 公司基本資料為候選 | 上市公司基本資料已取得股數及實收資本額；2026-11-13 實查 TPEx `mopsfin_t187ap03_O` 回傳 897 筆，6488 的 `IssueShares` 與 `Paidin.Capital.NTDollars` 如例，資料日期為 2026-11-12。僅確認欄位可取得，發行股數、流通股數、私募股及特別股的關係和更新時點待核對，尚未決定市值算法。現行 Yahoo `sharesOutstanding` 顯示為「股本」，股數與股本金額不同，名稱及來源口徑待修正。市值、近 12 個月 EPS、52 週高低、分析師目標價及人數的來源與計算口徑仍待確認；現行仍使用 Yahoo。 |
| 市值、股數、近 12 個月 EPS、52 週高低、分析師目標價與人數（S05） | 目前按個股 `/profile` 顯示 | 現行 Yahoo `.info`；替代來源尚未確認 | [stock.py:329](../backend/data_service/sources/stock.py#L329)；僅接受有限 int/float，先到小數 2 位；多數零轉 null，EPS、殖利率及分析師人數零保留，快取 1800 秒，未提供來源資料日期。`marketCap` 除以 1 億後到 1 位顯示億元，幣別及股價時間待核對；`sharesOutstanding` 除以 1 億後到 2 位顯示億股，發行／流通股數口徑待核對，介面「股本」名稱不精確。`trailingEps` 到 2 位且保留負值，與單季 EPS 的基本／稀釋與股數調整關係待查；`fiftyTwoWeekHigh/Low` 到 2 位，是否還原與幣別待查；`targetMeanPrice` 到 2 位，預測期間、幣別、樣本及更新日待查；`numberOfAnalystOpinions` 到 2 位，是否對應相同目標價樣本待查。上述欄位替代來源與計算方式尚未決定。 |
| 即時五檔委買、委賣價格與數量（S06） | 2026-11-13 盤中 twstock：2330 買一 2365、量 206，賣一 2370、量 293；6488 買一 635、量 12，賣一 637、量 12 | 暫定繼續使用 twstock `realtime.get`；套件向證交所基本市況網站 MIS 取得上市及上櫃行情；Fugle 日內報價 API 為備選 | 現行 `/orderbook` 已使用 twstock，價量陣列配對，`-` 略過，價至小數 2 位、量轉整數；程序內記憶體快取 30 秒，多程序不共用。2026-11-13 上述兩檔抽樣成功，稍後 Fugle 最佳買賣價相同、數量不同；時間不同不能判斷錯誤，非逐筆或全面驗證。twstock 提供來源時間但目前輸出未保留，須標示報價時間與取得時間；試撮、暫停交易、盤前盤後、數量單位、缺檔及市價委託表示尚待核對。TWSE／TPEx OpenAPI 目錄本次未找到現成盤中五檔端點，不代表官方沒有其他介面。MIS 為行情快照，程式快取使資料可能更舊；不保證逐筆即時。twstock 查詢先連網站再取行情且可能重試，server 須跨使用者集中限速、共用快取；TWSE 每 5 秒最多 3 次為本專案要求，非官方統一限制。Fugle 有時間與試撮等狀態，但日內 API 須另行控速；兩來源網站對外展示與轉用權限待核實。 |
| 個股與加權指數當日分時（S07） | 2026-11-13 盤中 Fugle 個股 `2330`、`6488` 及加權指數 `IX0001` 日內 1 分 K 均有回應 | 個股暫定 Fugle 日內 1 分 K；加權指數盤中暫定 Fugle，盤後優先 TWSE `exchangeReport/MI_5MINS_INDEX` 每 5 秒資料彙整 | **尚未實作**：目前 Yahoo 1 分 K 的收盤、成交量作分時線；前收取分時交易日前最後日收。現行橘線以每分鐘收盤×成交量求加權平均，僅為估算，非逐筆成交均價；無量時用當前收盤價，指數不應將其當股票均價。Fugle 個股 `average` 作累計均價候選：2026-11-13 `2330`、`6488` 盤中抽樣與同源 quote 的 `avgPrice` 及累計成交金額÷成交股數四捨五入一致，非獨立逐筆驗證；上市櫃整股 volume 為張、指數 volume 為成交金額，指數無 average。TWSE 2026-11-12 官方 5 秒指數按分鐘彙整與 Fugle 同日歷史 1 分指數比較，271 根中 270 根 OHLC 一致；09:00 官方開盤 44257.15、Fugle 44180.46，其餘高低收一致，原因待查；僅一天抽樣、不代表全面正確。2026-11-13 盤中查 TWSE 當日統計尚無資料，不能假設該端點提供盤中資料。S03 已知 2026-11-12 暫緩收盤 `2734`、`2941` 的 Fugle 歷史最後棒標 13:30；日內 API 當時回應未核實，不能推定相同，精確時間運算仍需獨立驗證。前一交易日實收與當日參考價於除權息日可能不同，平盤線口徑待確認；Fugle 日內及歷史 API 分別限速，server 須集中限速、共用快取及保留來源時間。資料授權及多市場盤中缺棒狀況待核對。 |
| 加權指數、櫃買指數點位與漲跌（S08） | 2026-11-13 MIS 加權及櫃買前收 43,091.87、335.73 點 | 盤中暫定證交所 MIS 同批取得 `tse_t00.tw`、`otc_o00.tw`；盤後加權採 TWSE `exchangeReport/MI_5MINS_INDEX` 最後一筆，櫃買採 TPEx OpenAPI `tpex_index`；Fugle `IX0001`、`IX0043` 為備援候選 | **尚未實作**：現行 Yahoo `^TWII`／`^TWOII` 取最近兩根日線，漲跌＝最新−前收、漲幅＝漲跌÷前收×100，兩位小數、30 秒程序內快取；資料不足 2 根回 null，註解稱櫃買固定 null 與實際仍嘗試查詢不符，缺少來源報價日期且未防前收為零。2026-11-13 盤中 MIS 同時取得兩項指數及前收，前收與 2026-11-12 TWSE 官方 5 秒表最後一筆及 TPEx `tpex_index` 收盤分別一致，Fugle 兩項 `previousClose` 亦相同；僅兩指數一天抽樣，盤中點位未同步逐筆核對。MIS 無防快取參數時曾回較舊時間，須檢查來源日期／時間、請求快取與失敗顯示，非以擷取時間冒充報價時間。TWSE 5 秒統計在 2026-11-13 盤中查當日未取得資料，不可假設盤中可用。指數開盤、收盤、休市、資料延遲、MIS 介面穩定性及對外展示授權待確認；應依交易日區分盤中與盤後資料，多用戶共用快取並集中限速。TWSE 每 5 秒最多 3 次是專案要求，非宣稱官方統一限制；Fugle 日內 API 另行限速。 |
| 國際指數點位及漲跌幅（S09） | 2026-11-12 上證收盤 3,655.83 點，Yahoo 與上海證交所一致 | 暫定沿用 Yahoo／yfinance：道瓊 `^DJI`、那斯達克綜合 `^IXIC`、日經 225 `^N225`、上證 `000001.SS` | 現行取最近兩根日 K 收盤計算 `(最新−前收)÷前收×100`，取到 2 位，缺少兩根時省略；30 秒程序內快取不代表來源每 30 秒更新或即時，分母零及單一請求例外中止整組待修正。2026-11-13 四個 Yahoo 代碼均取得資料；上證僅以 2026-11-12 一日官方收盤抽樣一致，道瓊、那斯達克、日經尚未獨立比較。各市場時區和交易日不同，須逐項顯示來源日期、時間、盤中／收盤及延遲狀態，缺失不猜測，server 共用快取並顯示失敗或過舊。yfinance 文件稱 Yahoo Finance API 資料供個人使用，對外網站展示授權及穩定性未確認；S&P DJI、Nasdaq、Nikkei、上海證交所官方來源及授權條件待逐一核對。 |
| 綜合損益表（S10） | 2026 前三季：1101 營收 112,522,875,000 元、稅後淨利 7,921,300,000 元；6488 分別為 44,069,861,000 元、7,179,871,000 元 | 暫定繼續用 FinMind `TaiwanStockFinancialStatements` 取得歷史單季資料；TWSE `opendata/t187ap06_L_ci`、TPEx `mopsfin_t187ap06_O_ci` 等依市場及產業的官方整批資料核對最新累計 | 現行 [fundamental.py](../backend/data_service/sources/fundamental.py#L27) 每次按股票及日期區間查詢，使用 EPS、IncomeAfterTaxes、Revenue、GrossProfit；驗證日期與有限值、依日期排序，程序內快取 1800 秒，僅部分公司有公告追蹤。2026-11-13 抽查上市一般業 1101、上櫃一般業 6488：官方 2026 Q3 累計營收、稅後淨利以千元換元後，均與 FinMind Q1＋Q2＋Q3 相同；官方累計基本 EPS 分別 0.63、15.00 元，亦與兩檔 FinMind 三季 EPS 相加相同。**僅兩公司、一期、所列科目抽樣，不代表其他股票、期間或科目正確。** FinMind 說明金額為新台幣元、一般為單季，EPS 為每股元；半年報公司與金融業科目另有差異。配股或股票分割可能使各季 EPS 股數基準不同，不能保證跨季直接相加；基本／稀釋 EPS、合併／個別報表及財報修正口徑須核對。該次官方兩端回應分別 752、442 筆，均為 2026 Q3；兩端點規格無指定年份、季度參數，不代表官方沒有其他歷史資料。MOPS 可查歷史財報，其程式取得方式、批次量與穩定性待查；2330 當次 FinMind 僅至 Q2，官方該批亦未找到，不可推論尚未公告或永久缺資料。須保存財報期間、取得時間及公告日證據，季末不是公告日；資料不足或來源差異保留未知，server 共用快取並處理 FinMind 額度、更新落後及修訂。TWSE 每 5 秒最多 3 次為專案要求。 |


| 範圍 | 審查內容及界線 |
|---|---|
| `backend/data/`、`data_service/` | 股票清單、六個來源模組、TTL、SQLite 與人工參考 JSON；全外部抓取入口均列於下表 |
| `backend/indicators/`、`screening/`、`api/` | 所有現有指標、品質判斷、技術／基本面條件及官方批次查核；未實作的回測／投組不當成現有功能 |
| `frontend/src/` | 全部 API 路由來源、資料合約、圖表／速查／自選股與示範資料；UI 包裝元件另查使用關係 |
| 根目錄、`scripts/`、`.github/`、`docs/` | 依賴、Docker／部署、檢查腳本、既有公式與計畫文件交叉核對；測試唯讀作為預期行為證據 |
| `.agents/skills/` | 視為工具本體，未審查其第三方實作、未刪除；不把技能示例當專案產物 |




| ID／來源 | 抓取程式位置／入口 | 原始欄位與輸出 | 後續轉換、運算 | 使用位置 | 待核實事項 |
|---|---|---|---|---|---|
| S11 FinMind 資產負債表 | 同上；`dataset=balance_sheet` | `TaiwanStockBalanceSheet`；stock_id/date/type/value；用 Equity、TotalAssets、CurrentAssets、CurrentLiabilities；查核另用 LongtermBorrowings、BondsPayable | 期末存量；ROE 平均期初期末 Equity；F-score 用資產／流動項；官方查核精確等值比較 | F02/F04、`audit_financials.py:18` | 合併權益與合併淨利須一致；長債科目不可擅自把缺值當零；FinMind 比對未含租賃 |
| S12 FinMind 現金流量表 | 同上；`dataset=cash_flow` | `TaiwanStockCashFlowsStatement`；stock_id/date/type/value；用 CashFlowsFromOperatingActivities | 品質標示 YTD；F-score **只取 12/31 全年 CFO**，沒有將中期 YTD 加總 | F04、品質 CLI | 非曆年制不支援；資本支出／FCF 尚未運算；不得把中期 CFO 當單季 |
| S13 FinMind 月營收 | 同上；`dataset=monthly_revenue` | `TaiwanStockMonthRevenue`；stock_id/date/revenue_year/revenue_month/revenue，保留 create_time 等 | 所屬月依 year/month；以 date 查詢篩選；YoY 比去年同月；前端 revenue/1e8→億元 | F03、近六個月營收表 | date 不是所屬月，create_time 不是正式公告日；去年同月缺／零不可算；來源金額是否元須逐筆核對 |
| S14 FinMind 股利 | 同上；`dataset=dividends` | `TaiwanStockDividend`；stock_id/date 與其餘上游股利欄位原樣；程式沒有固定完整欄位清單 | 只驗證股票/date、可序列化 JSON；不做逐一股利欄位型別檢查或殖利率計算 | 中台 raw endpoint、check_fundamentals 的品質摘要；**不供 profile 殖利率卡片** | 須實際保存 payload 列出每股現金／股票股利、除權息日與付款日欄位及單位；不把政策紀錄當已領股息 |
| S15 MOPS 官方年度合併 iXBRL | [official.py:217](../backend/data_service/sources/official.py#L217)；`/official-financials?year=...` | `https://mopsov.twse.com.tw/server-java/t164sb01`，step=1/CO_ID/SYEAR/SSEASON=4/REPORT_ID=C；原始 bytes、SHA、contexts、units、facts | 原件最多 10 MB；SQLite 以 ticker/year/SHA 保存內容版本，有效文件 86400 秒快取；每次重新解析；見 F05 | 官方批次查核 CLI；沒有自動回填補充 JSON 或 F-score | 僅指定 taxonomy、TWD、合併 scope；缺標籤非零、未見發行列非未發行；同 SHA 再抓更新 fetched_at，並非每次抓取的完整事件紀錄 |
| S16 台積電近期公告 | [announcements.py:13](../backend/data_service/sources/announcements.py#L13)、`:58`、`:249` | `https://pr.tsmc.com/english/latest-news` 及 `/english/news/數字`；title/published_on/period/source_url/source_kind/fetched_at | 月報標題辨識年月；季業績摘要讀正文確認 Issued on 與季度；不抽取財報金額 | S10/S13 附 announcement_tracking → assess_fundamentals | 只近期頁，最多兩季／四月；業績摘要不是完整核閱財報；HTML 格式變更可能使辨識失效 |
| S17 友達近期公告 | [announcements.py:16](../backend/data_service/sources/announcements.py#L16)、`:124`、`:194` | `https://www.auo.com/en-global/New_Archive/index`；限定 FinanceReport/news_IR 日期網址 | 清單日期＋標題判期間，檢查網址日期一致；不取金額 | 同 S16，2409 | 沒逐篇正文核對；清單不保證每月連續或歷史完整 |
| S18 環球晶近期公告 | [announcements.py:18](../backend/data_service/sources/announcements.py#L18)、`:231` | `https://www.sas-globalwafers.com/en/category/news_en/` 及 gwc_news_en_日期 | 合併同文章日期／標題 anchor，再正文確認 GWC 6488 與同句季度；不把 SAS 5483 當 GWC | 同 S16，6488 | 來源只首頁；聯合月報標題不等同已核對營收金額；句型改變需調整解析 |
| S19 群創近期公告 | [announcements.py:20](../backend/data_service/sources/announcements.py#L20)、`:167` | `https://www.innolux.com/api/news/GetNewsList?lang=EN&pageIndex=0&dept=ir&year=`；list.id/title/news_date | 正整數 id 組文章網址；標題辨識所屬月／季度，news_date 為公告日；不取金額 | 同 S16，3481 | 只第一頁，year 空白採來源預設；沒有翻頁／歷年保證 |
| S20 人工公告與科目參考 | [fundamental_references.json](../backend/data/fundamental_references.json)、[fundamental_quality.py:113](../backend/screening/fundamental_quality.py#L113) | 2330 Q3 公告 SEC 公司文件、Q2 官方核閱財報／簡明報表；6488 官方年度／前三季／Q2 PDF；ticker/dataset/period/field/reference_value/precision/basis/unit/URL | 只作 freshness 與 ROUND_HALF_UP 精度比較，不覆寫 FinMind；6488 Q4 EPS 參考 15.29−10.68=4.61 | 品質檢查 checks、依賴科目阻擋 | JSON 內均有實際 URL；本次未重抓 PDF；EPS 差額法跨期股數與 4.60 簡報差異待查；總 reviewed_on 早於部分逐項 reviewed_on，應逐項看 |
| S21 人工 F-score 補充 | [fundamental_supplements.json](../backend/data/fundamental_supplements.json)、[fundamental.py:170](../backend/screening/fundamental.py#L170) | 2330 MOPS、6488 公司 PDF、2409 AUO 4Q2025_TC.pdf、3481 114Q4 公司 PDF；各 2025/2024 年，三類非流動債額、equity_issued、頁碼／文字證據、部分 SHA | 依 ticker/year 唯一對應；長債三項相加；只接受明確布林發行事實，缺欄維持未知 | F04；前端顯示 current supplement 的來源連結與日期 | 不是自動抓取，不能推廣到未核對年度／股票；2330/6488 記錄未全附 SHA，須拿原件再核；2024 某些發行欄留空是刻意缺資料 |


| ID／輸出 | 程式位置 | 後續公式或處理 | 使用位置 | 待核實／限制 |
|---|---|---|---|---|
| C01 日週月庫存 | [stock.py:158](../backend/data_service/sources/stock.py#L158)、`:204`；[store.py:54](../backend/data_service/store.py#L54) | period→台北零時切點；週線含當週週一，月線非 1 日取下月 1 日；SQLite key=(完整 symbol,interval,ts)，增量倒數 5 根重疊、upsert | S02；跨重啟保存 | 只用首末日期判覆蓋，未驗證區間中缺棒；source_start 由最早回傳／容許落差 7/14/45 日推定，暫時截斷可能被當無更早資料 |
| C02 還原價檢查 | [stock.py:243](../backend/data_service/sources/stock.py#L243)、[store.py:120](../backend/data_service/store.py#L120) | 任一重疊 abs(newClose/oldClose−1)>0.001 且 old≠0 → pending，整段重抓；首尾覆蓋才清 pending；失敗 stale_adjust=true | get_stock_data:70 阻擋、Next 回 503；技術篩選亦阻擋 | 非完整公司行動辨識；當日未收棒變動也可能觸發；低於 0.1% 修訂／區間內缺棒／不同 period 並行一致性仍待驗證 |
| C03 漲跌停估價 | [stock.py:54](../backend/data_service/sources/stock.py#L54)、`:70` | up=floor((prev×1.1)/tick(up))×tick；down=ceil((prev×0.9)/tick(down))×tick，Decimal；tick 價格界線 10/50/100/500/1000，單位 .01/.05/.1/.5/1/5 | candles.limit_up/down、個股速查 | 只是估算，見 R07；不可視為官方交易參考價 |
| C04 現價／漲跌幅 | [get_stock_data.py:91](../backend/api/get_stock_data.py#L91) | price=Ct；change=Ct−C(t−1)；pct=change/C(t−1)×100；一根時前值用自己，分母零回 0 | 個股標題／速查、自選股，顏色依 change 正負 | 週月／分鐘是相鄰該週期差，非一律昨收，見 R03 |
| C05 SMA／EMA | [trend.py:6](../backend/indicators/trend.py#L6)、[indicators/__init__.py:35](../backend/indicators/__init__.py#L35) | SMA(n)=最近 n 個 C 平均，n=20/60；EMA(n)t=αCt+(1−α)EMA(t−1)，α=2/(n+1)，首價為種子 | KlineChart、速查、SMA 訊號；EMA 用於 MACD | SMA 需滿窗；所有參數以棒計；EMA 起點隨顯示期間重設 |
| C06 MACD | [trend.py:14](../backend/indicators/trend.py#L14) | DIF=EMA12−EMA26；signal=EMA9(DIF)；hist=DIF−signal（**不乘 2**） | 三序列副圖、線位置訊號、技術條件 | 與不同種子／倍數的券商可能不一致；latest.macd_crossover 僅比較大小，不是事件 |
| C07 RSI14 | [momentum.py:6](../backend/indicators/momentum.py#L6) | ΔC；gain=max(Δ,0)，loss=max(−Δ,0)；首 14 個差值平均作種子；avg_t=(13×avg前+本次)/14；RSI=100−100/(1+avgGain/avgLoss) | 副圖、速查、訊號、技術條件 | 需 15 根；只有上漲時100，兩者同為零時 0/0→NaN；API 相容 latest.rsi 無值填50，但頁面用序列缺值 |
| C08 KD(9,3,3) | [momentum.py:33](../backend/indicators/momentum.py#L33) | RSV=(C−min9 L)/(max9 H−min9 L)×100；區間高低相等用50；K=2/3 K前+1/3 RSV，D=2/3 D前+1/3 K；初值50 | KD 副圖、速查、技術條件 | 前8根 NaN；不是 TA-Lib STOCH 的簡單平滑；種子與顯示期間有關 |
| C09 ATR14 | [volatility.py:6](../backend/indicators/volatility.py#L6) | TR=max(H−L,abs(H−C前),abs(L−C前))；第一根TR=H−L但不放種子；第1..14根TR平均作種子，之後 (13×ATR前+TR)/14 | ATR 副圖、速查 | 需15根，單位同價格；未拿來實算進場／停損 |
| C10 均量／量比 | [volume.py:6](../backend/indicators/volume.py#L6) | SMA5/10(V)含本棒；ratio=Vt/mean(V(t−5)..V(t−1))；短資料退全段均值，零量均值回1 | 均量副圖／速查；量比 API、訊號、技術篩選 | 頁面額外要求至少6根且前5均量>0，否則顯示—；技術篩選拒絕零基準；不能把 API 的中性填值當真量比 |
| C11 K線型態 | [pattern.py:21](../backend/indicators/pattern.py#L21)、`:30` | TA-Lib CDLMORNINGSTAR/CDLEVENINGSTAR/CDLHAMMER/CDLHANGINGMAN/CDLENGULFING；依旗號正負→多空，預設只取最近5棒、按時間排序 | 側邊訊號、技術篩選當根偏多加分 | TA-Lib 預設門檻／penetration；不是每根都回型態，也不是統計勝率 |
| C12 分時／指數／五檔呈現 | S06–S09；[order-book.tsx:40](../frontend/src/components/stock/order-book.tsx#L40)、[watchlist-view.tsx:21](../frontend/src/components/watchlist-view.tsx#L21) | 五檔條寬=round(volume/max(1,全部檔量)×100)；Sparkline 對全部價格含平盤做 min/max 正規化；分時價色依 last≥prev | 個股／市場／自選股圖表 | 五檔量與股數單位不同不可混算；分時均價及假 UTC 見 S07；K線高低箭頭使用整個傳入資料區間，不是目前縮放視窗 |
| C13 速查判讀 | [indicator-summary.ts:9](../frontend/src/lib/indicator-summary.ts#L9)、`:49` | 只取與最後 candle 同時間的有限數值；SMA 比較收盤位置，MACD比較兩線；RSI>70/<30提示，量比>=1.5/<0.7提示；型態最近5根 | 個股速查及側邊訊號 | 描述不是事件／買賣點；提示量比>=1.5與技術門檻>1.5刻意不同，邊界需依用途閱讀 |

| 技術規則 | 明確公式／門檻（technical.py 行號） | 分數與使用 |
|---|---|---|
| 趨勢 | `Ct>SMA20t>SMA60t`（94） | 通過30分，必須通過 |
| MACD | `DIFt>0` **或** `DIF前<=signal前 且 DIFt>signalt`（67、101） | 通過25分，必須通過 |
| 動能 | `40<=RSI<=70` **或** `K前<=D前 且 Kt>Dt 且 Kt<80`（68、112） | 通過25分，必須通過 |
| 量能 | `Vt/前5根均量>1.5`（124） | 通過15分，必須通過 |
| 當根型態 | 當根存在任一 bullish 型態（74、131） | 加5分，可不通過；不補足前四規則 |
| 合計 | score=五項得分相加；passed=前四項全真（138） | 僅 CLI／Python；**沒有接到 `/api/screening` 示範總分**，非勝率 |

| ID／項目 | 來源欄位／位置 | 轉換及公式 | 使用位置 | 待核實事項 |
|---|---|---|---|---|
| F01 四季 EPS | S10.EPS；[screening/fundamental.py:115](../backend/screening/fundamental.py#L115) | 最新損益表期末往回4個連續季度；逐季 EPS>0，**不加總 EPS、不推導 Q4** | 基本面 EPS 卡片、研究條件 | 跨季基本／稀釋 EPS 與股數基準；與 S05 近12個月 EPS 不同 |
| F02 TTM ROE | S10.IncomeAfterTaxes、S11.Equity；[screening/fundamental.py:120](../backend/screening/fundamental.py#L120) | 四個單季合併淨利加總 / ((最早季前一期 Equity+末期 Equity)/2) ×100；門檻>12% | ROE卡片、研究條件 | 合併淨利／合併權益，不是歸母口徑；各期來源完整度；期初期末權益均須正 |
| F03 月營收 YoY | S13；[screening/fundamental.py:131](../backend/screening/fundamental.py#L131)、`:196` | (當月revenue/去年同月revenue−1)×100；最新3個連續所屬月都>0%；另輸出最新6個日曆月含缺值 | 成長研究條件、六個月表；顯示億元=元/1e8 | 去年同期必須>0、當期不得負；不是3月加總YoY，非來源內建成長率 |
| F04 年度 F-score 輸入 | S10/S11/S12/S21；[screening/fundamental.py:143](../backend/screening/fundamental.py#L143) | 以最新損益期末決定最近完整年度，非12月則往前1年；本年與前年度損益各加4個單季，CFO取各年度12/31；資產需再前一期；長債=非流動公司債+借款+租賃 | 九項表、總分；完整分數>=6為研究門檻 | 產業含金融／保險／證券／金控時拒用F-score；補充只限指定股票年度，不從股本變化猜是否發行 |
| F05 官方金額／股權證據 | S15；[official.py:91](../backend/data_service/sources/official.py#L91)、`:108`、`:158` | 無維度期末 TWD 負債，value=Decimal(移除逗號文字)×10^scale，需整數；tag 為 LongtermBorrowings／NoncurrentPortionOfNoncurrentBondsIssued／NoncurrentFinanceLeaseLiabilities；普通股維度另允許負號 | 官方查核 raw records；保留本年／前年12/31負債、兩年普通股明細 | 驗證公司、年度、Consolidated report；僅支援兩種數字format；部分／歧義保持null，不等同全份財報正確 |
| F06 官方普通股變動 | [official.py:138](../backend/data_service/sources/official.py#L138) | opening Equity(1/1)+ChangesInEquity=closing Equity(12/31)；明確正 IssueOfShares 事件→equity_issued=true；缺事件不回false | audit 的 equity_evidence，不自動改 F-score | 淨變動零／勾稽相符均不能證明無發行；需完整普通股維度及公司附註 |
| F07 FinMind／官方比對 | [audit_financials.py:18](../backend/api/audit_financials.py#L18) | LongtermBorrowings↔noncurrent_borrowings、BondsPayable↔noncurrent_bonds；同股票／期末恰一筆且 `==` 才 matched；未比租賃 | 逐公司 JSONL、`.exceptions.json`；預設間隔6秒，429/503／路由過時停止並列remaining | 精確等值不接受精度差；只兩個科目，不是完整長債／整份財報認證；輸出用w會覆蓋同名檔，執行前須選好路徑 |
| F08 人工精度比對 | S20；[fundamental_quality.py:146](../backend/screening/fundamental_quality.py#L146) | round_half_up(來源值/precision) 與 reference_value/precision 等值；缺／重複／不符→問題 | quality.checks→依賴科目阻擋 | reference_value 須對齊precision；沒有自動審核新增人工參考的basis/unit，不能只核數字 |
| F09 新鮮度與阻擋 | [fundamental_quality.py:113](../backend/screening/fundamental_quality.py#L113)、[screening/fundamental.py:86](../backend/screening/fundamental.py#L86) | 只用 published_on<=查詢end的人工／自動公告；latest_period<公告period→pending_update；rule依 table/period/field 掛品質問題、清 condition_met | 品質CLI、基本面warning／verdict | at_least_announced/reviewed_period不是全市場最新保證；source_error只改can_screen的漏洞見R04；歷史修訂與公告可得時間未完整保存 |

| 訊號 ID | 實際公式／成立條件 | 欄位來源／待核實 |
|---|---|---|
| positive_roa | NIy/A0y>0 | S10＋S11；期初資產正 |
| positive_cfo | CFOy/A0y>0 | S12全年＋S11 |
| improving_roa | NIy/A0y>NIp/A0p | 兩年各自期初資產，不是平均資產ROA |
| cash_exceeds_profit | CFOy>NIy | 同年同合併口徑；不是中期累計比單季 |
| lower_leverage | Dy/((A0y+A1y)/2)<Dp/((A0p+A1p)/2) | S21長債＋S11平均資產 |
| improving_liquidity | CAy/CLy>CAp/CLp | CurrentAssets/CurrentLiabilities；CL正 |
| no_equity_issued | 本年 equity_issued 明確為 false | 只S21人工事實；unknown不是false |
| improving_margin | GPy/Ry>GPp/Rp | S10；營收分母正 |
| improving_turnover | Ry/A0y>Rp/A0p | S10＋S11；使用期初資產 |

| 資料／入口 | 欄位與運算 | 使用位置／程式證據 | 待核實／尚未存在 |
|---|---|---|---|
| `/api/market` | updated_at、business_cycle、usdtwd、us10y、institutional、breadth、turnover、environment；直接常數，沒有環境判斷公式 | mock-data:14；MarketOverview／MarketBanner | 國發會 data.gov.tw #6099、TWSE OpenAPI、市場籌碼未接；USD/TWD `USDTWD=X`、美債 `^TNX` 也未抓 |
| `/api/market/futures` | tx_price/tx_change/basis/foreign_oi 常數；basis雖註解期貨−現貨但沒有計算 | mock-data:26；FuturesCard | 期貨／未平倉來源未定；不可拿示範basis與真指數勾稽 |
| `/api/market/rankings` | sector_performance/volume_leaders/gainers/losers 常數，volume_leaders實為億元成交值 | mock-data:34；RankingsSection、StockHomeView | 沒有全市場掃描、類股加權與排名公式 |
| `/api/market/news`、`/api/stock/[ticker]/news` | time/title/source 常數，個股只插入name | mock-data:66、93；MarketNewsSection、NewsTab | 經濟日報／MoneyDJ等署名不是實際抓取；TWSE重大訊息RSS/feedparser尚未接，與S16–S19官方公告追蹤不同 |
| `/api/stock/[ticker]/chip` | institutional逐日外資／投信／自營、融資券餘額／增減、大戶比例常數，ticker被void忽略 | mock-data:74；ChipTab | FinMind InstitutionalInvestorsBuySell／MarginPurchaseShortSale／Shareholding僅規劃；不同股票目前同值 |
| `/api/screening` | rank/score/reasons/entry_low/high/stop_loss/pct/allocation_pct及配置常數；頁面僅排序、繪製圓餅／Progress | mock-data:102；screening-view:129；API route:1 | 沒有停損%、進場區間、多因子總分或投組優化公式；即使score92也不是technical-v1或F-score結果 |
| 計畫與研究依賴 | FRED DGS10／fredapi、pytrends、Telegram、APScheduler、Alphalens、回測／最佳化套件 | [plan.md:140](../plan.md#L140)、pyproject research group | 安裝或寫入藍圖不等於已串接；本次來源程式搜尋未見實作，不列為現有抓取來源 |

| ID／優先 | 證據位置、觸發條件 | 影響與最小處理方向 | 確定程度 |
|---|---|---|---|
| R01／P1 分時資料時間多加8小時 | intraday.py:30 將台北壁鐘當UTC；intraday-tab.tsx:39、market/intraday-section.tsx:36再 `new Date(epoch)`→utils.ts:21本地格式化 | 台北09:00的圖表點會在資料時間文字顯示17:00，圖軸仍09:00；應統一真實時刻與圖表格式化，或明訂顯示專用timestamp的解碼，勿直接本地化假UTC | **重現時間轉換**：Node固定Asia/Taipei測得17:00；未啟動瀏覽器 |
| R02／P1 分時平盤線無條件取倒數第二日 | intraday.py:17–18；若分鐘已有當日資料，但5d日線尚未帶當日棒，daily Close=[99,100] | 回prev_close=99而非最近已完成的100，影響平盤線、整段顏色、自選sparkline；不足2根又用今日首分鐘價冒充昨收。應依分鐘所屬交易日找前一交易日，不靠固定-2 | **重現既有函式**：假來源、真fetch_intraday，回99；來源何時發生此時序待實測 |
| R03／P2 現價旁漲跌基準不明 | get_stock_data.py:91–95；stock-analysis-view.tsx:361稱「現價／漲跌」，公式用所選K前一根 | 同股切5分／週／月，百分比變成5分／週／月差，未寫明基準，易誤當每日漲跌；應明示相鄰棒週期，或另設固定日報價 | **靜態確認**；不是宣稱相鄰棒差公式算錯 |
| R04／P2 公告抓取失敗未傳入規則阻擋 | fundamental_quality.py:122只設can_screen=false，status仍unverified；screening/fundamental.py:99只按status/checks處理 | EPS等仍可顯示「研究條件符合門檻」；前端quality型別不含公告失敗原因，容易遺漏新鮮度失查。須針對依賴傳遞公告source_error；整體passed仍null，**不是已驗證選股通過** | **重現既有評估器**：現有sample加source_error，can_screen=False但EPS condition_met=True/calculated_unverified |
| R05／P1 行情來源回空仍當更新成功 | stock.py:234–241在new_rows空時回SQLite，stale_adjust只反映還原pending；stock-analysis-view.tsx:111更新本機時間 | 上游中斷／截斷且無pending時，舊收盤仍成功回傳，沒有來源失敗／最後來源更新時間；可能繼續計算舊資料並顯示剛更新。應附實際as_of／抓取狀態，與取得時間分開 | **靜態確認**；不是每次空資料都必須失敗，非交易日回舊資料可能合理 |
| R06／P2 市場頁背景錯誤不提示 | market-overview-view.tsx:51–65，silent=true時catch不設error，保留indices | 自動刷新失敗可長期保留舊指數且無失敗提示；沒有指數as_of，頁首updated_at又是market mock常數。應保留舊值但顯示更新失敗及來源時間 | **靜態確認**；未做瀏覽器故障注入 |
| R07／P2 漲跌停只用歷史還原收盤估價 | stock.py:70、98，所有已知代碼含ETF均使用同一10%／股票tick模型，未取官方當日參考價 | 除權息、不同商品／交易狀態可能不適用；前端價位不可當可下單限價。至少標「估算」並限定適用種類，正式精準值須官方當日參考資料 | **已確認模型限制，實際偏差待核實**；不宣稱所有ETF必定錯 |
| R08／P3「股本」實為股數 | stock.py:343、351 使用sharesOutstanding/1e8；profile-tab.tsx:88標股本、單位億股 | 容易與資本額（元）混淆；最小修正為標示發行／流通股數並核對供應商定義，不能擅乘固定面額 | **靜態確認**單位／標籤差異 |
| R09／P2 顯示期間改變指標種子 | get_stock_data.py:76–89直接計算顯示範圍；trend.py:10、momentum.py:22、54 | 同截止日切1M/6M可能有不同EMA/RSI/KD，短區間SMA60消失；若需與券商／技術CLI逐點一致，應固定預熱資料後再裁顯示 | **靜態確認**設計行為；差值大小及應採哪個平台口徑待核實，不把已明訂種子說成公式錯 |
| R10／P2 長歷史JSON可能超子程序stdout上限 | run-python.ts:16的execFile未設maxBuffer；stock route.ts:12任意period可到max；get_stock_data輸出多組完整序列 | 足夠長日／分鐘歷史可能超Node預設buffer而只回500；需實際量測payload後決定裁切／上限或傳輸方式 | **待重現條件風險**，本次未下載max行情；不宣稱目前UI每次會失敗 |

| 排序／標籤 | 可刪／縮小的具體位置 | 證據、替代與影響 | 確定程度 |
|---|---|---|---|
| 1 `delete` | [ui/chart.tsx:273](../frontend/src/components/ui/chart.tsx#L273) 的ChartLegend／ChartLegendContent及exports | 全frontend/src只有定義／exports；screening-view只用ChartContainer/Tooltip/TooltipContent。可刪約56行的unused圖例段及exports；保留tooltip共用getPayloadConfigFromPayload | 靜態無呼叫；不刪整個chart或recharts，圓餅仍用 |
| 2 `delete` | [ui/progress.tsx:54](../frontend/src/components/ui/progress.tsx#L54) ProgressLabel/ProgressValue | 全src無外部引用；screening只用Progress，刪兩個未用wrapper約22行及exports即可；Track/Indicator仍被內部使用 | 靜態無呼叫 |
| 3 `delete` | [ui/toggle.tsx:30](../frontend/src/components/ui/toggle.tsx#L30) 的Toggle wrapper | ToggleGroup直接用Base UI Toggle，只引用此檔toggleVariants；可刪wrapper約14行及對應unused import/export，**保留variants** | 靜態無呼叫；不可整檔刪除 |
| 4 `delete` | [main.py:1](../main.py#L1) 的Hello from stock-analysis入口（6行） | Docker／dev／文件啟動均使用backend.data_service.main或Next；沒有專案功能呼叫。替代：無 | 靜態未見使用；手動跑根main的外部習慣未知 |
| 5 `shrink` | stock-analysis-view.tsx:57、watchlist-view.tsx:16的同形fmtChange | 完全相同的漲跌字串格式；若已因格式變更同時維護兩份，可放既有utils.ts。當下不需另建formatter服務 | 已確認重複；小函式共用收益低，非必改 |
| 6 `yagni` | pyproject.toml:18 research與:42 default-groups | research套件在目前backend／frontend來源沒有執行呼叫，多數是未來藍圖；本次uv run因research→backtesting→bokeh下載而先失敗。日常啟動可考慮明確選group，**不因未接功能就刪研究工具** | 靜態使用關係＋本次下載失敗；不知使用者repo外研究方式，未建議刪依賴 |
| 7 `shrink` | market.py:32註解、types.ts:51、data_service/README的otc「一律null」說明 | 執行碼仍_quote(^TWOII)。應只保留一個準確的來源狀態敘述，其餘引用；目前讀文件無法知道會實際發請求 | 靜態已確認文字與程式不符，來源當下是否失效未核 |
| 8 `shrink` | docs/ARCHITECTURE.md:3、:29及末段的Archify圖連結／產物說明 | 本次刪圖後會失效；文件還有現行架構說明，**保留整份**，於本報告列出殘留引用。依本次只新增盤點文件的範圍，未順手改舊文件 | 已確認；不是可確定由Archify生成的文件 |

| 刪除檔案（相對共同父目錄） | 明確歸屬證據 | 刪除前bytes |
|---|---|---:|
| candidate.json | schema_version=1、diagram_type=architecture；meta.title台股分析系統、repository.url=neilyonglu/tw-stock-quant，output指同目錄HTML，sources指向本專案程式 | 5700 |
| tw-stock-quant.html | delivery/finalize/browser-check三份收據的同一路徑、SHA及大小均指向此互動架構圖；實際檔案SHA與收據一致 | 822308 |
| tw-stock-quant.delivery.json | command=deliver/type=architecture，receiptId=`6a877081-c7e3-4d81-af3e-26277b870b2b`，明列candidate及HTML | 646 |
| tw-stock-quant.finalize.json | command=finalize，stages.command明列`.agents/skills/archify/bin/archify.mjs deliver architecture`與上述input/output及repo-root | 36193 |
| tw-stock-quant.finalize-summary.json | command=finalize，specification/artifact SHA，evidence明列finalize與browser-check收據 | 1627 |
| tw-stock-quant.browser-check.json | command=browser-check、evidenceKind=automated-browser、deliveryReceiptId與delivery一致，artifact SHA指同HTML | 22098 |

| 命令／方法 | 本次實際結果 | 可以證明／不能證明 |
|---|---|---|
| `uv run pytest` | **未進入測試**，exit1；uv預設cache下sdists-v9/.git存取被拒(os error5) | 不是測試失敗，也不是測試通過 |
| PowerShell設`$env:UV_CACHE_DIR=Join-Path (Get-Location) '.uv-cache'`後`uv run pytest` | **仍未進入測試**，exit1；建立.venv後，research/backtesting的bokeh==3.9.1輪子下載遭網路限制(os error10013) | 不改pyproject／測試、不降低原驗證標準；需可存取既有cache或依賴下載後重跑指定命令 |
| Node stdin離線時間斷言 | exit0：Date.UTC建立09:00，轉Asia/Taipei得17:00 | 證明R01數值轉換；沒有執行完整UI |
| `uv run --no-sync python -`離線分時假來源 | exit0：stdlib MagicMock替代yfinance history，執行真fetch_intraday，daily=[99,100]、當日分鐘101，斷言prev_close==99 | 證明R02的條件路徑；不聲稱實際Yahoo今日發生同狀態 |
| `uv run --no-sync python -`離線品質評估 | exit0：唯讀AST擷取現有test_fundamental_screening.sample；只繞過未安裝的指標套件初始化，執行真品質／基本面模組；加入公告source_error後EPS仍True，passed仍None | 證明R04；未安裝pandas/TA-Lib，沒有執行完整指標套件或pytest |
| 檔案／來源掃描、SHA核對、最終git差異 | 六個產物的身份先驗證才刪除；最終確認只有本文件及六項刪除屬worker差異 | 沒有stage、commit、push、改branch或git metadata；原有技能stage保留；獨立verifier仍須驗收 |
