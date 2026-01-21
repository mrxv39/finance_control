
(function () {
  const App = (window.App = window.App || {});

  function norm(s) {
    return (s || "").toString().trim();
  }
  function contains(h, n) {
    return h.toLowerCase().includes(n.toLowerCase());
  }

  function byIdAny(ids) {
    for (const id of ids) {
      const el = document.getElementById(id);
      if (el) return el;
    }
    return null;
  }

  function ensureCombo(inputEl, key) {
    if (!inputEl) return null;

    let wrap = inputEl.closest(".combo-wrap");
    if (wrap) {
      return { wrap, panel: wrap.querySelector(`.combo-panel[data-key="${key}"]`) };
    }

    wrap = document.createElement("div");
    wrap.className = "combo-wrap";
    wrap.style.position = "relative";

    inputEl.parentNode.insertBefore(wrap, inputEl);
    wrap.appendChild(inputEl);

    const panel = document.createElement("div");
    panel.className = "combo-panel";
    panel.dataset.key = key;

    panel.style.display = "none";
    panel.style.position = "absolute";
    panel.style.zIndex = "9999";
    panel.style.left = "0";
    panel.style.right = "0";
    panel.style.marginTop = "4px";
    panel.style.maxHeight = "240px";
    panel.style.overflow = "auto";
    panel.style.background = "#fff";
    panel.style.color = "#111";
    panel.style.border = "1px solid rgba(0,0,0,0.15)";
    panel.style.borderRadius = "10px";
    panel.style.padding = "6px";
    panel.style.boxShadow = "0 10px 30px rgba(0,0,0,0.12)";

    wrap.appendChild(panel);
    return { wrap, panel };
  }

  function openPanel(panel) { if (panel) panel.style.display = "block"; }
  function closePanel(panel) { if (panel) panel.style.display = "none"; }

  function renderPanel(panel, items, onPick) {
    panel.innerHTML = "";
    if (!items.length) {
      const d = document.createElement("div");
      d.textContent = "Sin resultados";
      d.style.padding = "8px";
      d.style.opacity = "0.7";
      panel.appendChild(d);
      return;
    }

    for (const it of items) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = it.label;
      b.style.display = "block";
      b.style.width = "100%";
      b.style.textAlign = "left";
      b.style.padding = "8px";
      b.style.border = "0";
      b.style.background = "transparent";
      b.style.cursor = "pointer";
      b.onclick = () => onPick(it);
      panel.appendChild(b);
    }
  }

  let catalog = [];
  let loaded = false;

  async function loadCatalogOnce() {
    if (loaded) return;
    loaded = true;
    const r = await fetch("/api/categorias", { cache: "no-store" });
    catalog = r.ok ? await r.json() : [];
  }

  function uniqueCategorias() {
    const m = new Map();
    for (const x of catalog) {
      const c = norm(x.categoria);
      if (!c) continue;
      const n = Number(x.n || 0);
      m.set(c, Math.max(m.get(c) || 0, n));
    }
    return [...m.entries()]
      .map(([c, n]) => ({ label: c, value: c, n }))
      .sort((a, b) => b.n - a.n || a.label.localeCompare(b.label));
  }

  function todasSubcategorias() {
    const out = [];
    const seen = new Set();
    for (const x of catalog) {
      const s = norm(x.subcategoria);
      if (!s || seen.has(s)) continue;
      seen.add(s);
      out.push({ label: s, value: s, n: Number(x.n || 0) });
    }
    return out.sort((a, b) => b.n - a.n || a.label.localeCompare(b.label));
  }

  function subcategoriasPara(cat) {
    return catalog
      .filter(x => norm(x.categoria) === cat && norm(x.subcategoria))
      .map(x => ({ label: x.subcategoria, value: x.subcategoria, n: Number(x.n || 0) }));
  }

  function filterCats(q) {
    const all = uniqueCategorias();
    return q ? all.filter(x => contains(x.label, q)) : all;
  }

  function filterSubs(cat, q) {
    const all = cat ? subcategoriasPara(cat) : todasSubcategorias();
    return q ? all.filter(x => contains(x.label, q)) : all;
  }

  App.initCategoriaSubcategoriaCombos = async function () {
    const catEl = byIdAny(["categoria"]);
    const subEl = byIdAny(["concepto"]);
    if (!catEl || !subEl) return;

    const catCombo = ensureCombo(catEl, "categoria");
    const subCombo = ensureCombo(subEl, "subcategoria");

    await loadCatalogOnce();

    catEl.onfocus = () => {
      renderPanel(catCombo.panel, filterCats(catEl.value), it => {
        catEl.value = it.value;
        closePanel(catCombo.panel);
        subEl.focus();
      });
      openPanel(catCombo.panel);
    };
    catEl.oninput = catEl.onfocus;

    subEl.onfocus = () => {
      renderPanel(
        subCombo.panel,
        filterSubs(norm(catEl.value), subEl.value),
        it => {
          subEl.value = it.value;
          closePanel(subCombo.panel);
        }
      );
      openPanel(subCombo.panel);
    };
    subEl.oninput = subEl.onfocus;
  };

  document.addEventListener("DOMContentLoaded", () => {
    App.initCategoriaSubcategoriaCombos();
  });
})();
