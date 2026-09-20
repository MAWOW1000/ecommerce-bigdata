/** Dashboard: goi 10 view/procedure ben PostgreSQL va pheu chuyen doi ben MongoDB. */

const $ = (id) => document.getElementById(id);

const fmt = (v) => {
  if (v === null || v === undefined) return '<span class="muted">–</span>';
  if (typeof v === "number") {
    return Number.isInteger(v)
      ? v.toLocaleString("vi-VN")
      : v.toLocaleString("vi-VN", { maximumFractionDigits: 2 });
  }
  return String(v);
};

async function loadFunnel() {
  const data = await fetch("/api/analytics/mongo/funnel").then((r) => r.json());
  const max = Math.max(...data.steps.map((s) => s.sessions), 1);
  $("funnel").innerHTML = data.steps.map((s) => `
    <div class="funnel-row">
      <span>${s.step}</span>
      <div class="funnel-bar" style="width:${(s.sessions / max) * 100}%"></div>
      <span class="num">${s.sessions.toLocaleString("vi-VN")} phiên
        <span class="muted">(${s.conversion_pct}%)</span></span>
    </div>`).join("");
}

async function runQuery(code, btn) {
  document.querySelectorAll("#yc-buttons button").forEach((b) => b.classList.remove("primary"));
  btn?.classList.add("primary");

  $("result-title").textContent = "Đang chạy...";
  const data = await fetch(`/api/analytics/${code}?limit=200`).then((r) => r.json());

  $("result-title").innerHTML =
    `${data.code} — ${data.title} <span class="muted">(${data.row_count} dòng)</span>`;

  const table = $("result-table");
  if (!data.rows.length) { table.innerHTML = "<tr><td>Không có dữ liệu</td></tr>"; return; }

  const cols = Object.keys(data.rows[0]);
  const isNum = (c) => data.rows.every((r) => r[c] === null || typeof r[c] === "number");

  table.innerHTML =
    "<thead><tr>" + cols.map((c) => `<th class="${isNum(c) ? "num" : ""}">${c}</th>`).join("") +
    "</tr></thead><tbody>" +
    data.rows.map((r) =>
      "<tr>" + cols.map((c) => `<td class="${isNum(c) ? "num" : ""}">${fmt(r[c])}</td>`).join("") + "</tr>"
    ).join("") + "</tbody>";
}

async function init() {
  const catalog = await fetch("/api/analytics/catalog").then((r) => r.json());
  const box = $("yc-buttons");
  catalog.forEach((item, i) => {
    const b = document.createElement("button");
    b.textContent = `${item.code} · ${item.title}`;
    b.title = item.view;
    b.onclick = () => runQuery(item.code, b);
    box.appendChild(b);
    if (i === 0) setTimeout(() => b.click(), 0);
  });
  loadFunnel();
}

init();
