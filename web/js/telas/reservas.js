import { del, get, patch, post } from '../api.js';
import { estado, navegar, recarregar } from '../estado.js';
import {
  aoEnviar, cabecalho, campo, comErro, confirmar, erroForm, formatarDia, h, icone, item, maiuscula, pill,
  tile, toast, vazio,
} from '../ui.js';

const AREA_PADRAO = { regras: '', exige_aprovacao: false, antecedencia_dias: 60, limite_por_unidade: 2 };

// Mês aberto no calendário, mantido quando a tela é redesenhada depois de uma ação.
let mesVisto = null;
let condominioVisto = null;

const doisDigitos = (n) => String(n).padStart(2, '0');
const isoLocal = (d) => `${d.getFullYear()}-${doisDigitos(d.getMonth() + 1)}-${doisDigitos(d.getDate())}`;

function somarDias(iso, dias) {
  const d = new Date(`${iso}T12:00:00`);
  d.setDate(d.getDate() + dias);
  return isoLocal(d);
}

function somarMeses(mes, meses) {
  const [ano, m] = mes.split('-').map(Number);
  const d = new Date(ano, m - 1 + meses, 1);
  return `${d.getFullYear()}-${doisDigitos(d.getMonth() + 1)}`;
}

export async function telaReservas({ area: areaEscolhida } = {}) {
  const cid = estado.membro.condominio_id;
  const sindico = estado.membro.papel === 'sindico';
  const [{ areas, hoje }, proximas] = await Promise.all([
    get(`/api/condominios/${cid}/areas`),
    get(`/api/condominios/${cid}/reservas/proximas`),
  ]);

  const topo = cabecalho('Reservas', {
    subtitulo: 'Escolha a área e toque num dia livre',
    acao: sindico && h('a', { class: 'botao tonal', href: '#/reservas/areas' }, icone('editar'), 'Áreas'),
  });

  if (areas.length === 0) {
    return h('div', { class: 'pagina' }, topo, sindico
      ? primeirasAreas(cid)
      : vazio({ icone: 'reservas', titulo: 'Nenhuma área para reservar', texto: 'O síndico ainda não cadastrou o salão, a churrasqueira ou outras áreas.' }));
  }

  const area = areas.find((a) => String(a.id) === areaEscolhida) || areas[0];
  const mesAtual = hoje.slice(0, 7);
  if (!mesVisto || condominioVisto !== cid || (!sindico && mesVisto < mesAtual)) mesVisto = mesAtual;
  condominioVisto = cid;

  const contexto = {
    cid, area, hoje, sindico,
    calendario: h('div', { class: 'pilha-curta' }),
    painel: h('div', { class: 'painel-dia', 'aria-live': 'polite' }),
  };
  await carregarMes(contexto);

  return h('div', { class: 'pagina' },
    topo,
    sindico && proximas.pendentes.length > 0 && cartaoPendentes(cid, proximas.pendentes),
    areas.length > 1 && h('nav', { class: 'chips', 'aria-label': 'Áreas' },
      areas.map((a) => h('a', { class: 'chip', href: `#/reservas/${a.id}`, 'aria-current': a.id === area.id ? 'page' : null }, a.nome))),
    h('div', { class: 'colunas' },
    h('section', { class: 'cartao' },
      h('div', { class: 'aviso-topo' },
        tile('reservas'),
        h('div', { class: 'item-texto' }, h('h2', {}, area.nome), h('span', { class: 'item-sub' }, resumoArea(area)))),
      area.regras && h('details', {}, h('summary', {}, 'Regras de uso'), h('p', { class: 'texto-livre mudo' }, area.regras)),
      contexto.calendario,
      legenda(),
      contexto.painel),
    minhasReservas(cid, estado.membro.unidade_id ? proximas.minhas : null)));
}

function resumoArea(area) {
  return [
    'Dia inteiro',
    `até ${area.antecedencia_dias} dias antes`,
    area.exige_aprovacao ? 'síndico aprova' : 'confirmação na hora',
  ].join(' · ');
}

