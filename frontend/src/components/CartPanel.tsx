import { AlertTriangle, CheckCircle2, ShoppingBag, Trash2 } from "lucide-react"
import type { Customer } from "@/lib/api"
import { vnd } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"

export type CartLine = {
  variant_id: number
  product_id: number
  name: string
  sku: string
  image_url: string
  unit_price: number
  quantity: number
}

export type OrderResult =
  | { ok: true; order_id: number; total: number }
  | { ok: false; error: string; kind: string }

const PROVINCES = [
  "Ha Noi", "TP Ho Chi Minh", "Da Nang", "Hai Phong",
  "Can Tho", "Binh Duong", "Dong Nai", "Khanh Hoa",
]

type Props = {
  lines: CartLine[]
  customers: Customer[]
  customerId: number | null
  province: string
  result: OrderResult | null
  busy: boolean
  onCustomerChange: (id: number | null) => void
  onProvinceChange: (p: string) => void
  onRemove: (variantId: number) => void
  onCheckout: () => void
}

export function CartPanel({
  lines, customers, customerId, province, result, busy,
  onCustomerChange, onProvinceChange, onRemove, onCheckout,
}: Props) {
  const total = lines.reduce((s, l) => s + l.unit_price * l.quantity, 0)

  return (
    <Card className="gap-0 py-0">
      <CardHeader className="gap-0 border-b px-4 py-3">
        <CardTitle className="flex items-center gap-2 text-[13px] font-semibold">
          <ShoppingBag className="size-4 text-brand" />
          Giỏ hàng
          <span className="font-normal text-muted-foreground">→ PostgreSQL</span>
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3 p-4">
        <div className="grid gap-2">
          <Select
            value={customerId ? String(customerId) : "guest"}
            onValueChange={(v) => onCustomerChange(v === "guest" ? null : Number(v))}
          >
            <SelectTrigger className="h-9 w-full text-[12.5px]">
              <SelectValue placeholder="Chọn khách hàng">
                {(value: string) => {
                  if (!value || value === "guest") return "Khách vãng lai (chưa đăng nhập)"
                  const c = customers.find((x) => String(x.customerid) === value)
                  return c ? `#${c.customerid} — ${c.fullname}` : value
                }}
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="guest">Khách vãng lai (chưa đăng nhập)</SelectItem>
              {customers.map((c) => (
                <SelectItem key={c.customerid} value={String(c.customerid)}>
                  #{c.customerid} — {c.fullname} ({c.province})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={province} onValueChange={(v) => v && onProvinceChange(v)}>
            <SelectTrigger className="h-9 w-full text-[12.5px]">
              <SelectValue>{(value: string) => `Giao đến: ${value}`}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {PROVINCES.map((p) => <SelectItem key={p} value={p}>Giao đến: {p}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>

        <Separator />

        {lines.length === 0 ? (
          <p className="py-5 text-center text-[12px] text-muted-foreground">
            Giỏ hàng trống
          </p>
        ) : (
          <div className="thin-scroll max-h-[230px] space-y-2 overflow-y-auto pr-1">
            {lines.map((l) => (
              <div key={l.variant_id} className="flex items-center gap-2">
                <img src={l.image_url} alt="" className="size-10 shrink-0 rounded object-cover" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-[12px] leading-tight">{l.name}</p>
                  <p className="text-[11px] text-muted-foreground">
                    {vnd(l.unit_price)} × {l.quantity}
                  </p>
                </div>
                <span className="shrink-0 text-[12px] font-semibold text-brand">
                  {vnd(l.unit_price * l.quantity)}
                </span>
                <button
                  onClick={() => onRemove(l.variant_id)}
                  className="shrink-0 text-muted-foreground hover:text-destructive"
                  aria-label="Xóa"
                >
                  <Trash2 className="size-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        {lines.length > 0 && (
          <>
            <Separator />
            <div className="flex items-center justify-between text-[13px]">
              <span className="font-medium">Tổng cộng</span>
              <span className="text-[16px] font-bold text-brand">{vnd(total)}</span>
            </div>
          </>
        )}

        <Button
          onClick={onCheckout}
          disabled={lines.length === 0 || busy}
          className="h-10 w-full bg-brand text-[13px] font-semibold hover:bg-brand-dark"
        >
          {busy ? "Đang xử lý..." : "Đặt hàng"}
        </Button>

        {result && <ResultNotice result={result} />}
      </CardContent>
    </Card>
  )
}

function ResultNotice({ result }: { result: OrderResult }) {
  if (result.ok) {
    return (
      <div className="flex gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-2.5 text-[11.5px] text-emerald-900">
        <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />
        <div>
          Đã tạo đơn <b>#{result.order_id}</b> — {vnd(result.total)}.
          <div className="mt-0.5 text-emerald-800">
            Trigger <code className="rounded bg-emerald-100 px-1">tr_orderdetail_tru_ton_kho</code>
            {" "}đã trừ tồn kho trong cùng transaction.
          </div>
        </div>
      </div>
    )
  }
  return (
    <div className="flex gap-2 rounded-md border border-rose-200 bg-rose-50 p-2.5 text-[11.5px] text-rose-900">
      <AlertTriangle className="mt-0.5 size-4 shrink-0 text-rose-600" />
      <div>
        <b>Giao dịch bị chặn ({result.kind})</b>
        <pre className="mt-1 break-all whitespace-pre-wrap text-[10.5px] text-rose-800">
          {result.error}
        </pre>
        <div className="mt-1 text-rose-800">
          Toàn bộ đơn đã rollback — không dòng nào lọt vào CSDL.
        </div>
      </div>
    </div>
  )
}
