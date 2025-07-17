const CACHE_NAME = 'version-history-cache-v1';
const urlsToCache = [
  '/static/version_history.html',
  '/static/manifest.json',
  // Add icons and other assets as needed
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
}); 