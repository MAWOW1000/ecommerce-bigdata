import { Star } from "lucide-react"
import type { Product } from "@/lib/api"
import { compact, vnd } from "@/lib/api"
import { Button } from "@/components/ui/button"

type Props = {
  product: Product
  onView: (p: Product) => void
  onAddToCart: (p: Product) => void
}

export function ProductCard({ product: p, onView, onAddToCart }: Props) {
  const out = p.quantityonhand === 0
  const low = !out && p.quantityonhand < 20

  return (
    <div
      onClick={() => onView(p)}
      className="group relative flex cursor-pointer flex-col overflow-hidden rounded-sm border border-border bg-card transition hover:-translate-y-0.5 hover:border-brand hover:shadow-lg"
    >
      <div className="relative aspect-square overflow-hidden bg-muted">
        <img
          src={p.image_url}
          alt={p.productname}
          loading="lazy"
          className="size-full object-cover transition duration-300 group-hover:scale-105"
        />
        {out && (
          <div className="absolute inset-0 grid place-items-center bg-black/55">
            <span className="rounded-full border border-white/70 px-3 py-1 text-[11px] font-semibold text-white">
              HẾT HÀNG
            </span>
          </div>
        )}
        {low && (
          <span className="absolute top-1.5 left-1.5 rounded-sm bg-warning px-1.5 py-0.5 text-[10px] font-bold text-white">
            Sắp hết
          </span>
        )}
        <span className="absolute right-0 bottom-0 bg-brand/90 px-1.5 py-0.5 text-[10px] font-semibold text-white">
          {p.categoryname}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-1.5 p-2.5">
        <p className="line-clamp-2 min-h-[34px] text-[13px] leading-[1.35]">{p.productname}</p>

        <div className="flex items-baseline gap-1.5">
          <span className="text-[15px] font-semibold text-brand">{vnd(p.sellprice)}</span>
        </div>

        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          {p.avgrating > 0 && (
            <span className="flex items-center gap-0.5">
              <Star className="size-3 fill-warning text-warning" />
              {p.avgrating}
            </span>
          )}
          <span>Đã bán {compact(p.sold)}</span>
        </div>

        <div className="truncate text-[11px] text-muted-foreground">{p.shopname}</div>

        <div className="mt-auto flex items-center justify-between pt-1 text-[11px]">
          <span className={out ? "text-destructive" : low ? "text-warning" : "text-success"}>
            Tồn kho: <b>{p.quantityonhand}</b>
          </span>
          <span className="text-muted-foreground">{p.sku.slice(-6)}</span>
        </div>

        <Button
          size="sm"
          disabled={out}
          onClick={(e) => { e.stopPropagation(); onAddToCart(p) }}
          className="mt-1 h-8 w-full bg-brand text-[12px] hover:bg-brand-dark"
        >
          Thêm vào giỏ
        </Button>
      </div>
    </div>
  )
}
