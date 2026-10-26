import { get } from '../api.js';
import { estado } from '../estado.js';
import {
  cabecalho, comErro, h, item, quando, tile, vazio,
} from '../ui.js';

const linha = (i) => item({
  inicio: tile('relogio', 'neutra'),
  titulo: i.texto,
  sub: `${i.autor} · ${quando(i.criado_em)}`,
});

/** O que o síndico fez no dinheiro, nos moradores e nas exclusões. Só leitura. */
export async function telaHistorico() {
  const base = `/api/condominios/${estado.membro.condominio_id}/historico`;
  const { itens, tem_mais: temMais } = await get(base);
  if (!itens.length) {
    return h('div', { class: 'pagina estreita' },
      cabecalho('Histórico', { voltar: { rota: 'menu' } }),
      vazio({ icone: 'relogio', cor: 'neutra', titulo: 'Nada registrado ainda',
        texto: 'Lançamentos, taxas, entrada e saída de moradores e exclusões aparecem aqui.' }));
  }
  const lista = h('div', { class: 'cartao lista' }, itens.map(linha));
  let ultimo = itens[itens.length - 1].id;
  const mais = temMais ? h('button', { class: 'botao bloco', type: 'button' }, 'Carregar mais') : null;
  mais?.addEventListener('click', comErro(async () => {
    const pagina = await get(`${base}?antes=${ultimo}`, { fresco: true });
    lista.append(...pagina.itens.map(linha));
    if (pagina.itens.length) ultimo = pagina.itens[pagina.itens.length - 1].id;
    if (!pagina.tem_mais) mais.remove();
  }));
  return h('div', { class: 'pagina estreita' },
    cabecalho('Histórico', {
      voltar: { rota: 'menu' },
      subtitulo: 'Quem fez o quê. Estes registros não podem ser apagados.',
    }),
    lista,
    mais);
}
