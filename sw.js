// Minimal service worker: makes the dashboard installable as a PWA and
// lets it open offline (showing the last-cached reading) if there's no
// connection. Deliberately no full offline-first app — this is a live
// dashboard, so data/ files are always fetched from the network first.
const CACHE = "ecoflow-dashboard-v1";
const APP_SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);
  const isData = url.pathname.includes("/data/");

  if (isData) {
    // Network-first: always prefer a fresh chart/CSV, cache it for
    // offline viewing, fall back to whatever was last cached. index.html
    // cache-busts these requests with a ?t= query param, so cache under
    // the bare path (ignoring the query) or every load would miss.
    const cacheKey = new Request(url.origin + url.pathname);
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(cacheKey, copy));
          return response;
        })
        .catch(() => caches.match(cacheKey))
    );
    return;
  }

  // App shell: cache-first, network as fallback.
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
