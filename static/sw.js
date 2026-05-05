const CACHE = 'company-research-v1';

// Pre-cache the app shell on install
self.addEventListener('install', evt => {
  self.skipWaiting();
  evt.waitUntil(
    caches.open(CACHE).then(c => c.addAll(['/', '/history']))
  );
});

// Remove old caches on activation
self.addEventListener('activate', evt => {
  evt.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys.filter(k => k !== CACHE).map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

// Network-first for all GETs; fall back to cache when offline
self.addEventListener('fetch', evt => {
  if (evt.request.method !== 'GET') return;

  evt.respondWith(
    fetch(evt.request)
      .then(res => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(evt.request, copy));
        }
        return res;
      })
      .catch(() => caches.match(evt.request))
  );
});
