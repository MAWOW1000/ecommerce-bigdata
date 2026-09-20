import { useState } from "react"
import { Toaster } from "@/components/ui/sonner"
import { Header } from "@/components/Header"
import { StorePage } from "@/pages/StorePage"
import { DashboardPage } from "@/pages/DashboardPage"
import { BigDataPage } from "@/pages/BigDataPage"
import type { CartLine } from "@/components/CartPanel"
import { tracker } from "@/lib/tracker"

type Page = "store" | "dashboard" | "bigdata"

export default function App() {
  const [page, setPage] = useState<Page>(() => {
    const path = window.location.pathname
    if (path.startsWith("/dashboard")) return "dashboard"
    if (path.startsWith("/bigdata")) return "bigdata"
    return "store"
  })
  const [searchInput, setSearchInput] = useState("")
  const [search, setSearch] = useState("")
  const [cart, setCart] = useState<CartLine[]>([])

  const navigate = (p: Page) => {
    setPage(p)
    window.history.pushState({}, "", p === "store" ? "/" : `/${p}`)
  }

  const submitSearch = () => {
    const q = searchInput.trim()
    setSearch(q)
    if (q) void tracker.track("search", { query: q, result_count: null })
    if (page !== "store") navigate("store")
  }

  return (
    <div className="min-h-screen bg-background">
      <Header
        page={page}
        onNavigate={navigate}
        search={searchInput}
        onSearchChange={setSearchInput}
        onSearchSubmit={submitSearch}
        cartCount={cart.reduce((s, l) => s + l.quantity, 0)}
      />

      {page === "store" && <StorePage search={search} cart={cart} setCart={setCart} />}
      {page === "dashboard" && <DashboardPage />}
      {page === "bigdata" && <BigDataPage />}

      <footer className="border-t bg-card py-5 text-center text-[11.5px] text-muted-foreground">
        Đồ án Cơ sở dữ liệu &amp; Big Data · Kiến trúc dữ liệu kép PostgreSQL + MongoDB
      </footer>

      <Toaster position="bottom-right" richColors />
    </div>
  )
}
