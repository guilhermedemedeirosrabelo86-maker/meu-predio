import { get } from '../api.js';
import { qrSvg } from '../qrcode.js';
import { copiar, h, icone } from '../ui.js';

/** Mostra no computador um QR Code para abrir o app no celular pela mesma rede Wi-Fi. */
export async function telaCelular() {
  const rede = await get('/api/rede');
  const [principal, ...outros] = rede.enderecos;

  let conteudo;
  if (!rede.aberto_na_rede) {
    conteudo = h('section', { class: 'cartao' },
      h('h2', {}, 'O servidor está fechado para a rede'),
      h('p', { class: 'mudo' }, 'Do jeito que foi iniciado, só este computador consegue abrir o app.'),
      h('ol', { class: 'passos' },
        h('li', {}, 'Feche a janela preta do servidor.'),
        h('li', {}, 'Abra pelo arquivo ', h('strong', {}, 'iniciar-celular.bat'), ', na pasta do projeto.'),
        h('li', {}, 'Esta página vai abrir sozinha, já com o QR Code.')));
  } else if (!principal) {
    conteudo = h('section', { class: 'cartao' },
      h('h2', {}, 'Nenhuma rede encontrada'),
      h('p', { class: 'mudo' }, 'Conecte o computador ao Wi-Fi e recarregue esta página.'));
  } else {
    conteudo = h('section', { class: 'cartao passe' },
      h('h2', {}, 'Aponte a câmera do celular'),
      h('div', { class: 'qr-moldura' }, qrSvg(principal, { rotulo: `QR Code para abrir ${principal}` })),
      h('p', { class: 'endereco-rede' }, principal),
      h('button', { class: 'botao tonal', onclick: () => copiar(principal) }, icone('copiar'), 'Copiar endereço'),
      outros.length > 0 && h('p', { class: 'dica' }, `Se não abrir, tente: ${outros.join(' ou ')}`),
      h('ol', { class: 'passos' },
        h('li', {}, 'O celular precisa estar ', h('strong', {}, 'no mesmo Wi-Fi'), ' que este computador.'),
        h('li', {}, 'Se o celular não carregar, o ', h('strong', {}, 'Firewall do Windows'), ' está bloqueando. Na primeira vez, o Windows pergunta se o Python pode acessar a rede: marque ',
          h('strong', {}, 'o tipo de rede em que você está'), ' (privada ou pública) e clique em Permitir. Em computador da empresa isso pode precisar do suporte de TI.'),
        h('li', {}, 'Sem HTTPS, o celular abre o app normalmente, mas não deixa instalar na tela inicial nem receber notificações.')));
  }

  return h('div', { class: 'tela-acesso' },
    h('main', { class: 'acesso' },
      h('div', { class: 'acesso-marca' },
        h('span', { class: 'logo' }, icone('celular')),
        h('h1', {}, 'Abrir no celular'),
        h('p', {}, 'Teste o Meu Prédio no seu celular, como os moradores vão usar.')),
      conteudo,
      h('p', { class: 'centro' }, h('a', { href: '#/' }, 'Voltar ao app'))));
}
