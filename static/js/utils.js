export const $ = (id) => document.getElementById(id);

export function money(v) {
  const n = Number(v);
  if (Number.isNaN(n)) return "0.00";
  return n.toFixed(2);
}

export function currentMonth() {
  const d = new Date();
  const mm
