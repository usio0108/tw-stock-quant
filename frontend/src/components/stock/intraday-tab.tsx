"use client"

import { useEffect, useState } from "react"
import { formatWallClockEpoch } from "@/lib/utils"
import { Skeleton } from "@/components/ui/skeleton"
import { IntradayChart } from "@/components/charts/intraday-chart"
import type { IntradaySeries } from "@/lib/types"

export function IntradayTab({ ticker, refreshKey }: { ticker: string; refreshKey: number }) {
  const [data, setData] = useState<IntradaySeries | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    setError(null)
    fetch(`/api/stock/${ticker}/intraday`, { signal: ctrl.signal })
      .then(async (res) => {
        const json = await res.json()
        if (!res.ok || json.error) throw new Error(json.error ?? "Unknown error")
        setData(json)
      })
      .catch((e: unknown) => {
        if (e instanceof Error && e.name === "AbortError") return
        setError(e instanceof Error ? e.message : "Failed to load data")
      })
    return () => ctrl.abort()
  }, [ticker, refreshKey])

  if (error) {
    return <div className="h-100 flex items-center justify-center text-muted-foreground">暫時無法載入分時走勢（非交易時段可能沒有今日資料）</div>
  }
  if (!data) {
    return <Skeleton className="h-100 w-full bg-zinc-900" />
  }

  const lastPoint = data.points.at(-1)
  return (
    <div className="space-y-1.5">
      <p className="text-xs text-muted-foreground">資料時間 {lastPoint ? formatWallClockEpoch(lastPoint.time) : "—"}</p>
      <IntradayChart data={data} />
      <p className="text-xs text-muted-foreground">橘線是累計成交均價；灰色虛線是平盤（前一交易日收盤價）參考線{data.prev_close == null && "；目前取不到前一交易日收盤，不畫平盤線"}</p>
    </div>
  )
}
