

(function () {
  const App = (window.App = window.App || {});

  App.$ = (id) => document.getElementById(id);

  App.money = function money(v) {
    return Number(v).toFixed(2);
  };

  App.showError = function showError(msg) {
    const box = App.$("errorBox");
    if (!box) return;
    box.style.display = msg ? "block" : "none";
    box.textContent = msg || "";
  };

  App.currentMonth = function currentMonth() {
    const d = new Date();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    return `${d.getFullYear()}-${mm}`;
  };

  App.escapeHtml = function escapeHtml(s) {
    return (s || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  };
})();
