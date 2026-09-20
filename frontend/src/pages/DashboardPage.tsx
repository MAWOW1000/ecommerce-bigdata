import { useEffect, useState } from "react"
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts"
import { Filter, TrendingDown } from "lucide-react"
import { api, type AnalyticsResult, type CatalogItem, type FunnelStep } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"

const STEP_LABEL: Record<string, string> = {
  product_view: "Xem sản phẩm",
  add_to_cart: "Thêm vào giỏ",
  checkout_start: "Bắt đầu thanh toán",
  purchase: "Mua hàng",
}

// Doi ten cot ky thuat cua CSDL sang nhan doc duoc tren giao dien
const COLUMN_LABEL: Record<string, string> = {
  thang: "Tháng", danhmuc: "Danh mục", sodon: "Số đơn", soluongban: "SL bán",
  doanhthu: "Doanh thu", productid: "Mã SP", productname: "Sản phẩm",
  categoryname: "Danh mục", shopname: "Gian hàng", customerid: "Mã KH",
  fullname: "Khách hàng", province: "Tỉnh/Thành", recency: "Recency (ngày)",
  frequency: "Frequency", monetary: "Monetary", phankhuc: "Phân khúc",
  tinhthanh: "Tỉnh/Thành", tongdon: "Tổng đơn", donhuy: "Đơn hủy",
  tylehuypct: "Tỷ lệ hủy (%)", lydophobien: "Lý do phổ biến",
  sku: "SKU", quantityonhand: "Tồn kho", safetystock: "Ngưỡng an toàn",
  thieuhut: "Thiếu hụt", mucdo: "Mức độ", sellerid: "Mã NB",
  sodongiaothanhcong: "Đơn giao TC", sosanpham: "Số SP",
  diemtrungbinh: "Điểm TB", sodanhgia: "Số đánh giá", hangdoanhthu: "Hạng",
  kenhthanhtoan: "Kênh TT", aov: "AOV", tongdoanhthu: "Tổng doanh thu",
  promocode: "Mã KM", discountpct: "Giảm (%)", startdate: "Từ ngày",
  enddate: "Đến ngày", sodonapdung: "Đơn áp dụng", doanhthugoc: "Doanh thu gốc",
  tonggiamgia: "Tổng giảm", aovcokhuyenmai: "AOV có KM",
  aovkhongkhuyenmai: "AOV không KM", donvivanchuyen: "Đơn vị VC",
  solohang: "Số lô", sologiaothanhcong: "Giao thành công",
  solothatbai: "Thất bại", songaygiaotb: "Số ngày TB", p95_songay: "P95 (ngày)",
  tongdanhgia: "Tổng đánh giá", danhgiathap: "Đánh giá thấp",
  tylethappct: "Tỷ lệ thấp (%)", r: "R", f: "F", m: "M",
}

const CHART_COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)"]