async function carregarMes(ctx, sentido = 0) {
  const { reservas } = await get(`/api/condominios/${ctx.cid}/reservas?area_id=${ctx.area.id}&mes=${mesVisto}`);
  ctx.calendario.replaceChildren(...calendario(ctx, reservas));
  ctx.painel.replaceChildren();
  if (sentido) ctx.calendario.querySelector('.calendario').classList.add(sentido > 0 ? 'vindo-direita' : 'vindo-esquerda');
}

function calendario(ctx, reservas) {
  const mesAtual = ctx.hoje.slice(0, 7);
  const limite = somarDias(ctx.hoje, ctx.area.antecedencia_dias);
  const podeVoltar = ctx.sindico || mesVisto > mesAtual;
  const podeAvancar = ctx.sindico ? mesVisto < somarMeses(mesAtual, 12) : mesVisto < limite.slice(0, 7);
  const mudarMes = (passo) => comErro(async () => {
    mesVisto = somarMeses(mesVisto, passo);
    await carregarMes(ctx, passo);
  });

  const [ano, mes] = mesVisto.split('-').map(Number);
  const titulo = new Date(ano, mes - 1, 1).toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' });
  const porDia = Object.fromEntries(reservas.map((r) => [r.data, r]));
  const celulas = [];
  for (let i = new Date(ano, mes - 1, 1).getDay(); i > 0; i--) celulas.push(h('span', { 'aria-hidden': 'true' }));

  for (let dia = 1; dia <= new Date(ano, mes, 0).getDate(); dia++) {
    const iso = `${mesVisto}-${doisDigitos(dia)}`;
    const reserva = porDia[iso];
    const passado = iso < ctx.hoje;
    const foraDoPrazo = !ctx.sindico && iso > limite;
    let classe;
    let situacao;
    if (reserva) {
      classe = reserva.minha ? 'minha' : 'ocupado';
      if (reserva.status === 'pendente') classe += ' pendente';
      situacao = reserva.minha ? 'reservado pela sua unidade' : `reservado pela unidade ${reserva.unidade}`;
      if (reserva.status === 'pendente') situacao += ', aguardando aprovação';
    } else if (passado) {
      classe = 'indisponivel';
      situacao = 'já passou';
    } else if (foraDoPrazo) {
      classe = 'indisponivel';
      situacao = 'ainda não liberado para reserva';
    } else {
      classe = 'livre';
      situacao = 'livre';
    }
    const botao = h('button', {
      type: 'button',
      class: `dia ${classe}${iso === ctx.hoje ? ' hoje' : ''}`,
      disabled: !reserva && (passado || foraDoPrazo),
      'aria-label': `${formatarDia(iso)}: ${situacao}`,
      title: situacao,
      onclick: comErro(async () => {
        ctx.calendario.querySelector('.dia.selecionado')?.classList.remove('selecionado');
        botao.classList.add('selecionado');
        await mostrarDia(ctx, iso, reserva);
      }),
    }, dia);
    celulas.push(botao);
  }

  return [
    h('div', { class: 'calendario-topo' },
      h('button', { type: 'button', class: 'botao', disabled: !podeVoltar, onclick: mudarMes(-1), 'aria-label': 'Mês anterior' }, icone('voltar')),
      h('h3', {}, maiuscula(titulo)),
      h('button', { type: 'button', class: 'botao', disabled: !podeAvancar, onclick: mudarMes(1), 'aria-label': 'Próximo mês' }, icone('seta'))),
    deslizavel(h('div', { class: 'calendario' },
      ['D', 'S', 'T', 'Q', 'Q', 'S', 'S'].map((d) => h('span', { class: 'semana', 'aria-hidden': 'true' }, d)),
      celulas), (passo) => {
      if (passo < 0 ? podeVoltar : podeAvancar) mudarMes(passo)();
    }),
  ];
}

/** Deslizar o dedo para os lados chama aoDeslizar(+1 ou -1). */
function deslizavel(el, aoDeslizar) {
  let inicio = null;
  el.addEventListener('touchstart', (e) => { inicio = [e.touches[0].clientX, e.touches[0].clientY]; }, { passive: true });
  el.addEventListener('touchend', (e) => {
    if (!inicio) return;
    const dx = e.changedTouches[0].clientX - inicio[0];
    const dy = e.changedTouches[0].clientY - inicio[1];
    inicio = null;
    if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) aoDeslizar(dx < 0 ? 1 : -1);
  }, { passive: true });
  return el;
}

