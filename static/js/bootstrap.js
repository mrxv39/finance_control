import { $, currentMonth, showError } from "./utils.js";
import { apiGetResumen, apiGetGastos, apiPostGasto } from "./api.js";
import { renderResumen, renderGastosTable } from "./gastos_ui.js";
import { initNotaSuggestions } from "./suggest_nota.js";

async function cargar() {
  const mes = $("mesFiltro").value || currentMonth();
  const categoria = $("catFiltro").value || "";
  const q = ($("qFiltro").value || "").trim();

  const resumen = await apiGetResumen(mes);
  renderResumen(resumen);

  const gastos = await apiGetGastos({ mes, categoria, q });
  renderGastosTable(gastos, cargar);
}

function initDefaults() {
  $("fecha").value = new Date().toISOString().slice(0, 10);
  $("mesFiltro").value = currentMonth();

  $("btnHoy").addEventListener("click", () => {
    $("fecha").value = new Date().toISOString().slice(0, 10);
  });

  $("btnRefrescar").addEventListener("click", (e) => {
    e.preventDefault();
    cargar().catch(err => showError(err.message || "Error"));
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

    try {
      await apiPostGasto(payload);
      $("importe").value = "";
      $("nota").value = "";
      if ($("concepto")) $("concepto").value = "";
      await cargar();
    } catch (err) {
      showError(err.message || "Error al guardar");
    }
  });

  // Sugerencias por prefijo de nota
  initNotaSuggestions();
}

export function initApp() {
  initDefaults();
  cargar().catch(err => showError(err.message || "Error"));
}
