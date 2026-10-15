self.addEventListener('install', event => { self.skipWaiting(); });
self.addEventListener('activate', event => { event.waitUntil(self.clients.claim()); });
self.addEventListener('push', event => {
  let data = {title:'Magrão Imports', body:'Você tem uma atualização de pedido.', url:'/app/'};
  try { if (event.data) data = {...data, ...event.data.json()}; } catch (_) {}
  event.waitUntil(self.registration.showNotification(data.title, {body:data.body, tag:data.tag || 'magrao-admin', icon:'/favicon.svg', badge:'/favicon.svg', data:{url:data.url || '/app/'}, renotify:true}));
});
self.addEventListener('notificationclick', event => {
  event.notification.close(); const url = event.notification.data?.url || '/app/';
  event.waitUntil(self.clients.matchAll({type:'window', includeUncontrolled:true}).then(list => { for (const client of list) { if ('focus' in client) { client.navigate(url); return client.focus(); } } return self.clients.openWindow(url); }));
});
