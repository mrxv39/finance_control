import { $, money, escapeHtml } from "./utils.js";
import { apiDeleteGasto } from "./api.js";

export function renderResumen(resumen) {
  $("totalMes").textContent = money(resumen.total || 0);

  const porCat = (resumen.por_categoria || [])
    .slice(0, 4)
    .map(x => `${x.categoria}: ${money(x.total)}`)
    .join(" · ");

  $("porCategoria").textContent = porCat || "-";
}

export function renderGastosTable(gastos, onReload) {
  $("countBox").textContent = `(${gastos.length})`;

  const tbody = $("tbody");
  tbody.innerHTML = "";

  for (const g of gastos) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td style="padding:10px; border-bottom:1px solid rgba(15,23,42,.06);">${escapeHtml(g.fecha)}</td>
      <td style="padding:10px; border-bottom:1px solid rgba(15,23,42,.06);">
        <span class="badge text-bg-secondary">${escapeHtml(g.categoria)}</span>
      </td>
      <td style="padding:10px; border-bottom:1px solid rgba(15,23,42,.06);" class="text-muted">${escapeHtml(g.concepto || "")}</td>
      <td style="padding:10
