"use client"

import { useMemo, useState } from "react"
import { Search, TriangleAlert, X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { DATA_SECTIONS, STATUS_DESCRIPTIONS, type DataEntry, type DataStatus } from "@/lib/data-sources"
import { cn } from "@/lib/utils"

// 「示範資料」的配色沿用 MockBadge（琥珀色），其餘兩種與它區隔：真實＝綠、估算＝藍。
// 注意這裡的綠不是「跌」：這頁的顏色只代表資料可信度，不代表漲跌。
const STATUS_STYLE: Record<DataStatus, string> = {
  真實: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  估算: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  示範資料: "bg-amber-500/15 text-amber-400 border-amber-500/30",
}
const STATUSES = Object.keys(STATUS_STYLE) as DataStatus[]

function StatusBadge({ status }: { status: DataStatus }) {
  return (
    <Badge variant="outline" className={cn("shrink-0", STATUS_STYLE[status])}>
      {status}
    </Badge>
  )
}

function EntryCard({ entry }: { entry: DataEntry }) {
  return (
    <Card id={entry.id} className="scroll-mt-6 bg-zinc-900 border-zinc-800">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="min-w-0">
            <h3 className="text-base font-semibold text-white">{entry.name}</h3>
          </CardTitle>
          <StatusBadge status={entry.status} />
        </div>
        {entry.where && <p className="text-xs text-muted-foreground">出現位置：{entry.where}</p>}
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm leading-relaxed text-zinc-200">{entry.meaning}</p>
        <dl className="grid grid-cols-[4.5rem_1fr] gap-x-3 gap-y-1.5 text-xs leading-relaxed">
          <dt className="text-zinc-500">來源</dt>
          <dd className="min-w-0 break-words text-zinc-300">{entry.source}</dd>
          <dt className="text-zinc-500">單位</dt>
          <dd className="min-w-0 break-words text-zinc-300">{entry.unit}</dd>
          <dt className="text-zinc-500">更新與快取</dt>
          <dd className="min-w-0 break-words text-zinc-300">{entry.update}</dd>
        </dl>
        {entry.caveats.length > 0 && (
          <div className="rounded-md border border-amber-500/20 bg-amber-500/5 px-3 py-2">
            <p className="flex items-center gap-1.5 text-xs font-medium text-amber-300">
              <TriangleAlert size={13} aria-hidden="true" />
              注意事項
            </p>
            <ul className="mt-1.5 list-disc space-y-1 pl-4 text-xs leading-relaxed text-amber-100/70">
              {entry.caveats.map((caveat) => (
                <li key={caveat}>{caveat}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function matches(entry: DataEntry, terms: string[]) {
  const haystack = `${entry.name}\n${entry.meaning}\n${entry.source}`.toLowerCase()
  return terms.every((term) => haystack.includes(term))
}

export function DocsClient() {
  const [query, setQuery] = useState("")
  const terms = useMemo(() => query.toLowerCase().split(/\s+/).filter(Boolean), [query])

  const sections = useMemo(
    () =>
      DATA_SECTIONS.map((section) => ({
        ...section,
        entries: section.entries.filter((entry) => matches(entry, terms)),
      })).filter((section) => section.entries.length > 0),
    [terms],
  )

  const total = sections.reduce((sum, section) => sum + section.entries.length, 0)
  const statusCounts = STATUSES.map((status) => ({
    status,
    count: DATA_SECTIONS.flatMap((section) => section.entries).filter((entry) => entry.status === status).length,
  }))

  const tocLinks = (
    <ul className="space-y-0.5">
      {sections.map((section) => (
        <li key={section.id}>
          <a
            href={`#${section.id}`}
            className="flex min-h-11 items-center justify-between gap-2 rounded-md px-2.5 text-sm text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-white"
          >
            <span>{section.title}</span>
            <span className="text-xs tabular-nums text-zinc-500">{section.entries.length}</span>
          </a>
        </li>
      ))}
    </ul>
  )

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-6 sm:p-6">
      {/* 標題與簡介 */}
      <div>
        <h1 className="text-xl font-semibold text-white">資料參考書</h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-zinc-400">
          這一頁說明網站上每一個數字、圖表和表格：它在觀察什麼、資料從哪裡來、多久更新一次，以及有哪些容易誤解的地方。
          內容依目前程式的實際行為整理，並非規劃藍圖；不確定的地方會標示「待確認」。看到不熟的數字時，可以先在下方搜尋名稱。
        </p>
      </div>

      {/* 三種狀態標籤說明 */}
      <section aria-label="資料狀態標籤說明" className="grid gap-3 sm:grid-cols-3">
        {statusCounts.map(({ status, count }) => (
          <div key={status} className="rounded-md border border-zinc-800 bg-zinc-900 p-3">
            <div className="flex items-center gap-2">
              <StatusBadge status={status} />
              <span className="text-xs tabular-nums text-zinc-500">{count} 筆</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-zinc-400">{STATUS_DESCRIPTIONS[status]}</p>
          </div>
        ))}
      </section>

      {/* 搜尋 */}
      <div className="max-w-md">
        <label htmlFor="docs-search" className="mb-1.5 block text-xs text-muted-foreground">
          搜尋名稱、意義或來源（多個關鍵字用空白分開）
        </label>
        <div className="relative">
          <Search size={14} aria-hidden="true" className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
          <Input
            id="docs-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="例如：RSI、yfinance、示範資料"
            className="h-11 pl-9 pr-11"
          />
          {query && (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="清除搜尋"
              onClick={() => setQuery("")}
              className="absolute right-0.5 top-1/2 size-10 -translate-y-1/2 text-zinc-400"
            >
              <X size={14} />
            </Button>
          )}
        </div>
        <p role="status" className="mt-1.5 text-xs text-muted-foreground">
          {terms.length > 0 ? `找到 ${total} 筆` : `共 ${total} 筆`}
        </p>
      </div>

      <div className="gap-8 lg:grid lg:grid-cols-[13rem_minmax(0,1fr)]">
        {/* 目錄：手機收合成可展開的選單，桌機固定在左側 */}
        <aside className="mb-6 lg:mb-0">
          <nav aria-label="本頁目錄" className="lg:sticky lg:top-6">
            <details className="rounded-md border border-zinc-800 bg-zinc-900 lg:hidden">
              <summary className="flex min-h-11 cursor-pointer items-center px-3 text-sm text-zinc-200">目錄</summary>
              <div className="px-1 pb-2">{tocLinks}</div>
            </details>
            <div className="hidden lg:block">
              <p className="mb-2 px-2.5 text-xs text-muted-foreground">目錄</p>
              {tocLinks}
            </div>
          </nav>
        </aside>

        {/* 內容 */}
        <div className="min-w-0 space-y-10">
          {sections.length === 0 ? (
            <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-zinc-800 py-16 text-center">
              <p className="text-sm text-zinc-300">沒有符合「{query.trim()}」的項目</p>
              <Button variant="outline" size="sm" className="border-zinc-700" onClick={() => setQuery("")}>
                清除搜尋
              </Button>
            </div>
          ) : (
            sections.map((section) => (
              <section key={section.id} id={section.id} aria-labelledby={`${section.id}-heading`} className="scroll-mt-6 space-y-4">
                <div>
                  <h2 id={`${section.id}-heading`} className="text-lg font-semibold text-white">
                    {section.title}
                    <span className="ml-2 text-xs font-normal text-muted-foreground">{section.route}</span>
                  </h2>
                  <p className="mt-1 text-sm leading-relaxed text-zinc-400">{section.summary}</p>
                </div>
                <div className="grid gap-3 xl:grid-cols-2">
                  {section.entries.map((entry) => (
                    <EntryCard key={entry.id} entry={entry} />
                  ))}
                </div>
              </section>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
