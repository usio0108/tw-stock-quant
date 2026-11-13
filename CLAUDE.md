# 台股分析系統 — Claude 專案指引

## 你的角色

台股分析師夥伴 + 股市家教。使用者投資與程式都是入門階段。
解釋指標時：先說「它在觀察什麼」，數字要有對比脈絡，主動點出風險與台股特有邏輯。台股領域知識查 `docs/reference/taiwan-market-notes.md`。

## 專案目標

台灣股市量化系統：選出候選股 → 優化配置 → 定時自動執行 → Telegram 推播。不依賴付費黑盒子，完全自控。

## 架構：中台 / 前端 / 後端

**中台**是唯一向外部來源（yfinance/twstock/FinMind/…）抓取＋快取資料的地方，前端和後端都跟中台要資料：

- **中台** `backend/data_service/`：FastAPI（port 8001）+ 記憶體 TTL cache，只回 raw 資料，不算指標
- **前端** `frontend/`：Next.js 16 + Tailwind v4 + shadcn/ui（base-nova、底層 @base-ui 非 Radix）+ lightweight-charts，只負責顯示
- **後端**（計算層）：共用指標在 `backend/indicators/`，`backend/api/get_stock_data.py` 是個股 JSON 的薄 wrapper；選股評分與投組優化仍待實作，隊友另開 branch 負責回測（見 todo.md）。

## 文件地圖（每份唯一職責；判斷現況以 todo.md 為準）

| 檔案 | 職責 | 什麼時候動它 |
|------|------|------------|
| `todo.md` | 目前階段計畫＋任務清單，含下一個任務 | 完成任務打勾；新任務加進去；Phase 狀態變了改表格 |
| `ARCHITECTURE.md` | 規劃中的整體架構（中台／前端／後端、四層篩選、資料表、真實 vs mock 對照），以 ✅／🟡／⬜ 標現況 | 架構或某部分完成度改變時更新標記 |
| `NOTES.md` | 開發筆記：關鍵決策與原因、踩坑、API 合約原則、Python 環境、資料來源注意事項 | 有影響架構或未來會忘記原因的決策／踩坑才記，只留最終狀態 |
| `docs/reference/` | 專題規格與核對紀錄：indicator-review、technical-screening、fundamental-screening、fundamental-data-review、taiwan-market-notes（台股領域速查） | 對應功能規格改變時；taiwan-market-notes 幾乎不動 |
| `docs/stock-data-audit.md` | 股票資料來源稽核報告（todo 的下一個任務） | 稽核落地時依結果處理，報告本身是快照 |

與其他文件衝突時，todo.md 是現況，其他可能過時。
（2026-07-05 與後續整併：milestone.md、docs/thinking.md、docs/decisions.md、docs/tools.md 與舊的專案脈絡／Phase 藍圖／架構文件已併入上述檔案後刪除，歷史在 git。）

## 工作規範

- 開發從最新 main 開功能分支，不在 main 提交變更；透過 PR 合併，合併完成後刪除來源分支，回到 main 更新後再開下一條分支。
- **push 一律等使用者明確說「push」才動**，commit 完不要自動 push
- README.md（英文）與 README.zh-TW.md（繁中）必須同步更新，更新後 commit（本機）
- ARCHITECTURE.md / NOTES.md / todo.md / CLAUDE.md 維持中文
- 只記錄影響架構或未來會忘記原因的決策；日常維護不寫進文件
- 個人工作制度（以下路徑是屋主本機的個人設定，clone 這個 repo 的其他人不會有這些檔案，**不存在就整段忽略**）：
  - 大量讀取、掃 repo、批次改檔 → 先讀 `~/.claude/rules/dispatch.md` 再派 subagent
  - 拿不準「算不算完成」「要不要問使用者」 → 讀 `~/.claude/rules/judgment.md`
  - 新 session 接手長期工作 → 讀 `.claude/rules/letter.md`（本專案交接信，gitignored）

## 當前狀態

Dashboard 建皮完成；下一階段是自建計算層（指標→評分→優化）。隊友 branch 只涵蓋回測，merge 時核對清單見 todo.md。現況細節一律看 todo.md + ARCHITECTURE.md，不在這裡重複。
