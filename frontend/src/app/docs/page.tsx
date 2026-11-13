import type { Metadata } from "next"
import { DocsClient } from "./docs-client"

export const metadata: Metadata = {
  title: "資料參考書｜台股分析",
  description: "網站上每個數字、圖表與表格的來源、意義、更新頻率與注意事項",
}

export default function DocsPage() {
  return <DocsClient />
}
