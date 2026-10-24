// Service worker portálu Jak se máme: jen upozornění na nová jednání a novinky (Web Push).
// Nic neukládá do mezipaměti, web funguje stejně jako bez něj.
// Server pošle zašifrovaný JSON {title, body, url, tag}; prohlížeč ho rozšifruje a sem dorazí hotový.
// (Převzato z webu Střeličníku, new.strelicnik.cz.)

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))

// Hlášení serveru, co se se zprávou stalo (deník doručování, bez údajů o zařízení).
const report = (tag, stage, detail = '') =>
  fetch('/push/api.php?a=seen', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tag, stage, detail }),
    keepalive: true,
  }).catch(() => undefined)

self.addEventListener('push', (event) => {
  let data = {}
  try {
    data = event.data ? event.data.json() : {}
  } catch (e) {
    data = { body: event.data ? event.data.text() : '' }
  }
  const tag = data.tag || 'jaksemame'

  event.waitUntil(
    report(tag, 'push').then(() => self.registration.showNotification(data.title || 'Jak se máme', {
      body: data.body || '',
      icon: '/icon-192.png',
      lang: 'cs',
      // Stejný štítek nahradí předchozí upozornění, ať se v liště nehromadí,
      tag,
      // a renotify zařídí, že se nové přesto ohlásí.
      renotify: true,
      data: { url: data.url || '/' },
    }))
      .then(() => report(tag, 'shown'))
      .catch((e) => report(tag, 'error', String((e && e.message) || e))),
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const target = new URL((event.notification.data && event.notification.data.url) || '/', self.location.origin).href

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if (new URL(client.url).origin === self.location.origin && 'focus' in client) {
          // navigate() selže u okna, které service worker neřídí; pak otevřít nové
          return client.focus()
            .then(() => ('navigate' in client ? client.navigate(target) : self.clients.openWindow(target)))
            .catch(() => self.clients.openWindow(target))
        }
      }
      return self.clients.openWindow(target)
    }),
  )
})
