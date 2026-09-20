import { useEffect, useState } from "react"
import { Activity, RefreshCw } from "lucide-react"
import { api, type EventStats, type TrackedEvent } from "@/lib/api"
import { tracker } from "@/lib/tracker"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const TYPE_COLOR: Record<string, string> = {
  page_view: "bg-slate-100 text-slate-700",
  search: "bg-blue-100 text-blue-700",
  product_view: "bg-violet-100 text-violet-700",
  add_to_cart: "bg-amber-100 text-amber-800",
  remove_from_cart: "bg-rose-100 text-rose-700",
  checkout_start: "bg-cyan-100 text-cyan-800",
  purchase: "bg-emerald-100 text-emerald-700",
}

export function EventStream() {
  const [events, setEvents] = useState<TrackedEvent[]>([])
  const [stats, setStats] = useState<EventStats | null>(null)
  const [onlyLive, setOnlyLive] = useState(false)
  const [freshIds, setFreshIds] = useState<Set<string>>(new Set())

  const reload = async () => {
    const [list, s] = await Promise.all([api.recentEvents(25, onlyLive), api.eventStats()])
    setEvents(list)
    setStats(s)
  }

  useEffect(() => { void reload() }, [onlyLive])

  // Su kien vua ban tu UI duoc chen ngay len dau danh sach, khong cho reload.
  useEffect(() => {
    const unsubscribe = tracker.subscribe((ev) => {
      setEvents((prev) => [ev, ...prev].slice(0, 25))
      setFreshIds((prev) => new Set(prev).add(ev.event_id))
      setStats((prev) =>
        prev ? { ...prev, total: prev.total + 1, live: prev.live + 1 } : prev)
      setTimeout(() => setFreshIds((prev) => {
        const next = new Set(prev); next.delete(ev.event_id); return next
      }), 1200)
    })
    return () => { unsubscribe() }
  }, [])

  return (
    <Card className="gap-0 py-0">
      <CardHeader className="gap-0 border-b px-4 py-3">
        <CardTitle className="flex items-center gap-2 text-[13px] font-semibold">
          <Activity className="size-4 text-brand" />
          Event Stream
          <span className="font-normal text-muted-foreground">→ MongoDB</span>
          <Button
            variant="ghost" size="sm"
            onClick={() => void reload()}
            className="ml-auto h-7 px-2 text-muted-foreground"
          >
            <RefreshCw className="size-3.5" />
          </Button>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3 p-4">
        <div className="grid grid-cols-2 gap-2">
          <Stat label="Tổng document" value={stats?.total ?? 0} />
          <Stat label="Sinh từ UI này" value={stats?.live ?? 0} highlight />
        </div>

        <label className="flex cursor-pointer items-center gap-2 text-[12px] text-muted-foreground">
          <input
            type="checkbox"
            checked={onlyLive}
            onChange={(e) => setOnlyLive(e.target.checked)}
            className="size-3.5 accent-[#ee4d2d]"
          />
          Chỉ hiện event sinh từ giao diện này
        </label>

        <div className="thin-scroll max-h-[420px] space-y-1.5 overflow-y-auto pr-1">
          {events.length === 0 && (
            <p className="py-6 text-center text-[12px] text-muted-foreground">
              Chưa có event. Hãy bấm vào một sản phẩm.
            </p>
          )}
          {events.map((ev) => (
            <div
              key={ev.event_id}
              className={`rounded-md border border-border bg-card px-2.5 py-2 text-[11.5px]
                ${ev.source === "live_ui" ? "border-l-2 border-l-brand" : ""}
                ${freshIds.has(ev.event_id) ? "event-new" : ""}`}
            >
              <div className="flex items-center gap-2">
                <Badge
                  variant="secondary"
                  className={`h-[18px] rounded px-1.5 text-[10px] font-semibold ${
                    TYPE_COLOR[ev.event_type] ?? "bg-slate-100 text-slate-700"}`}
                >
                  {ev.event_type}
                </Badge>
                <span className="ml-auto text-[10.5px] text-muted-foreground">
                  {new Date(ev.timestamp).toLocaleTimeString("vi-VN")}
                </span>
              </div>
              <div className="mt-1 text-[10.5px] text-muted-foreground">
                user: {ev.user_id ?? "khách vãng lai"} · {ev.device?.platform ?? "—"}
              </div>
              <pre className="mt-1 overflow-hidden text-[10px] leading-snug break-all whitespace-pre-wrap text-muted-foreground">
                {JSON.stringify(ev.payload ?? {})}
              </pre>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function Stat({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className={`rounded-md px-3 py-2 ${highlight ? "bg-brand-soft" : "bg-muted"}`}>
      <div className={`text-[19px] leading-tight font-bold ${highlight ? "text-brand" : ""}`}>
        {value.toLocaleString("vi-VN")}
      </div>
      <div className="text-[10.5px] text-muted-foreground">{label}</div>
    </div>
  )
}
