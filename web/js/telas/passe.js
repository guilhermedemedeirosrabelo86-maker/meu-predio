import { ErroApi, get } from '../api.js';
import { qrSvg } from '../qrcode.js';
import { formatarDia, h, icone, maiuscula, pill } from '../ui.js';
import { linkValidacao, periodo, SITUACOES, TIPOS } from './visitas.js';

/** Página pública do visitante (sem login): mostra o QR Code para apresentar na portaria. */
export async function telaPasse({ token }) {
  let passe;
  try {
    ({ passe } = await get(`/api/passes/${encodeURIComponent(token)}`));
  } catch (e) {
    if (!(e instanceof ErroApi && e.status === 404)) throw e;
    return moldura(h('section', { class: 'cartao passe' },
      h('span', { class: 'tile grande cor-ocorrencias' }, icone('x')),
      h('h2', {}, 'Passe não encontrado'),
      h('p', { class: 'mudo' }, 'Confira o link com quem liberou sua entrada.')));
  }
  const ativo = passe.situacao === 'valida' || passe.situacao === 'futura';
  const dias = passe.data_inicio === passe.data_fim
    ? maiuscula(formatarDia(passe.data_inicio))
    : `${maiuscula(formatarDia(passe.data_inicio))} a ${formatarDia(passe.data_fim)}`;

  return moldura(h('section', { class: 'cartao passe' },
    pill(...SITUACOES[passe.situacao]),
    h('div', { class: 'pilha-curta' },
      h('p', { class: 'mudo pequeno' }, `Passe de ${TIPOS[passe.tipo][0].toLowerCase()}`),
      h('div', { class: 'nome-visitante' }, passe.nome),
      h('p', { class: 'mudo' }, passe.condominio, passe.endereco && ` · ${passe.endereco}`)),
    ativo
      ? h('div', { class: 'qr-moldura' }, qrSvg(linkValidacao(token), { rotulo: 'QR Code de entrada' }))
      : h('p', {}, passe.situacao === 'cancelada' ? 'Esta liberação foi cancelada.' : 'Esta liberação já expirou.'),
    h('div', { class: 'dados-visita' },
      h('div', { class: 'dado' }, h('div', { class: 'rotulo' }, 'Quando'), h('div', { class: 'valor' }, periodo(passe))),
      h('div', { class: 'dado' }, h('div', { class: 'rotulo' }, 'Código'), h('div', { class: 'valor codigo' }, passe.codigo))),
    ativo && h('p', { class: 'dica' }, `${dias}. Mostre este QR Code e um documento com foto na portaria.`)));
}

function moldura(conteudo) {
  return h('div', { class: 'tela-acesso' },
    h('main', { class: 'acesso' },
      h('div', { class: 'acesso-marca' }, h('span', { class: 'logo' }, icone('predio')), h('h1', {}, 'Meu Prédio')),
      conteudo));
}
