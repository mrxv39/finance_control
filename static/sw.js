/* Service Worker - PWA Gastos
   Objetivo: cachear SOLO assets estáticos y NO cachear HTML (/) para que el login/redirect funcione siempre.
*/

const CACHE_NAME = "gastos-static-v3"; // sube este número si haces cambios para forzar actualización
const ASSETS_TO_CACHE = [
  "/static/style.css",
  "/static/app.js",
  "/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      // limpia caches antiguos
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((k) => k.startsWith("gastos-static-") && k !== CACHE_NAME)
          .map((k) => caches.delete(k))
      );
      await self.clients.claim();
    })()
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);

  // 1) NO cachear navegación/HTML (incluye "/")
  // Esto evita que el SW sirva una home cacheada sin redirección a /login.
  if (req.mode === "navigate") {
    event.respondWith(fetch(req));
    return;
  }

  // 2) NO cachear /api (siempre red)
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(fetch(req));
    return;
  }

  // 3) Cache-first para assets
  event.respondWith(
    caches.match(req).then((cached) => cached || fetch(req))
  );
});
