import { useEffect, useState } from "react"
import { toast } from "sonner"
import { api, type Category, type Customer, type Product } from "@/lib/api"
import { tracker } from "@/lib/tracker"
import { ProductCard } from "@/components/ProductCard"
import { CartPanel, type CartLine, type OrderResult } from "@/components/CartPanel"
import { EventStream } from "@/components/EventStream"
import { Skeleton } from "@/components/ui/skeleton"

type Props = { search: string; cart: CartLine[]; setCart: (f: (c: CartLine[]) => CartLine[]) => void }

export function StorePage({ search, cart, setCart }: Props) {
  const [categories, setCategories] = useState<Category[]>([])
  const [customers, setCustomers] = useState<Customer[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [categoryId, setCategoryId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  const [customerId, setCustomerId] = useState<number | null>(null)
  const [province, setProvince] = useState("Ha Noi")
  const [result, setResult] = useState<OrderResult | null>(null)
  const [busy, setBusy] = useState(false)

  // ------------------------------------------------------------- tai du lieu
  useEffect(() => {
    void (async () => {
      const [cats, custs] = await Promise.all([api.categories(), api.customers()])
      setCategories(cats)
      setCustomers(custs)
      void tracker.track("page_view", { page: "/", referrer: document.referrer || "direct" })
    })()
  }, [])

  const loadProducts = async (catId: number | null, q: string) => {
    setLoading(true)
    setProducts(await api.products({
      category_id: catId ?? undefined, q: q || undefined, limit: 24,
    }))
    setLoading(false)
  }

  useEffect(() => { void loadProducts(categoryId, search) }, [categoryId, search])

  // ------------------------------------------------------------- gio hang
  const addToCart = (p: Product) => {
    setCart((prev) => {
      const found = prev.find((l) => l.variant_id === p.variantid)
      if (found) {
        return prev.map((l) =>
          l.variant_id === p.variantid ? { ...l, quantity: l.quantity + 1 } : l)
      }
      return [...prev, {
        variant_id: p.variantid, product_id: p.productid, name: p.productname,
        sku: p.sku, image_url: p.image_url, unit_price: p.sellprice, quantity: 1,
      }]
    })
    void tracker.track("add_to_cart", {
      product_id: p.productid, variant_id: p.variantid, quantity: 1, price: p.sellprice,
    }, province)
    toast.success("Đã thêm vào giỏ", { description: p.productname })
  }

  const removeFromCart = (variantId: number) => {
    const line = cart.find((l) => l.variant_id === variantId)
    setCart((prev) => prev.filter((l) => l.variant_id !== variantId))
    void tracker.track("remove_from_cart",
      { variant_id: variantId, quantity: line?.quantity }, province)
  }

  const checkout = async () => {
    if (!customerId) {
      setResult({
        ok: false, kind: "khóa ngoại",
        error: "Đơn hàng bắt buộc có CustomerID — hãy chọn một khách hàng.",
      })
      return
    }
    setBusy(true)
    const total = cart.reduce((s, l) => s + l.unit_price * l.quantity, 0)
    await tracker.track("checkout_start", { cart_size: cart.length, cart_value: total }, province)

    const res = await api.createOrder({
      customer_id: customerId,
      ship_province: province,
      session_id: tracker.sessionId,
      lines: cart.map((l) => ({
        variant_id: l.variant_id, quantity: l.quantity, unit_price: l.unit_price,
      })),
    })
    setResult(res)
    setBusy(false)

    if (res.ok) {
      toast.success(`Đặt hàng thành công — đơn #${res.order_id}`)
      setCart(() => [])
      void loadProducts(categoryId, search)   // tai lai de thay ton kho giam that
    } else {
      toast.error("Giao dịch bị chặn", { description: res.error })
    }
  }

  return (
    <div className="mx-auto grid max-w-[1440px] gap-4 px-4 py-4 lg:grid-cols-[1fr_360px]">
      <div className="space-y-4">
        {/* ---------------------------------------------------- danh muc */}
        <section className="rounded-sm border bg-card p-3">
          <h2 className="mb-2.5 text-[12px] font-semibold tracking-wide text-muted-foreground uppercase">
            Danh mục
          </h2>
          <div className="flex flex-wrap gap-1.5">
            <CategoryChip
              active={categoryId === null}
              label="Tất cả"
              onClick={() => setCategoryId(null)}
            />
            {categories.map((c) => (
              <CategoryChip
                key={c.categoryid}
                active={categoryId === c.categoryid}
                label={`${c.categoryname} (${c.sosanpham})`}
                onClick={() => {
                  setCategoryId(c.categoryid)
                  void tracker.track("search",
                    { filters_applied: ["category"], category_id: c.categoryid }, province)
                }}
              />
            ))}
          </div>
        </section>

        {/* ---------------------------------------------------- san pham */}
        <section>
          <div className="mb-2.5 flex items-baseline gap-2">
            <h2 className="text-[15px] font-semibold">
              {search ? `Kết quả cho "${search}"` : "Gợi ý hôm nay"}
            </h2>
            <span className="text-[12px] text-muted-foreground">{products.length} sản phẩm</span>
          </div>

          {loading ? (
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
              {Array.from({ length: 10 }).map((_, i) => (
                <Skeleton key={i} className="h-[330px] rounded-sm" />
              ))}
            </div>
          ) : products.length === 0 ? (
            <p className="rounded-sm border bg-card py-16 text-center text-[13px] text-muted-foreground">
              Không tìm thấy sản phẩm nào.
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
              {products.map((p) => (
                <ProductCard
                  key={p.variantid}
                  product={p}
                  onView={(prod) => void tracker.track("product_view", {
                    product_id: prod.productid, variant_id: prod.variantid,
                    dwell_seconds: Math.floor(Math.random() * 90) + 5,
                    position_in_list: products.indexOf(prod) + 1,
                  }, province)}
                  onAddToCart={addToCart}
                />
              ))}
            </div>
          )}
        </section>
      </div>

      {/* ---------------------------------------------------- cot phai */}
      <aside className="space-y-4 lg:sticky lg:top-[104px] lg:self-start">
        <CartPanel
          lines={cart}
          customers={customers}
          customerId={customerId}
          province={province}
          result={result}
          busy={busy}
          onCustomerChange={(id) => { setCustomerId(id); tracker.setUser(id) }}
          onProvinceChange={setProvince}
          onRemove={removeFromCart}
          onCheckout={() => void checkout()}
        />
        <EventStream />
      </aside>
    </div>
  )
}

function CategoryChip({ active, label, onClick }: {
  active: boolean; label: string; onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full border px-3 py-1 text-[12px] transition
        ${active
          ? "border-brand bg-brand text-white"
          : "border-border bg-card hover:border-brand hover:text-brand"}`}
    >
      {label}
    </button>
  )
}
