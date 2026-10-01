import { del, get, post } from '../api.js';
import { estado, navegar, recarregar } from '../estado.js';
import { qrPng, qrSvg } from '../qrcode.js';
import {
  aoEnviar, cabecalho, campo, comErro, confirmar, copiar, erroForm, h, icone, item, opcoes, pill, quando, secao,
  tile, toast, vazio,
} from '../ui.js';

export const TIPOS = {
  visita: ['Visita', 'perfil'],
  prestador: ['Prestador de serviço', 'manutencao'],
  entrega: ['Entrega', 'caixa'],
};
export const SITUACOES = {
  valida: ['Liberada hoje', 'verde'],
  futura: ['Agendada', 'azul'],
  expirada: ['Expirada', ''],
  cancelada: ['Cancelada', 'vermelho'],
};

const doisDigitos = (n) => String(n).padStart(2, '0');
export const hojeLocal = () => {
  const d = new Date();
  return `${d.getFullYear()}-${doisDigitos(d.getMonth() + 1)}-${doisDigitos(d.getDate())}`;
};
const diaCurto = (iso) => (iso === hojeLocal() ? 'hoje' : `${iso.slice(8, 10)}/${iso.slice(5, 7)}`);

export function periodo(visita) {
  if (visita.data_inicio === visita.data_fim) {
    const dia = diaCurto(visita.data_inicio);
    return dia === 'hoje' ? 'Hoje' : `Dia ${dia}`;
  }
  return `De ${diaCurto(visita.data_inicio)} a ${diaCurto(visita.data_fim)}`;
}

/** Endereço que vai no QR Code: abre a tela de validação no celular da portaria. */
export const linkValidacao = (token) => `${location.origin}/#/portaria/v/${token}`;
/** Página pública que o visitante abre para mostrar o QR Code. */
const linkPasse = (token) => `${location.origin}/#/passe/${token}`;

