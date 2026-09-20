/** Lop goi API toi backend FastAPI. */

export type Product = {
  productid: number
  productname: string
  categoryname: string
  shopname: string
  variantid: number
  sku: string
  color: string | null
  size: string | null
  sellprice: number
  quantityonhand: number
  avgrating: number
  image_url: string
  sold: number
}

export type Category = { categoryid: number; categoryname: string; sosanpham: number }
export type Customer = { customerid: number; fullname: string; province: string }

export type TrackedEvent = {
  event_id: string
  session_id: string
  user_id: number | null
  event_type: string
  timestamp: string
  device?: { platform?: string }
  payload?: Record<string, unknown>
  source?: string
}

export type EventStats = { total: number; live: number; by_type: Record<string, number> }
export type FunnelStep = { step: string; events: number; sessions: number; conversion_pct: number }

export type AnalyticsResult = {
  code: string
  title: string
  row_count: number
  rows: Record<string, string | number | null>[]
}

export type CatalogItem = { code: string; view: string; title: string }

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) throw new Error(`${path} -> ${res.status}`)
  return res.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  return res.json() as Promise<T>
}

export const api = {
  categories: () => get<Category[]>("/api/categories"),
  customers: () => get<Customer[]>("/api/customers?limit=40"),

  products: (params: { category_id?: number; q?: string; limit?: number }) => {
    const sp = new URLSearchParams()
    if (params.category_id) sp.set("category_id", String(params.category_id))
    if (params.q) sp.set("q", params.q)
    sp.set("limit", String(params.limit ?? 24))
    return get<Product[]>(`/api/products?${sp}`)
  },

  track: (event: {
    session_id: string
    user_id: number | null
    event_type: string
    payload?: Record<string, unknown>
    device?: Record<string, unknown>
    geo?: Record<string, unknown>
  }) => post<{ ok: boolean; event: TrackedEvent }>("/api/track", event),

  recentEvents: (limit = 25, onlyLive = false) =>
    get<TrackedEvent[]>(`/api/events/recent?limit=${limit}&only_live=${onlyLive}`),

  eventStats: () => get<EventStats>("/api/events/stats"),
  funnel: () => get<{ steps: FunnelStep[] }>("/api/analytics/mongo/funnel"),
  analyticsCatalog: () => get<CatalogItem[]>("/api/analytics/catalog"),
  analytics: (code: string, limit = 200) =>
    get<AnalyticsResult>(`/api/analytics/${code}?limit=${limit}`),
  inventory: (variantId: number) =>
    get<{ quantityonhand: number; safetystock: number }>(`/api/inventory/${variantId}`),

  createOrder: (body: {
    customer_id: number
    ship_province: string
    session_id: string
    lines: { variant_id: number; quantity: number; unit_price: number }[]
  }) =>
    post<
      | { ok: true; order_id: number; total: number }
      | { ok: false; error: string; kind: string }
    >("/api/orders", body),
}

export const vnd = (n: number) =>
  new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 })
    .format(n)

export const compact = (n: number) =>
  n >= 1000 ? `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}k` : String(n)
