import { BarChart3, Database, Leaf, Search, Server, ShoppingCart, Store } from "lucide-react"
import { Input } from "@/components/ui/input"

type Page = "store" | "dashboard" | "bigdata"

type Props = {
  page: Page
  onNavigate: (page: Page) => void
  search: string
  onSearchChange: (v: string) => void
  onSearchSubmit: () => void
  cartCount: number
}

export function Header({
  page, onNavigate, search, onSearchChange, onSearchSubmit, cartCount,
}: Props) {
  return (
    <header className="brand-gradient sticky top-0 z-30 text-white shadow-sm">
      <div className="mx-auto max-w-[1440px] px-4 pt-2 pb-3">
        {/* Hang tren: cac nhan ky thuat, thay cho thanh dieu huong phu */}
        <div className="flex items-center gap-4 text-[11.5px] text-white/80">
          <span className="flex items-center gap-1"><Database className="size-3" /> PostgreSQL · giao dịch</span>
          <span className="flex items-center gap-1"><Leaf className="size-3" /> MongoDB · hành vi</span>
          <span className="flex items-center gap-1"><Server className="size-3" /> HDFS + Spark · phân tích</span>
          <span className="ml-auto hidden sm:block">Đồ án CSDL &amp; Big Data</span>
        </div>

        {/* Hang duoi: logo - o tim kiem - gio hang */}
        <div className="mt-2 flex items-center gap-5">
          <button
            onClick={() => onNavigate("store")}
            className="flex shrink-0 items-center gap-2 text-[22px] font-bold tracking-tight"
          >
            <Store className="size-6" /> ShopDB
          </button>

          <div className="relative flex-1">
            <Input
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onSearchSubmit()}
              placeholder="Tìm sản phẩm, thương hiệu..."
              className="h-10 border-0 bg-white pr-12 text-foreground placeholder:text-muted-foreground"
            />
            <button
              onClick={onSearchSubmit}
              className="absolute top-1 right-1 flex h-8 w-10 items-center justify-center rounded bg-brand text-white hover:bg-brand-dark"
              aria-label="Tìm kiếm"
            >
              <Search className="size-4" />
            </button>
          </div>

          <nav className="flex shrink-0 items-center gap-1">
            <NavButton
              active={page === "store"}
              onClick={() => onNavigate("store")}
              icon={<ShoppingCart className="size-4" />}
              label="Cửa hàng"
              badge={cartCount}
            />
            <NavButton
              active={page === "dashboard"}
              onClick={() => onNavigate("dashboard")}
              icon={<BarChart3 className="size-4" />}
              label="Phân tích"
            />
            <NavButton
              active={page === "bigdata"}
              onClick={() => onNavigate("bigdata")}
              icon={<Server className="size-4" />}
              label="Big Data"
            />
          </nav>
        </div>
      </div>
    </header>
  )
}

function NavButton({
  active, onClick, icon, label, badge,
}: {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
  badge?: number
}) {
  return (
    <button
      onClick={onClick}
      className={`relative flex items-center gap-1.5 rounded px-3 py-2 text-[13px] font-medium transition
        ${active ? "bg-white/20" : "hover:bg-white/10"}`}
    >
      {icon}
      <span className="hidden md:inline">{label}</span>
      {badge ? (
        <span className="absolute -top-0.5 -right-0.5 flex size-[17px] items-center justify-center rounded-full bg-white text-[10px] font-bold text-brand">
          {badge}
        </span>
      ) : null}
    </button>
  )
}
