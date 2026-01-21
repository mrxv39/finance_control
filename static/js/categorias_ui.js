import { apiGet } from "./api.js";

function qs(sel, root = document) { return root.querySelector(sel); }

function ensureWrapper(input, key) {
  let wrap = input.closest(".combo-wrap");
  if (wrap) return wrap;

  wrap = document.createElement("div");
  wrap.className = "combo-wrap";
  input.parentNode.insertBefore(wrap, input);
  wrap.appendChild(input);

  const panel = document.createElement("div");
  panel.className = "combo-panel";
  panel.dataset.key = key;
  panel.hidden = true;
  wrap.appendChild(panel);

  return wrap;
}

function renderOptions(panel, items, onPick) {
  panel.innerHTML = "";
  if (!items.length) {
    const empty = document.createElement("div");
    empty.className = "combo-empty";
    empty.textContent = "Sin resultados";
    panel.appendChild(empty);
    return;
  }

  for (const it of items) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "combo-item";
    btn.textContent = it.label;
    btn.addEventListener("click", () => onPick(it));
    panel.appendChild(btn);
  }
}

function openPanel(panel) { panel.hidden = false; }
function closePanel(panel) { panel.hidden = true; }

function normalize(s) { return (s || "").toString().trim(); }
function contains(hay, needle) { return hay.toLowerCase().includes(needle.toLowerCase()); }

export async function initCategoriasUI() {
  const catInput = qs('input[name="categoria"]');
  const subInput = qs('input[name="subcategoria"]');

  // Si aún no existe subcategoria en tu HTML, no hacemos nada.
  if (!catInput || !subInput) return;

  const catWrap = ensureWrapper(catInput, "categoria");
  const subWrap = ensureWrapper(subInput, "subcategoria");

  const catPanel = qs(".combo-panel[data-key='categoria']", catWrap);
  const subPanel = qs(".combo-panel[data-key='subcategoria']", subWrap);

  // 1) Prefetch catálogo (mezcla base + BD)
  let catalog = [];
  try {
    catalog = await apiGet("/api/categorias");
  } catch (e) {
    catalog = [];
  }

  function uniqueCats(list) {
    const seen = new Set();
    const out = [];
    for (const x of list) {
      const c = normalize(x.categoria);
      if (!c || seen.has(c)) continue;
      seen.add(c);
      out.push({ label: c, value: c, n: x.n || 0 });
    }
    out.sort((a,b) => (b.n - a.n) || a.label.localeCompare(b.label));
    return out.slice(0, 50);
  }

  function subsForCat(cat) {
    const out = [];
    for (const x of catalog) {
      const c = normalize(x.categoria);
      const s = normalize(x.subcategoria);
      if (!c || !s) continue;
      if (c !== cat) continue;
      out.push({ label: s, value: s, n: x.n || 0 });
    }
    out.sort((a,b) => (b.n - a.n) || a.label.localeCompare(b.label));
    return out.slice(0, 80);
  }

  function filterCats(q) {
    const all = uniqueCats(catalog);
    if (!q) return all;
    return all.filter(x => contains(x.label, q)).slice(0, 50);
  }

  function filterSubs(cat, q) {
    const all = subsForCat(cat);
    if (!q) return all;
    return all.filter(x => contains(x.label, q)).slice(0, 80);
  }

  function pickCategoria(it) {
    catInput.value = it.value;
    closePanel(catPanel);

    // reset subcategoria si no pertenece
    const curSub = normalize(subInput.value);
    const validSubs = new Set(subsForCat(it.value).map(x => x.value));
    if (curSub && !validSubs.has(curSub)) subInput.value = "";
    subInput.focus();
  }

  function pickSubcategoria(it) {
    subInput.value = it.value;
    closePanel(subPanel);
  }

  catInput.addEventListener("focus", () => {
    renderOptions(catPanel, filterCats(catInput.value), pickCategoria);
    openPanel(catPanel);
  });

  catInput.addEventListener("input", () => {
    renderOptions(catPanel, filterCats(catInput.value), pickCategoria);
    openPanel(catPanel);
  });

  subInput.addEventListener("focus", () => {
    const cat = normalize(catInput.value);
    renderOptions(subPanel, filterSubs(cat, subInput.value), pickSubcategoria);
    openPanel(subPanel);
  });

  subInput.addEventListener("input", () => {
    const cat = normalize(catInput.value);
    renderOptions(subPanel, filterSubs(cat, subInput.value), pickSubcategoria);
    openPanel(subPanel);
  });

  document.addEventListener("click", (ev) => {
    if (!catWrap.contains(ev.target)) closePanel(catPanel);
    if (!subWrap.contains(ev.target)) closePanel(subPanel);
  });

  // UX: al cambiar categoria manualmente, refresca sub
  catInput.addEventListener("blur", () => {
    const cat = normalize(catInput.value);
    if (!cat) return;
    const valid = new Set(subsForCat(cat).map(x => x.value));
    const curSub = normalize(subInput.value);
    if (curSub && !valid.has(curSub)) subInput.value = "";
  });
}
