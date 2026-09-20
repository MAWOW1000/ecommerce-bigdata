import { useEffect, useState } from "react"
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts"
import {
  ChevronRight, Database, FileText, Folder, HardDrive, Layers, Server, Zap,
} from "lucide-react"
import {
  api, bytes, type HadoopStatus, type HdfsEntry, type SparkResult, type SparkTable,
} from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"

const CHART_COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)",
                      "var(--chart-4)", "var(--chart-5)"]

const COLUMN_LABEL: Record<string, string> = {
  carrier: "Đơn vị VC", so_lo: "Số lô", so_ngay_giao_tb: "Ngày giao TB",
  p95_ngay: "P95 (ngày)", so_lan_quet_tb: "Lần quét TB", so_tram_tb: "Trạm TB",
  event_type: "Bước", so_phien: "Số phiên", so_su_kien: "Số sự kiện",
  thu_tu: "#", ty_le_pct: "Tỷ lệ (%)", product_id: "Mã SP",
  product_name: "Sản phẩm", category: "Danh mục", shop: "Gian hàng",
  so_don: "Số đơn", so_luong_ban: "SL bán", doanh_thu: "Doanh thu",
  product_view: "Lượt xem", add_to_cart: "Thêm giỏ",
  ty_le_xem_thanh_don: "Xem→Đơn (%)", thang: "Tháng", so_luong: "Số lượng",
  hang: "Hạng", gio: "Giờ", platform: "Nền tảng",
}

