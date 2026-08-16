const CACHE_NAME = "powerful-notes-shell-v2";
const SHELL_ASSETS = [
  "/static/style.css",
  "/static/app.js",
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Only ever touch static assets (CSS/JS/icons/manifest); everything else
// (pages, /api/*) always goes straight to the network, since it may contain
// authenticated, per-account client data that must never be cached.
//
// Network-first: always try for the latest version of the file so a deployed
// update is picked up immediately, falling back to the cached copy only when
// the network is unavailable (the actual offline use case).
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  const isStaticAsset = event.request.method === "GET" && SHELL_ASSETS.includes(url.pathname);

  if (!isStaticAsset) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});