export function DashboardPage() {
  const [catalog, setCatalog] = useState<CatalogItem[]>([])
  const [active, setActive] = useState("YC01")
  const [result, setResult] = useState<AnalyticsResult | null>(null)
  const [funnel, setFunnel] = useState<FunnelStep[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void (async () => {
      const [cat, f] = await Promise.all([api.analyticsCatalog(), api.funnel()])
      setCatalog(cat)
      setFunnel(f.steps)
    })()
  }, [])

  useEffect(() => {
    setLoading(true)
    void api.analytics(active, 200).then((r) => { setResult(r); setLoading(false) })
  }, [active])

  return (
    <div className="mx-auto max-w-[1440px] space-y-4 px-4 py-4">
      {/* ---------------------------------------------------- pheu chuyen doi */}
      <Card className="gap-0 py-0">
        <CardHeader className="gap-0 border-b px-4 py-3">
          <CardTitle className="flex flex-wrap items-center gap-2 text-[13px] font-semibold">
            <TrendingDown className="size-4 text-brand" />
            Phễu chuyển đổi
            <Badge variant="secondary" className="text-[10px] font-normal">
              MongoDB aggregation pipeline
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4">
          {funnel.length === 0 ? (
            <Skeleton className="h-[220px] w-full" />
          ) : (
            <div className="grid gap-5 lg:grid-cols-[1.3fr_1fr]">
              <ResponsiveContainer width="100%" height={230}>
                <BarChart
                  data={funnel.map((s) => ({ ...s, label: STEP_LABEL[s.step] ?? s.step }))}
                  margin={{ top: 8, right: 8, bottom: 4, left: 4 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false}
                         tickFormatter={(v: number) => v.toLocaleString("vi-VN")} />
                  <Tooltip
                    formatter={(v) => [Number(v).toLocaleString("vi-VN"), "Số phiên"] as [string, string]}
                    contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid var(--border)" }}
                  />
                  <Bar dataKey="sessions" radius={[5, 5, 0, 0]}>
                    {funnel.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % 4]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>

              <div className="space-y-2 self-center">
                {funnel.map((s, i) => (
                  <div key={s.step} className="flex items-center gap-3 text-[12.5px]">
                    <span className="w-[130px] shrink-0">{STEP_LABEL[s.step] ?? s.step}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${s.conversion_pct}%`,
                          background: CHART_COLORS[i % 4],
                        }}
                      />
                    </div>
                    <span className="w-[112px] shrink-0 text-right tabular-nums">
                      {s.sessions.toLocaleString("vi-VN")}
                      <span className="ml-1 text-muted-foreground">({s.conversion_pct}%)</span>
                    </span>
                  </div>
                ))}
                <p className="pt-1 text-[11px] text-muted-foreground">
                  Đếm theo <code>session_id</code> duy nhất ở mỗi bước, gộp cả event mock
                  lẫn event sinh từ storefront.
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ---------------------------------------------------- 10 truy van */}
      <Card className="gap-0 py-0">
        <CardHeader className="gap-0 border-b px-4 py-3">
          <CardTitle className="flex items-center gap-2 text-[13px] font-semibold">
            <Filter className="size-4 text-brand" />
            Mười yêu cầu nghiệp vụ
            <Badge variant="secondary" className="text-[10px] font-normal">
              VIEW / PROCEDURE / FUNCTION trên PostgreSQL
            </Badge>
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-3 p-4">
          <div className="flex flex-wrap gap-1.5">
            {catalog.map((item) => (
              <button
                key={item.code}
                onClick={() => setActive(item.code)}
                title={item.view}
                className={`rounded-md border px-2.5 py-1.5 text-left text-[11.5px] transition
                  ${active === item.code
                    ? "border-brand bg-brand text-white"
                    : "border-border bg-card hover:border-brand hover:text-brand"}`}
              >
                <b>{item.code}</b> · {item.title}
              </button>
            ))}
          </div>

          {result && (
            <div className="flex flex-wrap items-baseline gap-2 pt-1">
              <span className="text-[13.5px] font-semibold">{result.title}</span>
              <code className="rounded bg-muted px-1.5 py-0.5 text-[11px] text-muted-foreground">
                {catalog.find((c) => c.code === active)?.view}
              </code>
              <span className="text-[12px] text-muted-foreground">{result.row_count} dòng</span>
            </div>
          )}

          {loading || !result ? (
            <Skeleton className="h-[380px] w-full" />
          ) : (
            <ResultTable result={result} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function ResultTable({ result }: { result: AnalyticsResult }) {
  if (!result.rows.length) {
    return <p className="py-10 text-center text-[13px] text-muted-foreground">Không có dữ liệu.</p>
  }

  const cols = Object.keys(result.rows[0])
  const isNumeric = (c: string) =>
    result.rows.every((r) => r[c] === null || typeof r[c] === "number")

  const fmt = (v: string | number | null) => {
    if (v === null || v === undefined) return <span className="text-muted-foreground">–</span>
    if (typeof v === "number") {
      return Number.isInteger(v)
        ? v.toLocaleString("vi-VN")
        : v.toLocaleString("vi-VN", { maximumFractionDigits: 2 })
    }
    return v
  }

  return (
    <div className="thin-scroll max-h-[500px] overflow-auto rounded-md border">
      <Table>
        <TableHeader className="sticky top-0 z-10 bg-muted">
          <TableRow>
            {cols.map((c) => (
              <TableHead
                key={c}
                className={`h-8 text-[10.5px] tracking-wide uppercase ${
                  isNumeric(c) ? "text-right" : ""}`}
              >
                {COLUMN_LABEL[c] ?? c}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {result.rows.map((row, i) => (
            <TableRow key={i} className="hover:bg-brand-soft/50">
              {cols.map((c) => (
                <TableCell
                  key={c}
                  className={`py-1.5 text-[12px] ${isNumeric(c) ? "text-right tabular-nums" : ""}`}
                >
                  {fmt(row[c])}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
