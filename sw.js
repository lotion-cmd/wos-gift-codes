self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || '🎁 新しいギフトコード！';
  const body = data.body || '新しいコードが追加されました';
  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: '/wos-gift-codes/icon-192.png',
      badge: '/wos-gift-codes/icon-192.png',
    })
  );
});

self.addEventListener('notificationclick', event => {
  event.notification.close();
  event.waitUntil(
    clients.openWindow('https://lotion-cmd.github.io/wos-gift-codes/')
  );
});
