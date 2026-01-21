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

let CATS = [];              // [{id,nombre,subcategorias:[{id,nombre}]}]
let SUBS_BY_CAT = new Map(); // nombreCategoria -> [subcats]

function setSelectOptions(selectEl, options, placeholderText) {
  selectEl.innerHTML = "";
  const opt0 = document.createElement("option");
  opt0.value = "";
  opt0.textContent = placeholderText || "(Selecciona)";
  selectEl.appendChild(opt0);

  for (const txt of options) {
    const opt = document.createElement("option");
    opt.value = txt;
    opt.textContent = txt;
    selectEl.appendChild(opt);
  }
}

async function cargarCategorias() {
  // Endpoint creado en gastos_api.py: GET /api/categorias
  const r = await fetch("/api/categorias");
  const data = await r.json();

  CATS = Array.isArray(data) ? data : [];
  SUBS_BY_CAT = new Map();

  const catNames = CATS.map(c => c.nombre).sort((a,b) => a.localeCompare(b));

  for (const c of CATS) {
    const subs = (c.subcategorias || []).map(s => s.nombre);
    SUBS_BY_CAT.set(c.nombre, subs.sort((a,b)=>a.localeCompare(b)));
  }

  // Select del formulario (categoria/subcategoria)
  setSelectOptions($("categoria"), catNames, "(Selecciona)");
  setSelectOptions($("subcategoria"), [], "(Opcional)");

  // Select del filtro de categoría (catFiltro)
  setSelectOptions($("catFiltro"), catNames, "(Todas)");

  // Cuando cambia categoría en el formulario -> recargar subcategorías
  $("categoria").addEventListener("change", () => {
    const cat = $("categoria").value;
    const subs = SUBS_BY_CAT.get(cat) || [];
    setSelectOptions($("subcategoria"), subs, "(Opcional)");
  });

  // Cuando cambia filtro categoría -> recargar lista
  $("catFiltro").addEventListener("change", () => {
    cargar().catch(() => {});
  });
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
    subcategoria: $("subcategoria").value, // opcional
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
  // mantenemos categoría y subcategoría seleccionadas para meter varios gastos rápido
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

(async () => {
  initDefaults();
  await cargarCategorias();
  await cargar();
})();
