/** Logic trang ban hang: tai du lieu tu PostgreSQL, ban event sang MongoDB. */

const vnd = (n) => new Intl.NumberFormat("vi-VN").format(Math.round(n)) + " ₫";
const $ = (id) => document.getElementById(id);

let cart = [];        // [{variant_id, name, sku, unit_price, quantity, stock}]
let products = [];

// ------------------------------------------------------------------ khoi tao
document.getElementById("sid").textContent = Tracker.sessionId;

Tracker.onEvent((ev) => { if (ev) prependEvent(ev, true); refreshStats(); });

async function init() {
  const [cats, customers] = await Promise.all([
    fetch("/api/categories").then((r) => r.json()),
    fetch("/api/customers").then((r) => r.json()),
  ]);

  cats.forEach((c) => {
    const o = document.createElement("option");
    o.value = c.categoryid;
    o.textContent = `${c.categoryname} (${c.sosanpham})`;
    $("category").appendChild(o);
  });

  customers.forEach((c) => {
    const o = document.createElement("option");
    o.value = c.customerid;
    o.textContent = `#${c.customerid} — ${c.fullname} (${c.province})`;
    $("customer").appendChild(o);
  });

  await loadProducts();
  await refreshFeed();
  await refreshStats();
  Tracker.track("page_view", { page: "/", referrer: document.referrer || "direct" });
}

// ------------------------------------------------------------------ san pham
async function loadProducts() {
  const params = new URLSearchParams();
  if ($("category").value) params.set("category_id", $("category").value);
  if ($("search").value.trim()) params.set("q", $("search").value.trim());
  params.set("limit", "24");

  products = await fetch("/api/products?" + params).then((r) => r.json());
  $("prod-count").textContent = `(${products.length})`;

  const grid = $("products");
  grid.innerHTML = "";
  products.forEach((p) => grid.appendChild(renderCard(p)));
}

function renderCard(p) {
  const stock = p.quantityonhand;
  const cls = stock === 0 ? "stock-out" : stock < 20 ? "stock-low" : "stock-ok";
  const el = document.createElement("div");
  el.className = "card";
  el.innerHTML = `
    <div class="name">${p.productname}</div>
    <div class="meta">${p.categoryname} · ${p.shopname}</div>
    <div class="meta">${p.sku}${p.color ? " · " + p.color : ""}${p.size ? " · " + p.size : ""}</div>
    <div class="price">${vnd(p.sellprice)}</div>
    <div class="meta">
      Tồn: <span class="${cls}">${stock}</span>
      ${p.avgrating > 0 ? ` · ★ ${p.avgrating}` : ""}
    </div>
    <div class="actions">
      <button data-act="view">Xem</button>
      <button data-act="cart" ${stock === 0 ? "disabled" : ""}>+ Giỏ</button>
    </div>`;

  el.querySelector('[data-act="view"]').onclick = (e) => {
    e.stopPropagation();
    Tracker.track("product_view", {
      product_id: p.productid, variant_id: p.variantid,
      dwell_seconds: Math.floor(Math.random() * 90) + 5,
      position_in_list: products.indexOf(p) + 1,
    });
  };

  el.querySelector('[data-act="cart"]').onclick = (e) => {
    e.stopPropagation();
    addToCart(p);
  };

  return el;
}

// ------------------------------------------------------------------ gio hang
function addToCart(p) {
  const found = cart.find((l) => l.variant_id === p.variantid);
  if (found) found.quantity += 1;
  else cart.push({
    variant_id: p.variantid, name: p.productname, sku: p.sku,
    unit_price: p.sellprice, quantity: 1, stock: p.quantityonhand,
  });

  Tracker.track("add_to_cart", {
    product_id: p.productid, variant_id: p.variantid, quantity: 1,
    price: p.sellprice,
  });
  renderCart();
}

function removeFromCart(variantId) {
  const line = cart.find((l) => l.variant_id === variantId);
  cart = cart.filter((l) => l.variant_id !== variantId);
  Tracker.track("remove_from_cart", { variant_id: variantId, quantity: line?.quantity });
  renderCart();
}

