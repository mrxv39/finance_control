(function () {
  const App = (window.App = window.App || {});

  App._state = App._state || {};
  App._state.categoriaTouched = false;
  App._state.conceptoTouched = false;
  App._state.notaTimer = null;
  App._state.lastSuggestedKey = "";

  App.setSugerenciaUI = function setSugerenciaUI(text, show) {
    const box = App.$("sugerenciaBox");
    if (!box) return;
    box.style.display = show ? "block" : "none";
    box.textContent = show ? text : "";
  };

  App.sugerirDesdeNota = async function sugerirDesdeNota() {
    const notaEl = App.$("nota");
    if (!notaEl) return;

    const nota = (notaEl.value || "").trim();
    if (nota.length < 3) {
      App.setSugerenciaUI("", false);
      App._state.lastSuggestedKey = "";
      return;
    }

    if (nota === App._state.lastSuggestedKey) return;
    App._state.lastSuggestedKey = nota;

    const url = new URL(location.origin + "/api/sugerir");
    url.searchParams.set("nota", nota);

    const r = await fetch(url.toString());
    const data = await r.json();

    const sug = data && data.sugerencia ? data.sugerencia : null;
    if (!sug) {
      App.setSugerenciaUI("Sin sugerencias para esta nota", true);
      return;
    }

    const sugText = `Sugerido: ${sug.categoria}${sug.concepto ? " · " + sug.concepto : ""} (x${sug.score})`;
    App.setSugerenciaUI(sugText, true);

    if (!App._state.categoriaTouched && App.$("categoria")) {
      App.$("categoria").value = sug.categoria || "";
    }
    if (!App._state.conceptoTouched && App.$("concepto")) {
      App.$("concepto").value = sug.concepto || "";
    }
  };
})();
