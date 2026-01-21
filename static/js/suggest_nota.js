export async function apiGetResumen(mes) {
  const r = await fetch(`/api/resumen?mes=${encodeURIComponent(mes)}`);
  if (!r.ok) throw new Error("Error leyendo resumen");
  return await r.json();
}

export async function apiGetGastos({ mes, categoria, q }) {
  const url = new URL(location.origin + "/api/gastos");
  url.searchParams.set("mes", mes);
  if (categoria) url.searchParams.set("categoria", categoria);
  if (q) url.searchParams.set("q", q);

  const r = await fetch(url.toString());
  if (!r.ok) throw new Error("Error leyendo gastos");
  return await r.json();
}

export async function apiPostGasto(payload) {
  const r = await fetch("/api/gastos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.error || "Error al guardar");
  }
  return await r.json().catch(() => ({}));
}

export async function apiDeleteGasto(id) {
  const r = await fetch(`/api/gastos/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error("Error borrando gasto");
  return await r.json().catch(() => ({}));
}

/**
 * Prefijo de nota: "l" => sugiere notas que empiezan por "l"
 * Endpoint: /api/sugerir_nota?pref=...
 */
export async function apiSugerirNota(pref) {
  const r = await fetch(`/api/sugerir_nota?pref=${encodeURIComponent(pref)}`);
  if (!r.ok) throw new Error("Error en sugerencias de nota");
  return await r.json();
}