export function BigDataPage() {
  const [status, setStatus] = useState<HadoopStatus | null>(null)
  const [path, setPath] = useState("/ecommerce")
  const [entries, setEntries] = useState<HdfsEntry[]>([])
  const [catalog, setCatalog] = useState<SparkTable[]>([])
  const [active, setActive] = useState("hieu_suat_van_chuyen")
  const [result, setResult] = useState<SparkResult | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    void (async () => {
      const [s, c] = await Promise.all([api.hadoopStatus(), api.sparkCatalog()])
      setStatus(s)
      setCatalog(c)
    })()
  }, [])

  useEffect(() => {
    void api.hdfsLs(path).then((d) => setEntries(d.entries)).catch(() => setEntries([]))
  }, [path])

  useEffect(() => {
    setLoading(true)
    void api.sparkResult(active)
      .then(setResult)
      .catch(() => setResult(null))
      .finally(() => setLoading(false))
  }, [active])

  const crumbs = path.split("/").filter(Boolean)

  return (
    <div className="mx-auto max-w-[1440px] space-y-4 px-4 py-4">
      {/* -------------------------------------------------- trang thai cum */}
      <Card className="gap-0 py-0">
        <CardHeader className="gap-0 border-b px-4 py-3">
          <CardTitle className="flex flex-wrap items-center gap-2 text-[13px] font-semibold">
            <Server className="size-4 text-brand" />
            Cụm Hadoop HDFS
            {status?.online ? (
              <Badge className="h-[18px] bg-emerald-100 px-2 text-[10px] font-semibold text-emerald-700 hover:bg-emerald-100">
                ĐANG CHẠY
              </Badge>
            ) : (
              <Badge variant="secondary" className="h-[18px] px-2 text-[10px]">
                CHƯA KHỞI ĐỘNG
              </Badge>
            )}
            {status?.namenode_ui && (
              <a href={status.namenode_ui} target="_blank" rel="noreferrer"
                 className="ml-auto text-[11.5px] font-normal text-brand hover:underline">
                Mở giao diện NameNode ↗
              </a>
            )}
          </CardTitle>
        </CardHeader>

        <CardContent className="p-4">
          {!status ? (
            <Skeleton className="h-[72px] w-full" />
          ) : !status.online ? (
            <p className="py-4 text-center text-[12.5px] text-muted-foreground">
              HDFS chưa chạy. Khởi động bằng{" "}
              <code className="rounded bg-muted px-1.5 py-0.5">./scripts/start_hdfs.sh</code>
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-6">
              <Metric icon={<Server className="size-3.5" />} label="DataNode sống"
                      value={String(status.live_datanodes)} accent />
              <Metric icon={<Layers className="size-3.5" />} label="Tổng khối"
                      value={String(status.blocks_total)} />
              <Metric icon={<FileText className="size-3.5" />} label="Tổng file"
                      value={String(status.files_total)} />
              <Metric icon={<HardDrive className="size-3.5" />} label="Đã dùng"
                      value={bytes(status.capacity_used ?? 0)} />
              <Metric icon={<HardDrive className="size-3.5" />} label="Còn trống"
                      value={bytes(status.capacity_remaining ?? 0)} />
              <Metric icon={<Database className="size-3.5" />} label="DataNode chết"
                      value={String(status.dead_datanodes)} />
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-[400px_1fr]">
        {/* ------------------------------------------------ duyet cay HDFS */}
        <Card className="gap-0 py-0">
          <CardHeader className="gap-0 border-b px-4 py-3">
            <CardTitle className="text-[13px] font-semibold">
              <span className="flex items-center gap-2">
                <Folder className="size-4 text-brand" /> Cây thư mục HDFS
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent className="p-4">
            <div className="mb-2.5 flex flex-wrap items-center gap-0.5 text-[11.5px]">
              <button onClick={() => setPath("/ecommerce")}
                      className="text-brand hover:underline">ecommerce</button>
              {crumbs.slice(1).map((c, i) => (
                <span key={i} className="flex items-center gap-0.5">
                  <ChevronRight className="size-3 text-muted-foreground" />
                  <button
                    onClick={() => setPath("/" + crumbs.slice(0, i + 2).join("/"))}
                    className="text-brand hover:underline"
                  >{c}</button>
                </span>
              ))}
            </div>

            <div className="thin-scroll max-h-[420px] space-y-0.5 overflow-y-auto">
              {entries.length === 0 && (
                <p className="py-6 text-center text-[12px] text-muted-foreground">
                  Thư mục trống hoặc HDFS chưa chạy.
                </p>
              )}
              {entries.map((e) => (
                <button
                  key={e.name}
                  disabled={e.type === "FILE"}
                  onClick={() => setPath(`${path}/${e.name}`)}
                  className={`flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-[12px]
                    ${e.type === "DIRECTORY"
                      ? "hover:bg-brand-soft"
                      : "cursor-default text-muted-foreground"}`}
                >
                  {e.type === "DIRECTORY"
                    ? <Folder className="size-3.5 shrink-0 text-brand" />
                    : <FileText className="size-3.5 shrink-0" />}
                  <span className="truncate">{e.name}</span>
                  {e.type === "FILE" && (
                    <span className="ml-auto shrink-0 tabular-nums">
                      {bytes(e.size)}
                      <span className="ml-1.5 text-[10px]">×{e.replication}</span>
                    </span>
                  )}
                </button>
              ))}
            </div>

            <p className="mt-2.5 border-t pt-2.5 text-[10.5px] leading-snug text-muted-foreground">
              <code>×1</code> là hệ số nhân bản. Cụm một máy nên đặt bằng 1; trong cụm
              thật giá trị mặc định là 3 — mỗi khối nằm trên ba máy khác nhau.
            </p>
          </CardContent>
        </Card>

        {/* ------------------------------------------- ket qua Spark */}
        <Card className="gap-0 py-0">
          <CardHeader className="gap-0 border-b px-4 py-3">
            <CardTitle className="flex flex-wrap items-center gap-2 text-[13px] font-semibold">
              <Zap className="size-4 text-brand" />
              Kết quả xử lý bằng Apache Spark
              <Badge variant="secondary" className="text-[10px] font-normal">
                đọc từ hdfs://127.0.0.1:9000
              </Badge>
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-3 p-4">
            <div className="flex flex-wrap gap-1.5">
              {catalog.map((t) => (
                <button
                  key={t.name}
                  disabled={!t.available}
                  onClick={() => setActive(t.name)}
                  className={`rounded-md border px-2.5 py-1.5 text-[11.5px] transition
                    ${active === t.name
                      ? "border-brand bg-brand text-white"
                      : t.available
                        ? "border-border bg-card hover:border-brand hover:text-brand"
                        : "cursor-not-allowed border-border bg-muted text-muted-foreground"}`}
                >
                  {t.title}
                </button>
              ))}
            </div>

            {loading ? (
              <Skeleton className="h-[360px] w-full" />
            ) : !result ? (
              <p className="py-12 text-center text-[12.5px] text-muted-foreground">
                Chưa có kết quả. Chạy{" "}
                <code className="rounded bg-muted px-1.5 py-0.5">
                  uv run python -m ecommerce_bigdata.spark_analytics
                </code>
              </p>
            ) : (
              <>
                <SparkChart result={result} />
                <ResultTable result={result} />
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function Metric({ icon, label, value, accent }: {
  icon: React.ReactNode; label: string; value: string; accent?: boolean
}) {
  return (
    <div className={`rounded-md px-3 py-2 ${accent ? "bg-brand-soft" : "bg-muted"}`}>
      <div className="flex items-center gap-1 text-[10.5px] text-muted-foreground">
        {icon} {label}
      </div>
      <div className={`text-[17px] leading-tight font-bold ${accent ? "text-brand" : ""}`}>
        {value}
      </div>
    </div>
  )
}

/** Moi bang ket qua co mot dang bieu do phu hop rieng. */
function SparkChart({ result }: { result: SparkResult }) {
  const rows = result.rows

  if (result.name === "hieu_suat_van_chuyen") {
    return (
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="carrier" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="so_ngay_giao_tb" name="Ngày giao TB (SQL)"
               fill="var(--chart-1)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="so_tram_tb" name="Số trạm TB (MongoDB)"
               fill="var(--chart-2)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    )
  }

  if (result.name === "pheu_chuyen_doi") {
    return (
      <ResponsiveContainer width="100%" height={230}>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="event_type" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
          <Bar dataKey="so_phien" name="Số phiên" radius={[5, 5, 0, 0]}>
            {rows.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % 5]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    )
  }

  if (result.name === "gio_cao_diem") {
    const byHour = new Map<number, Record<string, number>>()
    for (const r of rows) {
      const h = Number(r.gio)
      const entry = byHour.get(h) ?? { gio: h }
      entry[String(r.platform)] = Number(r.so_su_kien)
      byHour.set(h, entry)
    }
    const data = [...byHour.values()].sort((a, b) => a.gio - b.gio)
    const platforms = [...new Set(rows.map((r) => String(r.platform)))]
    return (
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 4, left: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis dataKey="gio" tick={{ fontSize: 11 }} tickLine={false} axisLine={false}
                 tickFormatter={(v: number) => `${String(v).padStart(2, "0")}h`} />
          <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }}
                   labelFormatter={(v) => `${String(v).padStart(2, "0")}h`} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {platforms.map((p, i) => (
            <Line key={p} type="monotone" dataKey={p} stroke={CHART_COLORS[i % 5]}
                  strokeWidth={1.8} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    )
  }

  return null
}

function ResultTable({ result }: { result: SparkResult }) {
  if (!result.rows.length) {
    return <p className="py-8 text-center text-[13px] text-muted-foreground">Không có dữ liệu.</p>
  }

  const cols = Object.keys(result.rows[0])
  const isNumeric = (c: string) =>
    result.rows.every((r) => r[c] === null || typeof r[c] === "number")

  const fmt = (v: string | number | null) => {
    if (v === null) return <span className="text-muted-foreground">–</span>
    if (typeof v === "number") {
      return Number.isInteger(v)
        ? v.toLocaleString("vi-VN")
        : v.toLocaleString("vi-VN", { maximumFractionDigits: 2 })
    }
    return v
  }

  return (
    <div className="thin-scroll max-h-[340px] overflow-auto rounded-md border">
      <Table>
        <TableHeader className="sticky top-0 z-10 bg-muted">
          <TableRow>
            {cols.map((c) => (
              <TableHead key={c}
                className={`h-8 text-[10.5px] tracking-wide uppercase ${
                  isNumeric(c) ? "text-right" : ""}`}>
                {COLUMN_LABEL[c] ?? c}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {result.rows.map((row, i) => (
            <TableRow key={i} className="hover:bg-brand-soft/50">
              {cols.map((c) => (
                <TableCell key={c}
                  className={`py-1.5 text-[12px] ${isNumeric(c) ? "text-right tabular-nums" : ""}`}>
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
