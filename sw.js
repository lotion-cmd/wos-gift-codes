const CACHE_VERSION = 'v2';

self.addEventListener('install', event => {
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.map(key => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('push', event => {
  let title = '🎁 新しいギフトコード！';
  let body = '新しいコードが追加されました。サイトを確認してください。';
  try {
    const data = event.data.json();
    if (data.title) title = data.title;
    if (data.body) body = data.body;
  } catch(e) {}
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: '/wos-gift-codes/icon-192.png',
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow('https://lotion-cmd.github.io/wos-gift-codes/')
  );
});
