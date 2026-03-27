// Service Worker for Entorhino Web Push Notifications
self.addEventListener('push', function (event) {
    let data = { title: 'Entorhino', body: 'New notification', url: '/dashboard' };
    try {
        if (event.data) data = event.data.json();
    } catch (e) {
        data.body = event.data ? event.data.text() : 'New notification';
    }

    const options = {
        body: data.body || 'New notification',
        icon: data.icon || '/static/icon-192.png',
        badge: '/static/icon-192.png',
        data: { url: data.url || '/dashboard' },
        vibrate: [100, 50, 100],
        requireInteraction: false,
        tag: 'entorhino-' + Date.now(),
    };

    event.waitUntil(
        self.registration.showNotification(data.title || 'Entorhino', options)
    );
});

self.addEventListener('notificationclick', function (event) {
    event.notification.close();
    const url = event.notification.data?.url || '/dashboard';
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clientList) {
            for (const client of clientList) {
                if (client.url.includes(self.location.origin) && 'focus' in client) {
                    client.navigate(url);
                    return client.focus();
                }
            }
            return clients.openWindow(url);
        })
    );
});

self.addEventListener('install', function (event) {
    self.skipWaiting();
});

self.addEventListener('activate', function (event) {
    event.waitUntil(self.clients.claim());
});
