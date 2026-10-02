import { del, get, patch, post } from '../api.js';
import { estado, recarregar } from '../estado.js';
import {
  aoEnviar, cabecalho, campo, centavosDe, dinheiro, erroForm, h, icone, item, mascaraDinheiro, maiuscula, pill,
  secao, segmentado, tile, toast, vazio,
} from '../ui.js';

export const SITUACAO = {
  paga: ['Paga', 'verde'],
  pendente: ['Em aberto', 'amarelo'],
  atrasada: ['Atrasada', 'vermelho'],
};
const pillSituacao = (situacao) => pill(...SITUACAO[situacao]);
const urlBase = () => `/api/condominios/${estado.membro.condominio_id}/taxas`;

export const nomeMes = (mes, opcoesData = { month: 'long' }) => {
  const [ano, m] = mes.split('-').map(Number);
  return maiuscula(new Date(ano, m - 1, 1).toLocaleDateString('pt-BR', opcoesData));
};
function somarMeses(mes, meses) {
  const [ano, m] = mes.split('-').map(Number);
  const total = ano * 12 + (m - 1) + meses;
  return `${Math.floor(total / 12)}-${String((total % 12) + 1).padStart(2, '0')}`;
}
const diaCurto = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' }).replace('.', '');
const formatarCentavos = (centavos) => (centavos ? (centavos / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '');
const campoValor = (centavos) => mascaraDinheiro(h('input', {
  name: 'valor', inputmode: 'numeric', required: true, placeholder: '0,00', autocomplete: 'off', value: formatarCentavos(centavos),
}));

/** Diálogo com formulário: `acao(dados)` roda ao confirmar; se der erro, mostra e mantém aberto. */
function abrirDialogo({ titulo, texto, campos = [], botao, perigo = false, acao }) {
  const form = h('form', {},
    h('div', { class: 'pilha-curta' }, h('h2', {}, titulo), texto && h('p', { class: 'mudo' }, texto)),
    campos.length > 0 && h('div', { class: 'pilha' }, campos),
    erroForm(),
    h('div', { class: 'acoes dividir' },
      h('button', { class: 'botao', type: 'button', onclick: () => dialogo.close() }, 'Voltar'),
      h('button', { class: `botao ${perigo ? 'perigo' : 'primario'}`, type: 'submit' }, botao)));
  const dialogo = h('dialog', { class: 'dialogo' }, form);
  aoEnviar(form, async (dados) => {
    await acao(dados);
    dialogo.close();
  });
  dialogo.addEventListener('close', () => dialogo.remove());
  document.body.append(dialogo);
  dialogo.showModal();
}

function configurar(config) {
  abrirDialogo({
    titulo: 'Valor da taxa',
    texto: 'Usado como sugestão ao registrar cada pagamento. Mudar não altera os pagamentos já registrados.',
    campos: [
      campo('Valor mensal (R$)', campoValor(config.valor_centavos)),
      campo('Dia do vencimento', h('input', { name: 'vencimento', type: 'number', min: 1, max: 28, required: true, inputmode: 'numeric', value: config.vencimento }),
        'Depois desse dia, quem não pagou aparece como atrasado.'),
    ],
    botao: 'Salvar',
    acao: async (dados) => {
      await patch(`${urlBase()}/config`, { valor_centavos: centavosDe(dados.valor), vencimento: Number(dados.vencimento) });
      toast('Taxa atualizada.');
      recarregar();
    },
  });
}

let mesVisto = null;
let condominioVisto = null;
let filtro = 'todas';

/** A prestação de contas abre a taxa no mesmo mês que está mostrando. */
export function definirMesDasTaxas(mes) {
  condominioVisto = estado.membro.condominio_id;
  mesVisto = mes;
}

/** Síndico: quem pagou a taxa no mês. Morador: a situação da própria unidade. */
export async function telaTaxas() {
  const cid = estado.membro.condominio_id;
  if (condominioVisto !== cid) {
    condominioVisto = cid;
    mesVisto = null;
    filtro = 'todas';
  }
  return estado.membro.papel === 'sindico' ? telaDoSindico() : telaDoMorador();
}

async function telaDoSindico() {
  const dados = await get(`${urlBase()}${mesVisto ? `?mes=${mesVisto}` : ''}`);
  const { config, totais } = dados;
  const mesAtual = dados.hoje.slice(0, 7);
  mesVisto = dados.mes;
  const irPara = (mes) => () => {
    mesVisto = mes;
    recarregar();
  };

  const registrar = (u) => abrirDialogo({
    titulo: `Unidade ${u.unidade}`,
    texto: `Registrar a taxa de ${nomeMes(mesVisto).toLowerCase()} como paga. A entrada vai junto para a prestação de contas.`,
    campos: [
      campo('Valor recebido (R$)', campoValor(config.valor_centavos)),
      campo('Pago em', h('input', { name: 'pago_em', type: 'date', required: true, max: dados.hoje, value: dados.hoje })),
    ],
    botao: 'Registrar',
    acao: async (form) => {
      await post(`${urlBase()}/pagamentos`, {
        unidade_id: u.id, mes: mesVisto, valor_centavos: centavosDe(form.valor), pago_em: form.pago_em,
      });
      toast(`Unidade ${u.unidade}: taxa paga.`);
      recarregar();
    },
  });

  const desfazer = (u) => abrirDialogo({
    titulo: `Unidade ${u.unidade}`,
    texto: `Taxa de ${nomeMes(mesVisto).toLowerCase()} paga em ${diaCurto(u.pagamento.pago_em)}: ${dinheiro(u.pagamento.valor_centavos)}. `
      + 'Desfazer remove também a entrada da prestação de contas.',
    botao: 'Desfazer pagamento',
    perigo: true,
    acao: async () => {
      await del(`${urlBase()}/pagamentos/${u.pagamento.id}`);
      toast('Pagamento desfeito.');
      recarregar();
    },
  });

  const lista = h('div');
  const desenhar = () => {
    const visiveis = dados.unidades.filter((u) => filtro === 'todas' || (filtro === 'pagas') === Boolean(u.pagamento));
    lista.replaceChildren(visiveis.length === 0
      ? vazio({
        icone: filtro === 'pagas' ? 'contas' : 'check',
        cor: filtro === 'pagas' ? 'neutra' : 'reservas',
        titulo: filtro === 'pagas' ? 'Nenhuma taxa paga ainda' : 'Todas as unidades pagaram',
      })
      : h('div', { class: 'cartao lista' }, visiveis.map((u) => item({
        inicio: tile('unidade', u.pagamento ? 'reservas' : 'neutra'),
        titulo: `Unidade ${u.unidade}`,
        sub: u.pagamento
          ? `Pago em ${diaCurto(u.pagamento.pago_em)} · ${dinheiro(u.pagamento.valor_centavos)}`
          : u.moradores || 'Ninguém no app',
        fim: pillSituacao(u.situacao),
        onclick: () => (u.pagamento ? desfazer(u) : registrar(u)),
      }))));
  };
  desenhar();

  const emAberto = totais.unidades - totais.pagas;
  const meter = h('div', { class: 'barra' });
  meter.style.setProperty('--largura', `${totais.unidades ? (totais.pagas / totais.unidades) * 100 : 0}%`);

  return h('div', { class: 'pagina estreita' },
    cabecalho('Taxa condominial', {
      voltar: { rota: 'contas', texto: 'Contas' },
      subtitulo: config.valor_centavos ? `${dinheiro(config.valor_centavos)} por mês · vence dia ${config.vencimento}` : 'Marque quem já pagou em cada mês',
      acao: h('button', { class: 'botao tonal', type: 'button', onclick: () => configurar(config) }, icone('editar'), 'Valor'),
    }),
    !config.valor_centavos && h('section', { class: 'cartao alerta' },
      h('div', { class: 'aviso-topo' },
        tile('contas', 'contas'),
        h('div', { class: 'item-texto' },
          h('h2', {}, 'Defina o valor da taxa'),
          h('p', { class: 'mudo' }, 'Com o valor e o dia do vencimento, o app mostra quem está em atraso e avisa você no Início.'))),
      h('button', { class: 'botao primario', type: 'button', onclick: () => configurar(config) }, 'Definir valor')),
    h('section', { class: 'cartao contas-painel' },
      h('div', { class: 'calendario-topo' },
        h('button', { type: 'button', class: 'botao', onclick: irPara(somarMeses(mesVisto, -1)), 'aria-label': 'Mês anterior' }, icone('voltar')),
        h('h3', {}, nomeMes(mesVisto, { month: 'long', year: 'numeric' })),
        h('button', { type: 'button', class: 'botao', disabled: mesVisto > mesAtual, onclick: irPara(somarMeses(mesVisto, 1)), 'aria-label': 'Próximo mês' }, icone('seta'))),
      h('div', { class: 'taxas-progresso' },
        h('p', {}, h('strong', {}, `${totais.pagas} de ${totais.unidades}`), totais.unidades === 1 ? ' unidade pagou' : ' unidades pagaram'),
        h('div', { class: 'barra-trilho grossa', role: 'img', 'aria-label': `${totais.pagas} de ${totais.unidades} unidades pagaram` }, meter)),
      h('div', { class: 'contas-totais' },
        h('div', { class: 'dado' }, h('div', { class: 'rotulo' }, 'Recebido'), h('div', { class: 'valor' }, dinheiro(totais.recebido))),
        h('div', { class: 'dado' }, h('div', { class: 'rotulo' }, 'Em atraso'),
          h('div', { class: 'valor' }, totais.atrasadas === 0 ? 'Nenhuma' : `${totais.atrasadas} unidade${totais.atrasadas === 1 ? '' : 's'}`)))),
    segmentado([
      { valor: 'todas', rotulo: 'Todas' },
      { valor: 'abertas', rotulo: `Em aberto${emAberto ? ` (${emAberto})` : ''}` },
      { valor: 'pagas', rotulo: 'Pagas' },
    ], filtro, (valor) => {
      filtro = valor;
      desenhar();
    }),
    lista,
    h('p', { class: 'dica centro' }, 'Toque numa unidade para registrar o pagamento ou desfazer.'));
}

async function telaDoMorador() {
  const dados = await get(`${urlBase()}/minha`);
  const { config } = dados;
  const topo = cabecalho('Minha taxa', {
    voltar: { rota: 'contas', texto: 'Contas' },
    subtitulo: dados.unidade && config.valor_centavos
      ? `Unidade ${dados.unidade} · ${dinheiro(config.valor_centavos)} por mês · vence dia ${config.vencimento}`
      : null,
  });
  if (!dados.unidade || !config.valor_centavos) {
    return h('div', { class: 'pagina estreita' }, topo, vazio({
      icone: 'contas',
      cor: 'contas',
      titulo: !dados.unidade ? 'Você não está ligado a uma unidade' : 'Taxa ainda não definida',
      texto: !dados.unidade ? 'A situação da taxa aparece para quem mora numa unidade.' : 'Quando o síndico definir o valor da taxa, você acompanha seus pagamentos aqui.',
    }));
  }

  const atual = dados.meses[0];
  const atrasados = dados.meses.filter((m) => m.situacao === 'atrasada');
  const destaque = {
    paga: ['check', 'reservas', `Taxa de ${nomeMes(atual.mes).toLowerCase()} paga`, `Pagamento registrado em ${atual.pagamento && diaCurto(atual.pagamento.pago_em)}.`],
    pendente: ['relogio', 'unidade', `Taxa de ${nomeMes(atual.mes).toLowerCase()} em aberto`, `Vence no dia ${config.vencimento}.`],
    atrasada: ['alerta', 'ocorrencias', `Taxa de ${nomeMes(atual.mes).toLowerCase()} em atraso`, `Venceu no dia ${config.vencimento}. Se você já pagou, avise o síndico.`],
  }[atual.situacao];

  return h('div', { class: 'pagina estreita' },
    topo,
    h('section', { class: 'cartao' },
      h('div', { class: 'aviso-topo' },
        tile(destaque[0], destaque[1]),
        h('div', { class: 'item-texto' }, h('h2', {}, destaque[2]), h('p', { class: 'mudo' }, destaque[3])),
        pillSituacao(atual.situacao))),
    atrasados.length > (atual.situacao === 'atrasada' ? 1 : 0) && h('section', { class: 'cartao alerta' },
      h('p', { class: 'com-icone' }, icone('alerta'),
        `${atrasados.length} ${atrasados.length === 1 ? 'mês' : 'meses'} em atraso. Se já pagou, fale com o síndico para ele registrar.`)),
    secao('Últimos meses', h('div', { class: 'cartao lista' }, dados.meses.map((m) => item({
      titulo: nomeMes(m.mes, { month: 'long', year: 'numeric' }),
      sub: m.pagamento ? `Pago em ${diaCurto(m.pagamento.pago_em)} · ${dinheiro(m.pagamento.valor_centavos)}` : null,
      fim: pillSituacao(m.situacao),
    })))),
    h('p', { class: 'dica centro' }, 'Quem registra os pagamentos é o síndico. Só você e ele veem a situação da sua unidade.'));
}
