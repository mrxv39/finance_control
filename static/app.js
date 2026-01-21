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

function escapeHtml(s) {
  return (s || "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

let categoriaTouched = false;
let conceptoTouched = false;
let notaTimer = null;
let lastSuggestedKey = "";

function setSugerenciaUI(text, show) {
  const box = $("sugerenciaBox");
  if (!box) return;
  box.style.display = show ? "block" : "none";
  box.textContent = show ? text : "";
}

async function sugerirDesdeNota() {
  const notaEl = $("nota");
  if (!notaEl) return;

  const nota = (notaEl.value || "").trim();
  if (nota.length < 3) {
    setSugerenciaUI("", false);
    lastSuggestedKey = "";
    return;
  }

  // Evita spamear si no cambia
  if (nota === lastSuggestedKey) return;
  lastSuggestedKey = nota;

  const url = new URL(location.origin + "/api/sugerir");
  url.searchParams.set("nota", nota);

  const r = await fetch(url.toString());
  const data = await r.json();

  const sug = data && data.sugerencia ? data.sugerencia : null;
  if (!sug) {
    setSugerenciaUI("Sin sugerencias para esta nota", true);
    return;
  }

  const sugText = `Sugerido: ${sug.categoria}${sug.concepto ? " · " + sug.concepto : ""} (x${sug.score})`;
  setSugerenciaUI(sugText, true);

  // Autorrelleno solo si el usuario no tocó manualmente
  if (!categoriaTouched && $("categoria")) {
    $("categoria").value = sug.categoria || "";
  }
  if (!conceptoTouched && $("concepto")) {
    $("concepto").value = sug.concepto || "";
  }
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
      <td>${escapeHtml(g.fecha)}</td>
      <td><span class="badge text-bg-secondary">${escapeHtml(g.categoria)}</span></td>
      <td class="text-muted">${escapeHtml(g.concepto || "")}</td>
      <td class="text-muted">${escapeHtml(g.nota || "")}</td>
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

  // Reset flags al iniciar
  categoriaTouched = false;
  conceptoTouched = false;

  // Si el usuario toca manualmente categoría/concepto, no sobreescribimos
  if ($("categoria")) {
    $("categoria").addEventListener("input", () => { categoriaTouched = true; });
  }
  if ($("concepto")) {
    $("concepto").addEventListener("input", () => { conceptoTouched = true; });
  }

  // Debounce de sugerencias desde nota
  if ($("nota")) {
    $("nota").addEventListener("input", () => {
      clearTimeout(notaTimer);
      notaTimer = setTimeout(() => {
        sugerirDesdeNota().catch(() => {});
      }, 350);
    });
  }
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
    concepto: $("concepto") ? $("concepto").value : "",
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
  if ($("concepto")) $("concepto").value = "";

  // Tras guardar, permitimos sugerir de nuevo sin “bloqueo”
  categoriaTouched = false;
  conceptoTouched = false;
  setSugerenciaUI("", false);
  lastSuggestedKey = "";

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
