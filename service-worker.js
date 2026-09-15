const CACHE_NAME = "saathi-shell-v14";
const APP_SHELL = [
  "/", "/privacy", "/terms",
  "/limitations", "/support", "/offline.html", "/manifest.webmanifest",
  "/saathi-icon.svg", "/public.css", "/theme.js?v=20260915", "/site-theme.css?v=20260915"
];

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL)));
  self.skipWaiting();
});

// Keep reminder details inside the signed-in workspace, including on lock screens.
self.addEventListener('push', event => {
  let payload={};
  try{payload=event.data?.json()||{}}catch(_){}
  const tag=/^saathi-reminder-\d+-\d+$/.test(payload.tag||'')?payload.tag:'saathi-reminder';
  event.waitUntil(self.registration.showNotification('Saathi reminder',{
    body:'A reminder you scheduled is due. Open Saathi to review it.',
    icon:'/saathi-icon.svg',tag,renotify:false,data:{url:'/dashboard#reminders'}
  }));
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil((async()=>{
    const windows=await self.clients.matchAll({type:'window',includeUncontrolled:true});
    const existing=windows.find(client=>client.url===self.location.origin+'/dashboard#reminders');
    if(existing)return existing.focus();
    // Open a new tab rather than replacing an editor with an unsaved draft.
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
  if (request.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/")) return;
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).then(response => {
      if (response.ok && !["/account", "/dashboard", "/chat"].includes(url.pathname)) {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
      }
      return response;
    }).catch(async () => (await caches.match(request)) || caches.match("/offline.html")));
    return;
  }
  event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
    if (response.ok) {
      const copy = response.clone();
      caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
    }
    return response;
  })));
});