function legenda() {
  return h('div', { class: 'legenda', 'aria-hidden': 'true' },
    h('span', { class: 'l-livre' }, 'Livre'),
    h('span', { class: 'l-minha' }, 'Sua unidade'),
    h('span', { class: 'l-ocupado' }, 'Reservado'),
    h('span', { class: 'l-pendente' }, 'Aguardando'));
}

async function mostrarDia(ctx, iso, reserva) {
  const titulo = h('h3', {}, maiuscula(formatarDia(iso)));
  ctx.painel.replaceChildren(reserva ? detalhesReserva(ctx, reserva, titulo) : await formReserva(ctx, iso, titulo));
  ctx.painel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function formReserva(ctx, iso, titulo) {
  if (!ctx.sindico && !estado.membro.unidade_id) {
    return h('div', { class: 'pilha-curta' }, titulo,
      h('p', { class: 'mudo' }, 'Você precisa estar vinculado a uma unidade para reservar.'));
  }
  const precisaAprovar = ctx.area.exige_aprovacao && !ctx.sindico;
  let seletorUnidade = null;
  if (ctx.sindico) {
    ctx.unidades ??= (await get(`/api/condominios/${ctx.cid}/unidades`)).unidades;
    seletorUnidade = campo('Para a unidade', h('select', { name: 'unidade_id', required: true, value: estado.membro.unidade_id ?? '' },
      h('option', { value: '' }, 'Escolha…'),
      ctx.unidades.map((u) => h('option', { value: u.id }, u.identificador))));
  }

  const form = h('form', { class: 'pilha' },
    h('div', { class: 'pilha-curta' },
      titulo,
      h('p', {}, pill(precisaAprovar ? 'Livre · o síndico aprova' : 'Livre', 'verde'))),
    seletorUnidade,
    campo('Observação', h('input', { name: 'observacao', maxlength: 300, placeholder: 'Ex.: aniversário, uns 30 convidados' }), 'Opcional'),
    erroForm(),
    h('button', { class: 'botao primario bloco', type: 'submit' }, icone('check'), precisaAprovar ? 'Pedir reserva' : 'Reservar este dia'));
  aoEnviar(form, async (dados) => {
    const corpo = { area_id: ctx.area.id, data: iso, observacao: dados.observacao };
    if (ctx.sindico) corpo.unidade_id = Number(dados.unidade_id);
    const criada = await post(`/api/condominios/${ctx.cid}/reservas`, corpo);
    toast(criada.status === 'pendente' ? 'Pedido enviado ao síndico.' : 'Reserva confirmada!');
    recarregar();
  });
  return form;
}

function detalhesReserva(ctx, reserva, titulo) {
  const podeCancelar = ctx.sindico || (reserva.minha && reserva.data >= ctx.hoje);
  return h('div', { class: 'pilha' },
    h('div', { class: 'pilha-curta' },
      titulo,
      h('div', { class: 'acoes' },
        pill(reserva.minha ? 'Sua unidade' : `Unidade ${reserva.unidade}`, reserva.minha ? 'roxo' : ''),
        reserva.status === 'pendente' ? pill('Aguardando aprovação', 'amarelo') : pill('Confirmada', 'verde'))),
    reserva.reservado_por && h('p', { class: 'mudo pequeno' }, `Reservado por ${reserva.reservado_por}`),
    reserva.observacao && h('p', { class: 'texto-livre' }, reserva.observacao),
    (podeCancelar || (ctx.sindico && reserva.status === 'pendente')) && h('div', { class: 'acoes' },
      ctx.sindico && reserva.status === 'pendente' && h('button', { class: 'botao primario', onclick: aprovar(ctx.cid, reserva) }, icone('check'), 'Aprovar'),
      podeCancelar && h('button', { class: 'botao perigo-suave', onclick: cancelar(ctx.cid, reserva) },
        ctx.sindico && reserva.status === 'pendente' && !reserva.minha ? 'Recusar' : 'Cancelar reserva')));
}

const aprovar = (cid, reserva) => comErro(async () => {
  await patch(`/api/condominios/${cid}/reservas/${reserva.id}`, { status: 'confirmada' });
  toast('Reserva aprovada.');
  recarregar();
});

const cancelar = (cid, reserva) => comErro(async () => {
  const quando = formatarDia(reserva.data);
  const texto = reserva.minha
    ? `${reserva.area} em ${quando}.`
    : `${reserva.area} da unidade ${reserva.unidade} em ${quando}.`;
  if (!await confirmar(texto, { titulo: 'Cancelar reserva?', botao: 'Cancelar reserva', perigo: true })) return;
  await del(`/api/condominios/${cid}/reservas/${reserva.id}`);
  toast('Reserva cancelada.');
  recarregar();
});

function cartaoPendentes(cid, pendentes) {
  return h('section', { class: 'cartao alerta' },
    h('h2', {}, pendentes.length === 1 ? '1 reserva para aprovar' : `${pendentes.length} reservas para aprovar`),
    pendentes.map((r) => h('div', { class: 'morador' },
      tile('reservas'),
      h('div', { class: 'morador-texto' },
        h('strong', {}, `${r.area} · ${maiuscula(formatarDia(r.data))}`),
        h('span', { class: 'item-sub' }, `Unidade ${r.unidade}${r.reservado_por ? ` · ${r.reservado_por}` : ''}`),
        r.observacao && h('span', { class: 'item-sub' }, `“${r.observacao}”`),
        h('div', { class: 'acoes' },
          h('button', { class: 'botao primario pequeno', onclick: aprovar(cid, r) }, icone('check'), 'Aprovar'),
          h('button', { class: 'botao fantasma pequeno perigo', onclick: cancelar(cid, r) }, 'Recusar'))))));
}

function minhasReservas(cid, minhas) {
  if (!minhas) {
    return h('section', { class: 'cartao' },
      h('h2', {}, 'Como funciona'),
      h('p', { class: 'mudo' }, estado.membro.papel === 'sindico'
        ? 'Toque num dia livre para reservar em nome de uma unidade. Dias com ponto já estão reservados.'
        : 'Aqui você acompanha os dias reservados. Só moradores com unidade fazem reservas.'));
  }
  return h('section', { class: 'cartao lista' },
    h('h2', { class: 'titulo-lista' }, 'Próximas da sua unidade'),
    minhas.length === 0
      ? h('p', { class: 'dica titulo-lista' }, 'Nenhuma reserva marcada. Toque num dia livre do calendário.')
      : minhas.map((r) => item({
      inicio: tile('reservas'),
      titulo: maiuscula(formatarDia(r.data)),
      sub: h('span', {}, r.area, ' · ', r.status === 'pendente' ? 'aguardando aprovação' : 'confirmada'),
      fim: h('button', { class: 'botao fantasma pequeno perigo', onclick: cancelar(cid, r) }, 'Cancelar'),
      seta: false,
    })));
}

function primeirasAreas(cid) {
  const criar = (nome) => comErro(async () => {
    await post(`/api/condominios/${cid}/areas`, { ...AREA_PADRAO, nome });
    toast(`${nome} cadastrado.`);
    recarregar();
  });
  return vazio({
    icone: 'reservas',
    titulo: 'Quais áreas podem ser reservadas?',
    texto: 'Comece com uma sugestão. Depois dá para ajustar regras, antecedência e aprovação.',
    acao: h('div', { class: 'acoes' },
      h('button', { class: 'botao primario', onclick: criar('Salão de festas') }, icone('mais'), 'Salão de festas'),
      h('button', { class: 'botao primario', onclick: criar('Churrasqueira') }, icone('mais'), 'Churrasqueira'),
      h('a', { class: 'botao tonal', href: '#/reservas/areas/nova' }, 'Outra área')),
  });
}

// --- Gestão das áreas (síndico) ------------------------------------------------

export async function telaAreas() {
  const cid = estado.membro.condominio_id;
  const { areas } = await get(`/api/condominios/${cid}/areas`);
  const excluir = (area) => comErro(async () => {
    if (!await confirmar('As reservas marcadas nesta área também serão apagadas.', { titulo: `Excluir ${area.nome}?`, botao: 'Excluir', perigo: true })) return;
    await del(`/api/condominios/${cid}/areas/${area.id}`);
    toast('Área excluída.');
    recarregar();
  });
  return h('div', { class: 'pagina estreita' },
    cabecalho('Áreas comuns', {
      voltar: { rota: 'reservas', texto: 'Reservas' },
      subtitulo: 'Regras que valem para os moradores',
      acao: h('a', { class: 'botao primario', href: '#/reservas/areas/nova' }, icone('mais'), 'Nova'),
    }),
    areas.length === 0
      ? vazio({ icone: 'reservas', titulo: 'Nenhuma área cadastrada', texto: 'Cadastre o salão de festas, a churrasqueira ou outra área comum.' })
      : h('div', { class: 'cartao lista' }, areas.map((area) => item({
        inicio: tile('reservas'),
        titulo: area.nome,
        sub: `${resumoArea(area)} · até ${area.limite_por_unidade} por unidade`,
        fim: h('span', { class: 'acoes' },
          h('a', { class: 'botao fantasma pequeno', href: `#/reservas/areas/${area.id}/editar`, 'aria-label': `Editar ${area.nome}` }, icone('editar')),
          h('button', { class: 'botao fantasma pequeno perigo', onclick: excluir(area), 'aria-label': `Excluir ${area.nome}` }, icone('lixo'))),
        seta: false,
      }))));
}

export async function telaEditarArea({ id } = {}) {
  const cid = estado.membro.condominio_id;
  let area = { nome: '', ...AREA_PADRAO };
  if (id) {
    const { areas } = await get(`/api/condominios/${cid}/areas`);
    area = areas.find((a) => String(a.id) === id);
    if (!area) throw new Error('Área não encontrada.');
  }
  const exige = h('input', { type: 'checkbox', name: 'exige_aprovacao' });
  exige.checked = area.exige_aprovacao;

  const form = h('form', { class: 'cartao' },
    campo('Nome', h('input', { name: 'nome', required: true, maxlength: 60, value: area.nome, placeholder: 'Ex.: Salão de festas' })),
    campo('Regras de uso', h('textarea', { name: 'regras', maxlength: 2000, rows: 5, value: area.regras, placeholder: 'Ex.: Uso até 22h. Devolver limpo. Taxa de limpeza de R$ 50.' }),
      'Os moradores veem antes de reservar.'),
    h('div', { class: 'linha' },
      campo('Antecedência máxima (dias)', h('input', { name: 'antecedencia_dias', type: 'number', min: 1, max: 365, required: true, inputmode: 'numeric', value: area.antecedencia_dias })),
      campo('Reservas futuras por unidade', h('input', { name: 'limite_por_unidade', type: 'number', min: 1, max: 20, required: true, inputmode: 'numeric', value: area.limite_por_unidade }))),
    h('label', { class: 'interruptor' }, exige,
      h('span', {}, h('strong', {}, 'Reservas precisam da minha aprovação'), h('br'), h('span', { class: 'dica' }, 'Sem isso, a reserva é confirmada na hora'))),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, id ? 'Salvar alterações' : 'Cadastrar área'));

  aoEnviar(form, async (dados) => {
    const corpo = {
      nome: dados.nome,
      regras: dados.regras,
      exige_aprovacao: exige.checked,
      antecedencia_dias: Number(dados.antecedencia_dias),
      limite_por_unidade: Number(dados.limite_por_unidade),
    };
    if (id) await patch(`/api/condominios/${cid}/areas/${id}`, corpo);
    else await post(`/api/condominios/${cid}/areas`, corpo);
    toast(id ? 'Área atualizada.' : 'Área cadastrada.');
    navegar('reservas/areas');
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho(id ? 'Editar área' : 'Nova área', { voltar: { rota: 'reservas/areas', texto: 'Áreas comuns' } }),
    form);
}
