// Service worker: deixa o app abrir sem internet (mostrando a última versão)
// e abre o mural quando o morador toca numa notificação.
const CACHE = 'meu-predio-v21';
const ARQUIVOS = [
  '/', '/index.html', '/manifest.webmanifest', '/icone.svg', '/icone-192.png', '/icone-512.png',
  '/css/app.css', '/fonts/poppins-400.woff2', '/fonts/poppins-500.woff2', '/fonts/poppins-600.woff2', '/fonts/poppins-700.woff2', '/img/condominio-manha.jpg', '/img/condominio-tarde.jpg', '/img/condominio-noite.jpg',
  '/js/abertura.js', '/js/app.js', '/js/api.js', '/js/estado.js', '/js/notificacoes.js', '/js/qrcode.js', '/js/ui.js',
  '/js/telas/avisos.js', '/js/telas/celular.js', '/js/telas/condominios.js', '/js/telas/conta.js',
  '/js/telas/contas.js', '/js/telas/encomendas.js', '/js/telas/enquetes.js', '/js/telas/historico.js', '/js/telas/inicio.js', '/js/telas/legal.js',
  '/js/telas/menu.js', '/js/telas/moradores.js', '/js/telas/ocorrencias.js', '/js/telas/passe.js',
  '/js/telas/perfil.js', '/js/telas/portaria.js', '/js/telas/reservas.js', '/js/telas/taxas.js',
  '/js/telas/telefones.js', '/js/telas/unidade.js', '/js/telas/visitas.js',
];

self.addEventListener('install', (evento) => {
  evento.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ARQUIVOS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((nomes) => Promise.all(nomes.filter((n) => n !== CACHE).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

// Rede primeiro (para sempre pegar a versão nova); cache só quando estiver offline.
self.addEventListener('fetch', (evento) => {
  const url = new URL(evento.request.url);
  if (evento.request.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/')) return;
  evento.respondWith(
    fetch(evento.request)
      .then((resposta) => {
        if (resposta.ok) {
          const copia = resposta.clone();
          caches.open(CACHE).then((cache) => cache.put(evento.request, copia));
        }
        return resposta;
      })
      .catch(() => caches.match(evento.request).then((r) => r || caches.match('/index.html'))),
  );
});

self.addEventListener('notificationclick', (evento) => {
  evento.notification.close();
  const destino = evento.notification.data?.url || '/#/avisos';
  evento.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((janelas) => {
      for (const janela of janelas) {
        if ('focus' in janela) {
          janela.navigate(destino);
          return janela.focus();
        }
      }
      return self.clients.openWindow(destino);
    }),
  );
});