function renderCart() {
  const box = $("cart");
  if (!cart.length) {
    box.innerHTML = '<div class="muted" style="font-size:12px">Giỏ hàng trống</div>';
    return;
  }
  const total = cart.reduce((s, l) => s + l.unit_price * l.quantity, 0);
  box.innerHTML = cart.map((l) => `
    <div class="cart-line">
      <span>${l.name} <span class="muted">×${l.quantity}</span></span>
      <span>
        ${vnd(l.unit_price * l.quantity)}
        <button class="ghost" style="padding:1px 6px;margin-left:6px"
                onclick="removeFromCart(${l.variant_id})">×</button>
      </span>
    </div>`).join("")
    + `<div class="cart-line" style="border:0;font-weight:700">
         <span>Tổng</span><span>${vnd(total)}</span></div>`;
}

// ------------------------------------------------------------------ dat hang
async function checkout() {
  if (!cart.length) return;
  const customerId = $("customer").value;
  const box = $("order-result");

  if (!customerId) {
    box.innerHTML = '<div class="notice err">Chọn một khách hàng trước khi đặt hàng '
                  + '(đơn hàng bắt buộc có CustomerID — ràng buộc khóa ngoại).</div>';
    return;
  }

  const total = cart.reduce((s, l) => s + l.unit_price * l.quantity, 0);
  await Tracker.track("checkout_start", { cart_size: cart.length, cart_value: total });

  const res = await fetch("/api/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      customer_id: Number(customerId),
      ship_province: $("province").value,
      session_id: Tracker.sessionId,
      lines: cart.map((l) => ({
        variant_id: l.variant_id, quantity: l.quantity, unit_price: l.unit_price,
      })),
    }),
  });
  const data = await res.json();

  if (data.ok) {
    box.innerHTML = `<div class="notice ok">
      Đã tạo đơn <b>#${data.order_id}</b> — ${vnd(data.total)}.<br>
      Trigger <code>tr_orderdetail_tru_ton_kho</code> đã trừ tồn kho trong cùng transaction.
    </div>`;
    cart = [];
    renderCart();
    await loadProducts();       // tai lai de thay ton kho giam that
  } else {
    box.innerHTML = `<div class="notice err">
      <b>Giao dịch bị chặn (${data.kind})</b><br>
      <code style="font-size:11px">${data.error}</code><br>
      Toàn bộ đơn được rollback — không có dòng nào lọt vào CSDL.
    </div>`;
  }
  refreshStats();
  refreshFeed();
}

// ------------------------------------------------------------------ event feed
function prependEvent(ev, isNew = false) {
  const feed = $("feed");
  const el = document.createElement("div");
  el.className = "event" + (ev.source === "live_ui" ? " live" : "") + (isNew ? " new" : "");
  const t = new Date(ev.timestamp);
  el.innerHTML = `
    <div class="row1">
      <span class="type">${ev.event_type}</span>
      <span class="time">${t.toLocaleTimeString("vi-VN")}</span>
    </div>
    <div class="time">user: ${ev.user_id ?? "guest"} · ${ev.device?.platform ?? "-"}</div>
    <pre>${JSON.stringify(ev.payload ?? {})}</pre>`;
  feed.prepend(el);
  while (feed.children.length > 40) feed.lastChild.remove();
}

async function refreshFeed() {
  const only = $("only-live").checked;
  const events = await fetch(`/api/events/recent?limit=20&only_live=${only}`).then((r) => r.json());
  $("feed").innerHTML = "";
  events.forEach((e) => prependEvent(e));
}

async function refreshStats() {
  const s = await fetch("/api/events/stats").then((r) => r.json());
  $("ev-total").textContent = s.total.toLocaleString("vi-VN");
  $("ev-live").textContent = s.live.toLocaleString("vi-VN");
}

// ------------------------------------------------------------------ su kien UI
$("btn-checkout").onclick = checkout;
$("btn-refresh").onclick = refreshFeed;
$("only-live").onchange = refreshFeed;
$("category").onchange = () => {
  Tracker.track("search", { filters_applied: ["category"], category_id: $("category").value });
  loadProducts();
};
$("btn-search").onclick = () => {
  const q = $("search").value.trim();
  if (q) Tracker.track("search", { query: q, result_count: null });
  loadProducts();
};
$("search").onkeydown = (e) => { if (e.key === "Enter") $("btn-search").click(); };
$("customer").onchange = () => Tracker.setUser($("customer").value);

window.removeFromCart = removeFromCart;
init();
