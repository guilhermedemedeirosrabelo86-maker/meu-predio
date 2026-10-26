import { get } from '../api.js';
import { estado } from '../estado.js';
import { atualizarContador } from '../notificacoes.js';
import {
  dinheiro, formatarDia, h, icone, item, maiuscula, pill, primeiroNome, quando, saudacao, secao, tile,
} from '../ui.js';

const plural = (n, um, varios) => (n === 1 ? `1 ${um}` : `${n} ${varios}`);

/** Painel inicial: foto do condomínio com a saudação, os atalhos, o que pede atenção e o caixa. */
export async function telaInicio() {
  const membro = estado.membro;
  const sindico = membro.papel === 'sindico' || membro.papel === 'subsindico';
  const painel = await get(`/api/condominios/${membro.condominio_id}/painel`);
  atualizarContador(painel.avisos_nao_lidos);

  const pend = painel.pendencias || {};
  const taxaAtrasada = painel.taxa && (painel.taxa.situacao === 'atrasada' || painel.taxa.meses_atrasados > 0);
  // Todos os módulos do perfil, para nada ficar escondido. O selo mostra o que pede atenção.
  const modulos = (sindico
    ? [
      ['avisos', 'avisos', 'Avisos', painel.avisos_nao_lidos],
      ['contas', 'contas', 'Contas'],
      ['contas/taxas', 'recibo', 'Taxas', pend.taxas_atrasadas],
      ['moradores', 'moradores', 'Moradores', pend.pedidos_entrada],
      ['reservas', 'reservas', 'Reservas', pend.reservas],
      ['ocorrencias', 'ocorrencias', 'Ocorrências', painel.ocorrencias_abertas],
      ['enquetes', 'enquetes', 'Enquetes', painel.enquetes_sem_voto],
      ['encomendas', 'pacote', 'Encomendas', painel.portaria?.encomendas],
      ['visitas', 'visitas', 'Visitas'],
      ['portaria', 'portaria', 'Portaria'],
      ['telefones', 'telefones', 'Telefones úteis'],
    ]
    : [
      ['avisos', 'avisos', 'Avisos', painel.avisos_nao_lidos],
      ['reservas', 'reservas', 'Reservas'],
      ['visitas', 'visitas', 'Visitas'],
      membro.unidade_id && ['encomendas', 'pacote', 'Encomendas', painel.encomendas],
      ['enquetes', 'enquetes', 'Enquetes', painel.enquetes_sem_voto],
      ['ocorrencias', 'ocorrencias', 'Ocorrências', painel.ocorrencias_abertas],
      ['contas', 'contas', 'Contas'],
      painel.taxa && ['contas/taxas', 'recibo', 'Minha taxa', taxaAtrasada ? '!' : 0],
      membro.unidade_id && ['unidade', 'carro', 'Minha unidade'],
      ['telefones', 'telefones', 'Telefones úteis'],
    ]).filter(Boolean);
  // Completa a grade (4 por linha no celular) com atalhos úteis.
  const complementos = [['perfil', 'perfil', 'Meu perfil'], ['condominios', 'trocar', 'Condomínios'], ['menu', 'menu', 'Mais']];
  while (modulos.length % 4 && complementos.length) modulos.push(complementos.shift());

  // No computador o menu lateral já leva a todas as telas; no lugar dos atalhos ficam ações que já fazem algo.
  const acoes = (sindico
    ? [
      ['avisos/novo', 'avisos', 'Publicar aviso'],
      ['contas/novo', 'contas', 'Lançar conta'],
      ['enquetes/nova', 'enquetes', 'Nova enquete'],
      ['visitas/nova', 'visitas', 'Liberar visita'],
    ]
    : [
      membro.unidade_id && ['visitas/nova', 'visitas', 'Liberar visita'],
      ['ocorrencias/nova', 'ocorrencias', 'Abrir ocorrência'],
      ['reservas', 'reservas', 'Reservar área'],
    ]).filter(Boolean);

  const data = maiuscula(new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' }));
  // No computador, ao lado da foto: o caixa e as taxas do mês (síndico) ou a taxa da unidade (morador).
  const resumo = [
    sindico && painel.caixa && cartaoCaixa(painel.caixa),
    sindico && painel.taxas_mes && cartaoTaxas(painel.taxas_mes),
    !sindico && painel.taxa && cartaoMinhaTaxa(painel.taxa),
    !sindico && painel.caixa && cartaoCaixa(painel.caixa),
  ].filter(Boolean);
  return h('div', { class: 'pagina' },
    // Foto do condomínio no topo, com a saudação. No celular, os atalhos sobem um pouco sobre ela.
    h('div', { class: resumo.length ? 'inicio-topo com-resumo' : 'inicio-topo' },
      h('header', { class: 'hero-foto' },
        h('p', { class: 'data' }, data),
        h('h1', {}, `${saudacao()}, ${primeiroNome(estado.usuario.nome)}`),
        membro.unidade && h('span', { class: 'unidade' }, `Unidade ${membro.unidade}`)),
      resumo.length ? h('div', { class: 'inicio-resumo so-computador' }, resumo) : null),

    h('nav', { class: 'acoes-rapidas so-computador', 'aria-label': 'Ações rápidas' },
      acoes.map(([rota, nomeIcone, rotulo]) => h('a', { class: 'acao-rapida', href: `#/${rota}` },
        tile(nomeIcone), h('span', { class: 'acao-nome' }, rotulo), icone('mais', 'icone fraco')))),

    h('nav', { class: 'atalhos so-celular', 'aria-label': 'Atalhos do condomínio' },
      modulos.map(([rota, nomeIcone, rotulo, selo]) => h('a', { class: 'atalho', href: `#/${rota}` },
        tile(nomeIcone),
        h('span', { class: 'atalho-nome' }, rotulo),
        selo ? h('span', { class: 'selo', 'aria-label': 'Pede atenção' }, typeof selo === 'number' && selo > 9 ? '9+' : selo) : null))),

    h('div', { class: 'grade sem-sobras' },
      paraVoce(painel, sindico),
      painel.caixa && h('div', { class: 'so-celular' }, secao('Caixa', cartaoCaixa(painel.caixa))),
      (painel.ultimo_aviso || painel.proxima_reserva) && secao('Recentes', h('div', { class: 'cartao lista' },
      painel.ultimo_aviso && item({
        inicio: tile('avisos'),
        titulo: painel.ultimo_aviso.titulo,
        sub: `Último aviso, ${quando(painel.ultimo_aviso.criado_em)}`,
        fim: painel.ultimo_aviso.novo && pill('Novo', 'solido'),
        href: '#/avisos',
      }),
      painel.proxima_reserva && item({
        inicio: tile('reservas'),
        titulo: painel.proxima_reserva.area,
        sub: `Sua próxima reserva: ${formatarDia(painel.proxima_reserva.data)}`,
        fim: painel.proxima_reserva.status === 'pendente' ? pill('Aguardando', 'amarelo') : pill('Confirmada', 'verde'),
        href: '#/reservas',
      })))));
}

/** O que pede uma ação agora: pendências do síndico e o que chegou para a unidade. */
function paraVoce(painel, sindico) {
  const pend = painel.pendencias || {};
  const taxa = painel.taxa;
  const linhas = [
    pend.pedidos_entrada > 0 && ['moradores', 'moradores', plural(pend.pedidos_entrada, 'pedido para entrar', 'pedidos para entrar'), 'Moradores ou funcionários aguardando sua aprovação'],
    pend.reservas > 0 && ['reservas', 'reservas', plural(pend.reservas, 'reserva para aprovar', 'reservas para aprovar'), 'Áreas que exigem sua aprovação'],
    pend.taxas_atrasadas > 0 && ['contas/taxas', 'recibo', plural(pend.taxas_atrasadas, 'unidade com taxa atrasada', 'unidades com taxa atrasada'), 'Registre os pagamentos ou cobre os moradores'],
    sindico && painel.ocorrencias_abertas > 0 && ['ocorrencias', 'ocorrencias', plural(painel.ocorrencias_abertas, 'ocorrência em aberto', 'ocorrências em aberto'), 'Responda e acompanhe até resolver'],
    painel.encomendas > 0 && ['encomendas', 'pacote', plural(painel.encomendas, 'encomenda na portaria', 'encomendas na portaria'), 'Retire com a portaria'],
    painel.enquetes_sem_voto > 0 && ['enquetes', 'enquetes', plural(painel.enquetes_sem_voto, 'enquete esperando seu voto', 'enquetes esperando seu voto'), 'Cada unidade vota uma vez'],
    painel.avisos_nao_lidos > 0 && ['avisos', 'avisos', plural(painel.avisos_nao_lidos, 'aviso novo', 'avisos novos'), painel.ultimo_aviso?.novo ? painel.ultimo_aviso.titulo : 'No mural do condomínio'],
    !sindico && taxa && (taxa.situacao === 'atrasada' || taxa.meses_atrasados > 0) && ['contas/taxas', 'recibo', 'Taxa condominial em atraso', 'Veja os meses em aberto'],
    !sindico && taxa && taxa.situacao === 'pendente' && !taxa.meses_atrasados && ['contas/taxas', 'recibo', `Taxa vence dia ${taxa.vencimento}`, dinheiro(taxa.valor_centavos || 0)],
    !sindico && painel.ocorrencias_abertas > 0 && ['ocorrencias', 'ocorrencias', plural(painel.ocorrencias_abertas, 'ocorrência em aberto', 'ocorrências em aberto'), 'Acompanhe a resposta do síndico'],
    painel.visitas_hoje > 0 && ['visitas', 'visitas', plural(painel.visitas_hoje, 'visita liberada para hoje', 'visitas liberadas para hoje'), 'A portaria já está sabendo'],
    sindico && painel.portaria?.esperados > 0 && ['portaria', 'portaria', plural(painel.portaria.esperados, 'visitante esperado hoje', 'visitantes esperados hoje'), 'No prédio todo'],
  ].filter(Boolean);
  const titulo = sindico ? 'Precisa da sua atenção' : 'Para você';
  if (!linhas.length) {
    return secao(titulo, h('div', { class: 'cartao compacto' }, h('p', { class: 'mudo' }, 'Nada pendente. Quando algo chegar, aparece aqui.')));
  }
  return secao(titulo, h('div', { class: 'cartao lista' },
    linhas.map(([rota, nomeIcone, texto, sub]) => item({ inicio: tile(nomeIcone), titulo: texto, sub, href: `#/${rota}` }))));
}

const nomeDoMes = (mes) => new Date(`${mes}-15T12:00`).toLocaleDateString('pt-BR', { month: 'long' });

function cartaoCaixa({ saldo, entradas, saidas }) {
  const mes = new Date().toLocaleDateString('pt-BR', { month: 'long' });
  return h('a', { class: 'cartao', href: '#/contas' },
    h('div', { class: 'caixa-inicio' },
      h('div', {},
        h('div', { class: 'rotulo' }, 'Saldo do condomínio'),
        h('div', { class: `valor${saldo < 0 ? ' negativo' : ''}` }, dinheiro(saldo))),
      tile('seta')),
    h('div', { class: 'caixa-mes' },
      h('span', {}, `Em ${mes}: `, h('span', { class: 'entrou' }, `+ ${dinheiro(entradas)}`)),
      h('span', {}, `− ${dinheiro(saidas)}`)));
}

/** Síndico: quantas unidades já pagaram a taxa do mês, com uma barra de progresso. */
function cartaoTaxas({ mes, pagas, unidades }) {
  const faltam = unidades - pagas;
  const barra = h('div', { class: 'barra' });
  barra.style.setProperty('--largura', `${unidades ? (pagas / unidades) * 100 : 0}%`);
  return h('a', { class: 'cartao', href: '#/contas/taxas' },
    h('div', { class: 'caixa-inicio' },
      h('div', {},
        h('div', { class: 'rotulo' }, `Taxas de ${nomeDoMes(mes)}`),
        h('div', { class: 'valor' }, `${pagas} de ${unidades} pagas`)),
      tile('seta')),
    h('div', { class: 'barra-trilho grossa', role: 'img', 'aria-label': `${pagas} de ${unidades} unidades pagaram` }, barra),
    faltam > 0 && h('div', { class: 'caixa-mes' }, h('span', {}, `${plural(faltam, 'unidade', 'unidades')} sem pagar este mês`)));
}

/** Morador: a taxa da própria unidade no mês. */
function cartaoMinhaTaxa(taxa) {
  const texto = taxa.situacao === 'paga' ? 'Paga' : taxa.situacao === 'atrasada' ? 'Atrasada' : `Vence dia ${taxa.vencimento}`;
  const extra = taxa.meses_atrasados > 0 ? plural(taxa.meses_atrasados, 'mês em atraso', 'meses em atraso') : dinheiro(taxa.valor_centavos || 0);
  return h('a', { class: 'cartao', href: '#/contas/taxas' },
    h('div', { class: 'caixa-inicio' },
      h('div', {},
        h('div', { class: 'rotulo' }, `Minha taxa de ${nomeDoMes(taxa.mes)}`),
        h('div', { class: `valor${taxa.situacao === 'paga' ? ' positivo' : taxa.situacao === 'atrasada' ? ' negativo' : ''}` }, texto)),
      tile('seta')),
    h('div', { class: 'caixa-mes' }, h('span', { class: taxa.meses_atrasados > 0 ? 'atrasou' : '' }, extra)));
}
