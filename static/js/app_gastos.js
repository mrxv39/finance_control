
(function () {
  const App = (window.App = window.App || {});

  App.cargar = async function cargar() {
    const mes = App.$("mesFiltro").value || App.currentMonth();
    const categoria = App.$("catFiltro").value;
    const q = App.$("qFiltro").value.trim();

    const r = await fetch(`/api/resumen?mes=${encodeURIComponent(mes)}`);
    const resumen = await r.json();
    App.$("totalMes").textContent = App.money(resumen.total);

    const porCat = (resumen.por_categoria || [])
      .slice(0, 4)
      .map(x => `${x.categoria}: ${App.money(x.total)}`)
      .join(" · ");
    App.$("porCategoria").textContent = porCat;

    const url = new URL(location.origin + "/api/gastos");
    url.searchParams.set("mes", mes);
    if (categoria) url.searchParams.set("categoria", categoria);
    if (q) url.searchParams.set("q", q);

    const rr = await fetch(url.toString());
    const gastos = await rr.json();

    App.$("countBox").textContent = `(${gastos.length})`;

    const tbody = App.$("tbody");
    tbody.innerHTML = "";
    for (const g of gastos) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${App.escapeHtml(g.fecha)}</td>
        <td><span class="badge text-bg-secondary">${App.escapeHtml(g.categoria)}</span></td>
        <td class="text-muted">${App.escapeHtml(g.concepto || "")}</td>
        <td class="text-muted">${App.escapeHtml(g.nota || "")}</td>
        <td class="text-end fw-semibold">${App.money(g.importe)}</td>
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
        App.cargar();
      });
    });
  };

  App.initDefaults = function initDefaults() {
    App.$("fecha").value = new Date().toISOString().slice(0, 10);
    App.$("mesFiltro").value = App.currentMonth();

    App._state.categoriaTouched = false;
    App._state.conceptoTouched = false;

    if (App.$("categoria")) {
      App.$("categoria").addEventListener("input", () => { App._state.categoriaTouched = true; });
    }
    if (App.$("concepto")) {
      App.$("concepto").addEventListener("input", () => { App._state.conceptoTouched = true; });
    }

    if (App.$("nota")) {
      App.$("nota").addEventListener("input", () => {
        clearTimeout(App._state.notaTimer);
        App._state.notaTimer = setTimeout(() => {
          App.sugerirDesdeNota().catch(() => {});
        }, 350);
      });
    }
  };

  App.bindUI = function bindUI() {
    App.$("btnHoy").addEventListener("click", () => {
      App.$("fecha").value = new Date().toISOString().slice(0, 10);
    });

    App.$("btnRefrescar").addEventListener("click", (e) => {
      e.preventDefault();
      App.cargar();
    });

    App.$("formGasto").addEventListener("submit", async (e) => {
      e.preventDefault();
      App.showError("");

      const payload = {
        importe: App.$("importe").value,
        categoria: App.$("categoria").value,
        concepto: App.$("concepto") ? App.$("concepto").value : "",
        fecha: App.$("fecha").value,
        nota: App.$("nota").value
      };

      const res = await fetch("/api/gastos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        App.showError(err.error || "Error al guardar");
        return;
      }

      App.$("importe").value = "";
      App.$("nota").value = "";
      if (App.$("concepto")) App.$("concepto").value = "";

      App._state.categoriaTouched = false;
      App._state.conceptoTouched = false;
      App.setSugerenciaUI("", false);
      App._state.lastSuggestedKey = "";

      await App.cargar();
    });

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").then(() => {
        App.$("pwaStatus").textContent = "PWA";
        App.$("pwaStatus").className = "badge text-bg-success";
      }).catch(() => {
        App.$("pwaStatus").textContent = "Web";
      });
    }
  };

  App.start = async function start() {
    App.initDefaults();
    await App.initCategoriaSubcategoriaCombos().catch(() => {});
    App.bindUI();
    App.cargar();
  };
})();
