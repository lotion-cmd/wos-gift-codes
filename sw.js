self.addEventListener('push', event => {
  event.waitUntil(
    self.registration.showNotification('🎁 新しいギフトコード！', {
      body: '新しいコードが追加されました。サイトを確認してください。',
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
