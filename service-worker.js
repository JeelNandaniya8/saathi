const CACHE_NAME = "saathi-shell-v17";
const APP_SHELL = [
  "/", "/privacy", "/terms",
  "/limitations", "/support", "/offline.html", "/manifest.webmanifest",
  "/saathi-icon.svg", "/public.css", "/theme.js?v=20260915", "/site-theme.css?v=20260915"
];

// Pages we never want to cache (auth/account pages)
const NO_CACHE_PATHS = ["/account", "/api/"];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

// Keep reminder details inside the signed-in workspace, including on lock screens.
self.addEventListener('push', event => {
  let payload={};
  try{payload=event.data?.json()||{}}catch(_){}
  const digest=payload.kind==='digest';
  const tag=/^(?:saathi-reminder-\d+-\d+|saathi-digest-\d{4}-\d{2}-\d{2})$/.test(payload.tag||'')?payload.tag:'saathi-reminder';
  event.waitUntil(self.registration.showNotification(digest?'Your Saathi summary':'Saathi reminder',{
    body:digest?'Your scheduled reminders are ready to review. Open Saathi when it suits you.':'A reminder you scheduled is due. Open Saathi to review it.',
    icon:'/saathi-icon.svg',tag,renotify:false,data:{url:'/dashboard#reminders'}
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil((async()=>{
    const windows=await self.clients.matchAll({type:'window',includeUncontrolled:true});
    const existing=windows.find(client=>client.url===self.location.origin+'/dashboard#reminders');
    if(existing)return existing.focus();
    return self.clients.openWindow('/dashboard#reminders');
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)))));
  self.clients.claim();
});

self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);

  // Never intercept non-GET, cross-origin, or API requests
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (NO_CACHE_PATHS.some(p => url.pathname.startsWith(p))) return;

  // For navigation requests (page loads): Network-first with cache fallback
  if (request.mode === "navigate") {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Cache public pages but not authenticated ones
          if (response.ok && !["/dashboard", "/chat"].includes(url.pathname)) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
          }
          return response;
        })
        .catch(async () => {
          // Offline fallback: try cache, then offline.html
          const cached = await caches.match(request);
          if (cached) return cached;
          // For dashboard/chat offline: return offline.html with helpful message
          return caches.match("/offline.html");
        })
    );
    return;
  }

  // For static assets (JS/CSS/images/fonts): Cache-first
  if (/\.(css|js|svg|png|jpg|webp|woff2?|ico)(\?|$)/.test(url.pathname)) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(response => {
          if (response.ok) {
            const copy = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
          }
          return response;
        });
      })
    );
    return;
  }

  // Default: network-first
  event.respondWith(
    fetch(request).catch(() => caches.match(request))
  );
});