export async function telaVisitas() {
  const cid = estado.membro.condominio_id;
  const { visitas } = await get(`/api/condominios/${cid}/visitas`);
  const ativas = visitas.filter((v) => v.situacao === 'valida' || v.situacao === 'futura');
  const antigas = visitas.filter((v) => !ativas.includes(v)).reverse();

  const linha = (v) => item({
    inicio: tile(TIPOS[v.tipo][1], 'visitas'),
    titulo: v.nome,
    sub: [periodo(v), TIPOS[v.tipo][0], v.entradas && `entrou ${v.entradas}x`].filter(Boolean).join(' · '),
    fim: pill(...SITUACOES[v.situacao]),
    href: `#/visitas/${v.id}`,
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho('Visitantes', {
      subtitulo: 'Libere a entrada e mande o QR Code',
      acao: h('a', { class: 'botao primario', href: '#/visitas/nova' }, icone('mais'), 'Liberar'),
    }),
    ativas.length === 0
      ? vazio({
        icone: 'visitas',
        titulo: 'Nenhuma visita liberada',
        texto: 'Vai receber alguém? Libere a entrada e envie o QR Code pelo WhatsApp. A portaria confere na chegada.',
        acao: h('a', { class: 'botao primario', href: '#/visitas/nova' }, 'Liberar visitante'),
      })
      : secao('Liberadas', h('div', { class: 'cartao lista' }, ativas.map(linha))),
    antigas.length > 0 && secao('Últimos 7 dias', h('div', { class: 'cartao lista' }, antigas.map(linha))));
}

export async function telaNovaVisita() {
  const cid = estado.membro.condominio_id;
  const sindico = estado.membro.papel === 'sindico';
  const hoje = hojeLocal();
  let seletorUnidade = null;
  if (sindico && !estado.membro.unidade_id) {
    const { unidades } = await get(`/api/condominios/${cid}/unidades`);
    seletorUnidade = campo('Para a unidade', h('select', { name: 'unidade_id', required: true },
      h('option', { value: '' }, 'Escolha…'), unidades.map((u) => h('option', { value: u.id }, u.identificador))));
  }

  const inicio = h('input', { name: 'data_inicio', type: 'date', required: true, min: hoje, value: hoje });
  const fim = h('input', { name: 'data_fim', type: 'date', min: hoje });
  const variosDias = h('input', { type: 'checkbox' });
  const campoFim = campo('Até', fim, 'Para prestadores que vêm vários dias (até 30).');
  campoFim.hidden = true;
  variosDias.addEventListener('change', () => {
    campoFim.hidden = !variosDias.checked;
    fim.required = variosDias.checked;
    if (variosDias.checked && !fim.value) fim.value = inicio.value;
  });
  inicio.addEventListener('change', () => { fim.min = inicio.value; });

  const form = h('form', { class: 'pagina' },
    h('section', { class: 'cartao' },
      h('h2', {}, 'Quem vem?'),
      opcoes('tipo', Object.entries(TIPOS).map(([valor, [rotulo, nomeIcone]]) => ({ valor, rotulo, icone: nomeIcone, cor: 'visitas' })), { valor: 'visita' }),
      campo('Nome do visitante', h('input', { name: 'nome', required: true, maxlength: 100, autocomplete: 'off', placeholder: 'Ex.: Carlos Souza' }),
        'A portaria confere com um documento.'),
      seletorUnidade),
    h('section', { class: 'cartao' },
      h('h2', {}, 'Quando?'),
      campo('Data', inicio),
      h('label', { class: 'interruptor' }, variosDias, 'Vem por vários dias'),
      campoFim,
      campo('Observação para a portaria', h('input', { name: 'observacao', maxlength: 300, placeholder: 'Ex.: vai consertar o chuveiro' }), 'Opcional')),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, icone('visitas'), 'Gerar QR Code'));

  aoEnviar(form, async (dados) => {
    const corpo = {
      nome: dados.nome,
      tipo: dados.tipo,
      data_inicio: dados.data_inicio,
      data_fim: variosDias.checked ? dados.data_fim : dados.data_inicio,
      observacao: dados.observacao,
    };
    if (dados.unidade_id) corpo.unidade_id = Number(dados.unidade_id);
    const { visita } = await post(`/api/condominios/${cid}/visitas`, corpo);
    toast('Visita liberada! Agora envie o QR Code.');
    navegar(`visitas/${visita.id}`);
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho('Liberar visitante', { voltar: { rota: 'visitas', texto: 'Visitantes' } }),
    form);
}

export async function telaVisita({ id }) {
  const cid = estado.membro.condominio_id;
  const { visitas } = await get(`/api/condominios/${cid}/visitas`);
  const v = visitas.find((x) => String(x.id) === id);
  if (!v) throw new Error('Visita não encontrada ou de mais de 7 dias atrás.');
  const ativa = v.situacao === 'valida' || v.situacao === 'futura';
  const mensagem = `Olá, ${v.nome}! Sua entrada no ${estado.membro.condominio} está liberada (${periodo(v).toLowerCase()}). `
    + `Mostre este QR Code na portaria: ${linkPasse(v.token)} (código ${v.codigo})`;

  const compartilhar = comErro(async () => {
    const png = await qrPng(linkValidacao(v.token), { legenda: v.nome });
    const arquivo = new File([png], `qr-${v.codigo}.png`, { type: 'image/png' });
    if (navigator.canShare?.({ files: [arquivo] })) {
      try {
        await navigator.share({ files: [arquivo], text: mensagem });
      } catch (e) {
        if (e.name !== 'AbortError') throw e;
      }
    } else {
      window.open(`https://wa.me/?text=${encodeURIComponent(mensagem)}`, '_blank', 'noopener');
    }
  });
  const baixar = comErro(async () => {
    const png = await qrPng(linkValidacao(v.token), { legenda: v.nome });
    const url = URL.createObjectURL(png);
    h('a', { href: url, download: `qr-${v.nome.replace(/\W+/g, '-').toLowerCase()}.png` }).click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  const cancelar = comErro(async () => {
    if (!await confirmar(`O QR Code de ${v.nome} deixa de valer na portaria.`, { titulo: 'Cancelar liberação?', botao: 'Cancelar liberação', perigo: true })) return;
    await del(`/api/condominios/${cid}/visitas/${v.id}`);
    toast('Liberação cancelada.');
    recarregar();
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho(v.nome, { voltar: { rota: 'visitas', texto: 'Visitantes' }, subtitulo: TIPOS[v.tipo][0] }),
    h('section', { class: 'cartao passe' },
      pill(...SITUACOES[v.situacao]),
      ativa
        ? h('div', { class: 'qr-moldura' }, qrSvg(linkValidacao(v.token), { rotulo: `QR Code de entrada de ${v.nome}` }))
        : h('p', { class: 'mudo' }, 'Este QR Code não vale mais na portaria.'),
      h('div', { class: 'dados-visita' },
        h('div', { class: 'dado' }, h('div', { class: 'rotulo' }, 'Período'), h('div', { class: 'valor' }, periodo(v))),
        h('div', { class: 'dado' }, h('div', { class: 'rotulo' }, 'Código'), h('div', { class: 'valor codigo' }, v.codigo))),
      v.observacao && h('p', { class: 'mudo pequeno' }, v.observacao)),
    ativa && h('div', { class: 'pilha-curta' },
      h('button', { class: 'botao primario grande bloco', onclick: compartilhar }, icone('compartilhar'), 'Enviar para o visitante'),
      h('div', { class: 'acoes dividir' },
        h('button', { class: 'botao tonal', onclick: baixar }, icone('baixar'), 'Baixar imagem'),
        h('button', { class: 'botao tonal', onclick: () => copiar(linkPasse(v.token)) }, icone('link'), 'Copiar link'))),
    secao('Entradas', h('div', { class: 'cartao lista' }, item({
      inicio: tile('entrar', 'portaria'),
      titulo: v.entradas ? (v.entradas === 1 ? 'Entrou 1 vez' : `Entrou ${v.entradas} vezes`) : 'Ainda não chegou',
      sub: v.ultima_entrada ? `Última entrada ${quando(v.ultima_entrada)}` : 'A portaria registra quando ler o QR Code',
    }))),
    ativa && h('button', { class: 'botao fantasma perigo', onclick: cancelar }, 'Cancelar liberação'));
}
