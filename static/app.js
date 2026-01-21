

(function () {
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.defer = true;
      s.onload = resolve;
      s.onerror = reject;
      document.head.appendChild(s);
    });
  }

  async function boot() {
    await loadScript("/static/js/app_core.js");
    await loadScript("/static/js/app_sugerencias.js");
    await loadScript("/static/js/app_combo_cat.js");
    await loadScript("/static/js/app_gastos.js");

    if (window.App && typeof window.App.start === "function") {
      window.App.start();
    }
  }

  function bootWhenReady() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", () => {
        boot().catch(() => {});
      });
      return;
    }
    boot().catch(() => {});
  }

  bootWhenReady();
})();
