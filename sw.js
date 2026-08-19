/* Baba Catalogue 2026 — service worker.
   The app is one large self-contained HTML file, so "the app shell" is
   effectively index.html plus the icons. Strategy:
     - navigations: cache-first, falling back to network, then to cached index
     - everything else in scope: cache-first with background fill
   Bump CACHE_VERSION whenever index.html is re-deployed. */

const CACHE_VERSION = '2026-0819-8';
const CACHE = 'baba-catalogue-' + CACHE_VERSION;

const PRECACHE = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-512.png',
  './apple-touch-icon.png',
  './favicon-32.png',
  './favicon-16.png',
  './favicon.ico'
];

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    // Add individually: one 404 (e.g. a missing icon) must not fail the whole install.
    await Promise.all(PRECACHE.map(async url => {
      try { await cache.add(new Request(url, { cache: 'reload' })); }
      catch (e) { console.warn('[sw] skipped', url, e.message); }
    }));
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map(k => (k.startsWith('baba-catalogue-') && k !== CACHE)
      ? caches.delete(k) : Promise.resolve()));
    await self.clients.claim();
  })());
});

// Lets the page trigger an immediate update instead of waiting for all tabs to close.
self.addEventListener('message', event => {
  if (event.data === 'skipWaiting') self.skipWaiting();
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;   // leave cross-origin alone

  if (req.mode === 'navigate') {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const cached = await cache.match('./index.html');
      if (cached) {
        // Serve instantly, refresh in the background for next launch.
        event.waitUntil((async () => {
          try {
            const fresh = await fetch('./index.html', { cache: 'reload' });
            if (fresh && fresh.ok) await cache.put('./index.html', fresh.clone());
          } catch (e) {}
        })());
        return cached;
      }
      try {
        const res = await fetch(req);
        if (res && res.ok) cache.put('./index.html', res.clone());
        return res;
      } catch (e) {
        return cached || Response.error();
      }
    })());
    return;
  }

  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(req, { ignoreSearch: true });
    if (cached) return cached;
    try {
      const res = await fetch(req);
      if (res && res.ok && res.type === 'basic') cache.put(req, res.clone());
      return res;
    } catch (e) {
      return cached || Response.error();
    }
  })());
});
