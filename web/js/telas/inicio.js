import { get } from '../api.js';
import { estado } from '../estado.js';
import { atualizarContador } from '../notificacoes.js';
import {
  contar, formatarDia, h, icone, item, maiuscula, pill, primeiroNome, quando, saudacao, secao, tile,
} from '../ui.js';

/** Painel inicial: atalhos, pendências e um resumo de cada módulo. */
export async function telaInicio() {
  const membro = estado.membro;
  const sindico = membro.papel === 'sindico';
  const painel = await get(`/api/condominios/${membro.condominio_id}/painel`);
  atualizarContador(painel.avisos_nao_lidos);

  const atalhos = sindico
    ? [['avisos/novo', 'avisos', 'Novo aviso'], ['moradores', 'moradores', 'Moradores'],
      ['reservas', 'reservas', 'Reservas'], ['portaria', 'portaria', 'Portaria']]
    : [['visitas/nova', 'visitas', 'Liberar visita'], ['reservas', 'reservas', 'Reservar'],
      ['ocorrencias/nova', 'ocorrencias', 'Ocorrência'], ['unidade', 'unidade', 'Minha unidade']];

  return h('div', { class: 'pagina' },
    h('header', { class: 'hero topo-pagina' },
      h('p', { class: 'data' }, maiuscula(new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' }))),
      h('h1', {}, `${saudacao()}, ${primeiroNome(estado.usuario.nome)}`),
      h('div', { class: 'hero-chips' },
        h('a', { href: membro.unidade_id ? '#/unidade' : '#/condominios' }, icone('local'), membro.unidade ? `Unidade ${membro.unidade}` : membro.condominio),
        painel.avisos_nao_lidos > 0 && h('a', { href: '#/avisos' }, icone('sino'),
          painel.avisos_nao_lidos === 1 ? '1 aviso novo' : `${painel.avisos_nao_lidos} avisos novos`),
        !sindico && painel.visitas_hoje > 0 && h('a', { href: '#/visitas' }, icone('visitas'),
          painel.visitas_hoje === 1 ? '1 visita hoje' : `${painel.visitas_hoje} visitas hoje`),
        !sindico && painel.taxa && (painel.taxa.situacao !== 'paga' || painel.taxa.meses_atrasados > 0) && h('a', { href: '#/contas/taxas' }, icone('contas'),
          painel.taxa.situacao === 'atrasada' || painel.taxa.meses_atrasados > 0 ? 'Taxa em atraso' : `Taxa vence dia ${painel.taxa.vencimento}`),
        sindico && painel.portaria.esperados > 0 && h('a', { href: '#/portaria' }, icone('portaria'),
          `${painel.portaria.esperados} esperado${painel.portaria.esperados === 1 ? '' : 's'} hoje`))),

    h('nav', { class: 'atalhos', 'aria-label': 'Atalhos' },
      atalhos
        .filter(([rota]) => rota !== 'unidade' || membro.unidade_id)
        .map(([rota, cor, rotulo]) => h('a', { class: 'atalho', href: `#/${rota}` }, tile(cor), rotulo))),

    h('nav', { class: 'cartao resumo-numeros', 'aria-label': 'Resumo' },
      numero('avisos', painel.avisos_nao_lidos, painel.avisos_nao_lidos === 1 ? 'aviso novo' : 'avisos novos', 'avisos'),
      sindico
        ? numero('portaria', painel.portaria.esperados, painel.portaria.esperados === 1 ? 'visita hoje' : 'visitas hoje', 'portaria')
        : numero('visitas', painel.visitas_hoje, painel.visitas_hoje === 1 ? 'visita hoje' : 'visitas hoje', 'visitas'),
      numero('ocorrencias', painel.ocorrencias_abertas, painel.ocorrencias_abertas === 1 ? 'ocorrência aberta' : 'ocorrências abertas', 'ocorrencias'),
      sindico
        ? numero('entrar', painel.portaria.entradas, 'entradas em 24h', 'portaria', 'reservas')
        : numero('reservas', painel.proxima_reserva ? 1 : 0, painel.proxima_reserva ? 'reserva marcada' : 'reservas marcadas', 'reservas')),

    h('div', { class: 'grade' },
    sindico && pendencias(painel),
    painel.ultimo_aviso && secao('Último aviso', h('div', { class: 'cartao lista' }, item({
      inicio: tile('avisos'),
      titulo: painel.ultimo_aviso.titulo,
      sub: maiuscula(quando(painel.ultimo_aviso.criado_em)),
      fim: painel.ultimo_aviso.novo && pill('Novo', 'solido', 'sem-ponto'),
      href: '#/avisos',
    })), h('a', { href: '#/avisos' }, 'Ver todos')),

    painel.proxima_reserva && secao('Próxima reserva', h('div', { class: 'cartao lista' }, item({
      inicio: tile('reservas'),
      titulo: painel.proxima_reserva.area,
      sub: maiuscula(formatarDia(painel.proxima_reserva.data)),
      fim: painel.proxima_reserva.status === 'pendente' ? pill('Aguardando', 'amarelo') : pill('Confirmada', 'verde'),
      href: '#/reservas',
    })))));
}

/** Um número do resumo: ícone, valor e rótulo curto. Zero fica apagado para não chamar atenção. */
function numero(nomeIcone, valor, rotulo, rota, cor = nomeIcone) {
  return h('a', { class: `numero${valor ? '' : ' zero'}`, href: `#/${rota}` },
    tile(nomeIcone, cor),
    contar(h('span', { class: 'valor' }), valor),
    h('span', { class: 'rotulo' }, rotulo));
}

function pendencias(painel) {
  const { pedidos_entrada: pedidos, reservas, taxas_atrasadas: taxas } = painel.pendencias;
  const ocorrencias = painel.ocorrencias_abertas;
  if (!pedidos && !reservas && !ocorrencias && !taxas) return null;
  const linhas = [
    pedidos > 0 && item({
      inicio: tile('moradores'),
      titulo: pedidos === 1 ? '1 pedido para entrar' : `${pedidos} pedidos para entrar`,
      sub: 'Moradores ou funcionários aguardando sua aprovação',
      href: '#/moradores',
    }),
    reservas > 0 && item({
      inicio: tile('reservas'),
      titulo: reservas === 1 ? '1 reserva para aprovar' : `${reservas} reservas para aprovar`,
      sub: 'Áreas que exigem sua aprovação',
      href: '#/reservas',
    }),
    taxas > 0 && item({
      inicio: tile('contas', 'contas'),
      titulo: taxas === 1 ? '1 unidade com taxa atrasada' : `${taxas} unidades com taxa atrasada`,
      sub: 'Registre os pagamentos recebidos ou cobre os moradores',
      href: '#/contas/taxas',
    }),
    ocorrencias > 0 && item({
      inicio: tile('ocorrencias'),
      titulo: ocorrencias === 1 ? '1 ocorrência em aberto' : `${ocorrencias} ocorrências em aberto`,
      sub: 'Responda e acompanhe até resolver',
      href: '#/ocorrencias',
    }),
  ];
  return secao('Precisa da sua atenção', h('div', { class: 'cartao lista' }, linhas));
}
