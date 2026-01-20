const $ = (id) => document.getElementById(id);

function money(v) {
  return Number(v).toFixed(2);
}

function showError(msg) {
  const box = $("errorBox");
  box.style.display = msg ? "block" : "none";
  box.textContent = msg || "";
}

function currentMonth() {
  const d = new Date();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${d.getFullYear()}-${mm}`;
}

async function cargar() {
  const mes = $("mesFiltro").value || currentMonth();
  const categoria = $("catFiltro").value;
  const q = $("qFiltro").value.trim();

  const r = await fetch(`/api/resumen?mes=${encodeURIComponent(mes)}`);
  const resumen = await r.json();
  $("totalMes").textContent = money(resumen.total);

  const porCat = (resumen.por_categoria || [])
    .slice(0, 4)
    .map(x => `${x.categoria}: ${money(x.total)}`)
    .join(" · ");
  $("porCategoria").textContent = porCat;

  const url = new URL(location.origin + "/api/gastos");
  url.searchParams.set("mes", mes);
  if (categoria) url.searchParams.set("categoria", categoria);
  if (q) url.searchParams.set("q", q);

  const rr = await fetch(url.toString());
  const gastos = await rr.json();

  $("countBox").textContent = `(${gastos.length})`;

  const tbody = $("tbody");
  tbody.innerHTML = "";
  for (const g of gastos) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${g.fecha}</td>
      <td><span class="badge text-bg-secondary">${g.categoria}</span></td>
      <td class="text-muted">${(g.nota || "").replaceAll("<","&lt;")}</td>
      <td class="text-end fw-semibold">${money(g.importe)}</td>
      <td class="text-end">
        <button class="btn btn-sm btn-outline-danger" data-del="${g.id}">✕</button>
      </td>
    `;
    tbody.appendChild(tr);
  }

  tbody.querySelectorAll("[data-del]").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.getAttribute("data-del");
      await fetch(`/api/gastos/${id}`, { method: "DELETE" });
      cargar();
    });
  });
}

function initDefaults() {
  $("fecha").value = new Date().toISOString().slice(0, 10);
  $("mesFiltro").value = currentMonth();
}

$("btnHoy").addEventListener("click", () => {
  $("fecha").value = new Date().toISOString().slice(0, 10);
});

$("btnRefrescar").addEventListener("click", (e) => {
  e.preventDefault();
  cargar();
});

$("formGasto").addEventListener("submit", async (e) => {
  e.preventDefault();
  showError("");

  const payload = {
    importe: $("importe").value,
    categoria: $("categoria").value,
    fecha: $("fecha").value,
    nota: $("nota").value
  };

  const res = await fetch("/api/gastos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showError(err.error || "Error al guardar");
    return;
  }

  $("importe").value = "";
  $("nota").value = "";
  await cargar();
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").then(() => {
    $("pwaStatus").textContent = "PWA";
    $("pwaStatus").className = "badge text-bg-success";
  }).catch(() => {
    $("pwaStatus").textContent = "Web";
  });
}

initDefaults();
cargar();
