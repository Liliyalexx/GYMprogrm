const CACHE = 'gymprogrm-v1';
const PRECACHE = [
  '/portal/',
  '/portal/program/',
  '/portal/history/',
  '/portal/billing/',
  '/portal/recommendations/',
];

self.addEventListener('install', function(e) {
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE).then(function(cache) {
      return cache.addAll(PRECACHE).catch(function() {});
    })
  );
});

self.addEventListener('activate', function(e) {
  self.clients.claim();
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE; }).map(function(k) { return caches.delete(k); })
      );
    })
  );
});

self.addEventListener('fetch', function(e) {
  if (e.request.method !== 'GET') return;
  var url = new URL(e.request.url);
  if (url.origin !== location.origin) return;

  e.respondWith(
    fetch(e.request)
      .then(function(res) {
        if (res.ok) {
          var clone = res.clone();
          caches.open(CACHE).then(function(c) { c.put(e.request, clone); });
        }
        return res;
      })
      .catch(function() {
        return caches.match(e.request);
      })
  );
});
