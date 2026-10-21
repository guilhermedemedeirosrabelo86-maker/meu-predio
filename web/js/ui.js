/** Cria um elemento. Textos viram nós de texto (nunca HTML), o que evita injeção de código. */
export function h(tag, atributos = {}, ...filhos) {
  const el = document.createElement(tag);
  let valor;
  for (const [chave, v] of Object.entries(atributos || {})) {
    if (v == null || v === false) continue;
    if (chave === 'value') valor = v;
    else if (chave.startsWith('on')) el.addEventListener(chave.slice(2), v);
    else if (chave === 'class') el.className = v;
    else el.setAttribute(chave, v === true ? '' : v);
  }
  for (const filho of filhos.flat(Infinity)) {
    if (filho == null || filho === false || filho === '') continue;
    el.append(filho instanceof Node ? filho : String(filho));
  }
  if (valor !== undefined) el.value = valor; // depois dos filhos, para funcionar em <select>
  return el;
}

// Ícones de traço no estilo Lucide (licença ISC), desenhados em 24x24.
const ICONES = {
  inicio: ['M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z'],
  avisos: ['m3 11 18-5v12L3 14v-3z', 'M11.6 16.8a3 3 0 1 1-5.8-1.6'],
  sino: ['M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9', 'M10.3 21a1.94 1.94 0 0 0 3.4 0'],
  reservas: ['M8 2v4', 'M16 2v4', 'M3 10h18', 'M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z'],
  ocorrencias: ['M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z', 'M12 9v4', 'M12 17h.01'],
  visitas: ['M4 4h6v6H4z', 'M14 4h6v6h-6z', 'M4 14h6v6H4z', 'M14 14h2v2h-2z', 'M18 14h2', 'M14 18h2', 'M18 18h2v2', 'M20 16v.01'],
  portaria: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z', 'm9 12 2 2 4-4'],
  moradores: ['M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2', 'M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0', 'M22 21v-2a4 4 0 0 0-3-3.87', 'M16 3.13a4 4 0 0 1 0 7.75'],
  unidade: ['M4 21V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v16', 'M16 9h2a2 2 0 0 1 2 2v10', 'M2 21h20', 'M8 7h4', 'M8 11h4', 'M8 15h4'],
  carro: ['M5 17h14v-5l-2-5H7l-2 5z', 'M5 12h14', 'M7 17v2', 'M17 17v2', 'M7.5 14.5h.01', 'M16.5 14.5h.01'],
  perfil: ['M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2', 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0'],
  menu: ['M4 6h16', 'M4 12h16', 'M4 18h16'],
  seta: ['m9 18 6-6-6-6'],
  voltar: ['m15 18-6-6 6-6'],
  abaixo: ['m6 9 6 6 6-6'],
  mais: ['M12 5v14', 'M5 12h14'],
  camera: ['M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3z', 'M15 13a3 3 0 1 1-6 0 3 3 0 0 1 6 0'],
  enviar: ['m22 2-7 20-4-9-9-4z', 'M22 2 11 13'],
  check: ['M20 6 9 17l-5-5'],
  x: ['M18 6 6 18', 'M6 6l12 12'],
  relogio: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z', 'M12 6v6l4 2'],
  sair: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'm16 17 5-5-5-5', 'M21 12H9'],
  entrar: ['M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4', 'm10 17 5-5-5-5', 'M15 12H3'],
  trocar: ['m17 2 4 4-4 4', 'M3 11v-1a4 4 0 0 1 4-4h14', 'm7 22-4-4 4-4', 'M21 13v1a4 4 0 0 1-4 4H3'],
  compartilhar: ['M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8', 'm16 6-4-4-4 4', 'M12 2v13'],
  baixar: ['M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4', 'm7 10 5 5 5-5', 'M12 15V3'],
  pino: ['M12 17v5', 'M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V7a1 1 0 0 1 1-1 2 2 0 0 0 0-4H8a2 2 0 0 0 0 4 1 1 0 0 1 1 1z'],
  telefone: ['M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z'],
  email: ['M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z', 'm22 6-10 7L2 6'],
  conversa: ['M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'],
  copiar: ['M20 9h-9a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2v-9a2 2 0 0 0-2-2z', 'M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1'],
  lixo: ['M3 6h18', 'M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6', 'M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2'],
  editar: ['M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z'],
  barulho: ['M11 5 6 9H2v6h4l5 4z', 'M15.54 8.46a5 5 0 0 1 0 7.07', 'M19.07 4.93a10 10 0 0 1 0 14.14'],
  vazamento: ['M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5S5 13 5 15a7 7 0 0 0 7 7z'],
  limpeza: ['M12 3l1.9 5.8 5.8 1.9-5.8 1.9L12 18.4l-1.9-5.8-5.8-1.9 5.8-1.9z', 'M19 17v4', 'M17 19h4'],
  seguranca: ['M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z'],
  manutencao: ['M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94z'],
  outro: ['M5 12h.01', 'M12 12h.01', 'M19 12h.01'],
  caixa: ['M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z', 'M3.27 6.96 12 12.01l8.73-5.05', 'M12 22.08V12'],
  local: ['M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z', 'M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6z'],
  escanear: ['M3 7V5a2 2 0 0 1 2-2h2', 'M17 3h2a2 2 0 0 1 2 2v2', 'M21 17v2a2 2 0 0 1-2 2h-2', 'M7 21H5a2 2 0 0 1-2-2v-2', 'M7 12h10'],
  link: ['M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71', 'M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71'],
  info: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z', 'M12 16v-4', 'M12 8h.01'],
  alerta: ['M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z', 'M12 8v4', 'M12 16h.01'],
  predio: ['M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18z', 'M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2', 'M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2', 'M10 6h4', 'M10 10h4', 'M10 14h4', 'M10 18h4'],
  instalar: ['M12 15V3', 'm7 10 5 5 5-5', 'M5 21h14'],
  celular: ['M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z', 'M12 18h.01'],
  olho: ['M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7z', 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z'],
  'olho-fechado': ['M9.88 9.88a3 3 0 1 0 4.24 4.24', 'M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68', 'M6.61 6.61A13.53 13.53 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61', 'M2 2l20 20'],
  contas: ['M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1', 'M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4'],
  energia: ['M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z'],
  documento: ['M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z', 'M14 2v4a2 2 0 0 0 2 2h4', 'M10 9H8', 'M16 13H8', 'M16 17H8'],
  recibo: ['M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1z', 'M16 8h-6a2 2 0 1 0 0 4h4a2 2 0 1 1 0 4H8', 'M12 17.5v-11'],
  entrada: ['M17 7 7 17', 'M17 17H7V7'],
  saida: ['M7 7h10v10', 'M7 17 17 7'],
  pacote: ['M11 21.73a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73z', 'M12 22V12', 'm3.3 7 8.7 5 8.7-5', 'm7.5 4.27 9 5.15'],
  enquetes: ['M3 3v16a2 2 0 0 0 2 2h16', 'M7 16h8', 'M7 11h12', 'M7 6h3'],
  telefones: ['M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z'],
  whatsapp: ['M7.9 20A9 9 0 1 0 4 16.1L2 22z'],
  atualizar: ['M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8', 'M3 3v5h5', 'M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16', 'M16 16h5v5'],
};

export function icone(nome, classe = 'icone') {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('class', classe);
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', nome === 'outro' ? '3' : '2');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true');
  for (const d of ICONES[nome] || ICONES.info) {
    const caminho = document.createElementNS(ns, 'path');
    caminho.setAttribute('d', d);
    svg.append(caminho);
  }
  return svg;
}

/** Quadrado arredondado colorido com ícone (cor = nome do módulo). */
export const tile = (nome, cor = nome, extra = '') => h('span', { class: `tile cor-${cor} ${extra}`.trim() }, icone(nome));

export function avatar(nome, tamanho = '') {
  const partes = (nome || '?').trim().split(/\s+/);
  const iniciais = (partes[0][0] + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
  return h('span', { class: `avatar ${tamanho}`.trim(), 'aria-hidden': 'true' }, iniciais);
}

/** Plaquinha amarela com o número da unidade (ou um ícone, para quem não mora no prédio). */
export const placa = (unidade, rotulo = unidade && `Unidade ${unidade}`) => h('span', {
  class: 'placa-unidade', role: rotulo ? 'img' : null, 'aria-label': rotulo || null, 'aria-hidden': rotulo ? null : 'true',
}, unidade || icone('predio'));

/** Celular brasileiro (11 dígitos com DDD) vira link do WhatsApp. */
export function linkWhatsapp(telefone) {
  const digitos = telefone.replace(/\D/g, '').replace(/^55(?=\d{11}$)/, '');
  return digitos.length === 11 && digitos[2] === '9' ? `https://wa.me/55${digitos}` : null;
}

export const pill = (texto, cor = '', extra = '') => h('span', { class: `pill ${cor} ${extra}`.trim() }, texto);

/** Linha de lista: ícone/avatar, título, subtítulo e um final (seta, pílula...). */
export function item({ inicio, titulo, sub, fim, href, onclick, seta = Boolean(href || onclick) }) {
  const tag = href ? 'a' : onclick ? 'button' : 'div';
  return h(tag, { class: 'item', href, onclick, type: tag === 'button' ? 'button' : null },
    inicio,
    h('span', { class: 'item-texto' },
      h('span', { class: 'item-titulo' }, titulo),
      sub && h('span', { class: 'item-sub' }, sub)),
    (fim || seta) && h('span', { class: 'item-fim' }, fim, seta && icone('seta', 'icone seta')));
}

export function cabecalho(titulo, { subtitulo, acao, voltar } = {}) {
  return h('header', { class: 'topo-pagina' },
    voltar && h('a', { class: 'voltar', href: `#/${voltar.rota}` }, icone('voltar'), voltar.texto || 'Voltar'),
    h('div', { class: 'cabecalho-pagina' },
      h('div', {}, h('h1', {}, titulo), subtitulo && h('p', { class: 'subtitulo' }, subtitulo)),
      acao));
}

export function secao(titulo, conteudo, acao) {
  return h('section', { class: 'secao' },
    h('div', { class: 'secao-titulo' }, h('h2', {}, titulo), acao),
    conteudo);
}

export function vazio({ icone: nomeIcone, cor, titulo, texto, acao }) {
  return h('div', { class: 'vazio' },
    tile(nomeIcone, cor || nomeIcone, 'grande'),
    h('h2', {}, titulo),
    texto && h('p', {}, texto),
    acao);
}

export const esqueleto = () => h('div', { class: 'esqueleto', 'aria-busy': 'true', 'aria-label': 'Carregando' },
  h('div', { class: 'esq-faixa' }), h('div', { class: 'esq-grande' }), h('div', { class: 'esq-medio' }), h('div', { class: 'esq-medio' }));

let contadorCampos = 0;

/** Rótulo + controle de formulário + dica opcional. */
export function campo(rotulo, controle, dica) {
  if (!controle.id) controle.id = `campo-${++contadorCampos}`;
  return h('div', { class: 'campo' },
    h('label', { for: controle.id }, rotulo),
    controle,
    dica && (dica instanceof Node ? dica : h('small', { class: 'dica' }, dica)));
}

/** Grupo de opções em cartões (radio). opcoes: [{ valor, rotulo, icone }] */
export function opcoes(nome, lista, { valor, classe = '' } = {}) {
  return h('div', { class: `opcoes ${classe}`.trim(), role: 'radiogroup' },
    lista.map((o) => h('label', { class: 'opcao-cartao' },
      h('input', { type: 'radio', name: nome, value: o.valor, checked: o.valor === valor, required: true }),
      h('span', {}, o.icone && tile(o.icone, o.cor || 'neutra'), o.rotulo))));
}

/** Controle segmentado. Chama aoMudar(valor) e marca o botão ativo. */
export function segmentado(lista, valor, aoMudar) {
  const el = h('div', { class: 'segmentado', role: 'group' });
  el.style.setProperty('--total', lista.length);
  el.style.setProperty('--indice', Math.max(0, lista.findIndex((o) => o.valor === valor)));
  lista.forEach((o, i) => {
    el.append(h('button', {
      type: 'button',
      'aria-pressed': String(o.valor === valor),
      onclick: (e) => {
        el.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', 'false'));
        e.currentTarget.setAttribute('aria-pressed', 'true');
        el.style.setProperty('--indice', i);
        vibrar(6);
        aoMudar(o.valor);
      },
    }, o.rotulo));
  });
  return el;
}

export const erroForm = () => h('p', { class: 'erro-form', role: 'alert' });

/** Liga o envio do formulário a uma ação assíncrona, mostrando erros e travando o botão. */
export function aoEnviar(form, acao) {
  form.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    const botao = form.querySelector('button[type="submit"]');
    const erro = form.querySelector('.erro-form');
    ocupar(botao, true);
    if (erro) erro.textContent = '';
    try {
      await acao(Object.fromEntries(new FormData(form)));
    } catch (e) {
      vibrar([15, 60, 15]);
      if (erro) erro.textContent = e.message;
      else toast(e.message, 'erro');
    } finally {
      ocupar(botao, false);
    }
  });
  return form;
}

/** Envolve um clique assíncrono para mostrar erros como toast. */
export const comErro = (acao) => async (evento) => {
  const botao = evento?.currentTarget;
  ocupar(botao, true);
  try {
    await acao(evento);
  } catch (e) {
    toast(e.message, 'erro');
  } finally {
    if (botao?.isConnected) ocupar(botao, false);
  }
};

/** Trava o botão e, se a ação demorar, mostra o spinner (evita piscar em ações rápidas). */
function ocupar(botao, ocupado) {
  if (!botao || !('disabled' in botao)) return;
  botao.disabled = ocupado;
  clearTimeout(botao.esperaSpinner);
  if (ocupado) botao.esperaSpinner = setTimeout(() => botao.classList.add('carregando'), 150);
  else botao.classList.remove('carregando');
}

/** Vibração curta no Android (ignorada onde não existe). */
export function vibrar(padrao = 10) {
  try { navigator.vibrate?.(padrao); } catch { /* sem suporte */ }
}

const semMovimento = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
export const esperar = (ms) => new Promise((resolver) => setTimeout(resolver, ms));

/** Cobre a tela com a logo no meio (ao entrar na conta). Devolve null para quem pediu menos movimento. */
export function abrirAbertura(texto) {
  if (semMovimento()) return null;
  const el = h('div', { class: 'abertura chegando', role: 'status', 'aria-label': texto },
    h('span', { class: 'logo' }, icone('predio')),
    h('p', { class: 'abertura-texto' }, texto));
  el.dataset.desde = performance.now();
  document.body.append(el);
  return el;
}

/** Faz a logo crescer e sumir, revelando o app, depois de ela ficar ao menos `minimo` ms na tela. */
export async function fecharAbertura(el, minimo = 1200) {
  if (!el?.isConnected || el.dataset.fechando) return;
  el.dataset.fechando = '1';
  if (!el.dataset.desde) {
    try { sessionStorage.setItem('aberturaVista', '1'); } catch { /* sem armazenamento */ }
  }
  if (semMovimento()) return el.remove();
  // Sem `desde`, é a abertura do index.html, que aparece junto com a página.
  await esperar(Math.max(0, minimo - (performance.now() - Number(el.dataset.desde || 0))));
  el.classList.add('saindo');
  await esperar(500);
  el.remove();
}

export function toast(mensagem, tipo = 'ok') {
  document.querySelector('.toast')?.remove();
  const el = h('div', { class: `toast ${tipo}`, role: tipo === 'erro' ? 'alert' : 'status' },
    icone(tipo === 'erro' ? 'alerta' : 'check'), mensagem);
  const sair = () => {
    el.classList.add('saindo');
    setTimeout(() => el.remove(), 350);
  };
  el.addEventListener('click', sair);
  document.body.append(el);
  vibrar(tipo === 'erro' ? [15, 60, 15] : 10);
  setTimeout(sair, 2800);
}

export function confirmar(mensagem, { titulo, botao = 'Confirmar', perigo = false } = {}) {
  return new Promise((resolver) => {
    const dialogo = h('dialog', { class: 'dialogo' },
      h('form', { method: 'dialog' },
        h('div', { class: 'pilha-curta' }, titulo && h('h2', {}, titulo), h('p', { class: titulo ? 'mudo' : '' }, mensagem)),
        h('div', { class: 'acoes dividir' },
          h('button', { class: 'botao', value: 'nao' }, 'Voltar'),
          h('button', { class: `botao ${perigo ? 'perigo' : 'primario'}`, value: 'sim' }, botao))));
    dialogo.addEventListener('close', () => {
      resolver(dialogo.returnValue === 'sim');
      dialogo.remove();
    });
    document.body.append(dialogo);
    dialogo.showModal();
  });
}

export async function copiar(texto) {
  try {
    await navigator.clipboard.writeText(texto);
  } catch {
    const area = h('textarea', { readonly: true }, texto);
    document.body.append(area);
    area.select();
    document.execCommand('copy');
    area.remove();
  }
  toast('Copiado!');
}

/** Datas do servidor vêm em UTC no formato "AAAA-MM-DD HH:MM:SS". */
export const dataServidor = (textoSql) => new Date(textoSql.replace(' ', 'T') + 'Z');

export function quando(textoSql) {
  const data = dataServidor(textoSql);
  const agora = new Date();
  const segundos = (agora - data) / 1000;
  if (segundos < 60) return 'agora';
  if (segundos < 3600) return `há ${Math.floor(segundos / 60)} min`;
  const hora = data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  if (data.toDateString() === agora.toDateString()) return `hoje às ${hora}`;
  const ontem = new Date(agora);
  ontem.setDate(agora.getDate() - 1);
  if (data.toDateString() === ontem.toDateString()) return `ontem às ${hora}`;
  const dia = data.toLocaleDateString('pt-BR', {
    day: 'numeric', month: 'short', year: data.getFullYear() === agora.getFullYear() ? undefined : 'numeric',
  });
  return `${dia} às ${hora}`;
}

export const hora = (textoSql) => dataServidor(textoSql).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });

/** "2026-10-10" -> "sábado, 10 de outubro" (o ano aparece só se não for o atual). */
export function formatarDia(iso, { curto = false } = {}) {
  const data = new Date(`${iso}T12:00:00`);
  return data.toLocaleDateString('pt-BR', {
    weekday: curto ? 'short' : 'long',
    day: 'numeric',
    month: curto ? 'short' : 'long',
    year: data.getFullYear() === new Date().getFullYear() ? undefined : 'numeric',
  });
}

export const maiuscula = (texto) => texto.charAt(0).toUpperCase() + texto.slice(1);

export const primeiroNome = (nome) => nome.trim().split(/\s+/)[0];

export function saudacao() {
  const horaAtual = new Date().getHours();
  return horaAtual < 12 ? 'Bom dia' : horaAtual < 18 ? 'Boa tarde' : 'Boa noite';
}

export const linkTelefone = (telefone) => `tel:${telefone.replace(/[^\d+]/g, '')}`;

/** ABC1D23 -> ABC-1D23 (só para exibição). */
export const formatarPlaca = (placa) => `${placa.slice(0, 3)}-${placa.slice(3)}`;

/** 123456 (centavos) -> "R$ 1.234,56". */
export const dinheiro = (centavos) => (centavos / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

/** "1.234,56" -> 123456. */
export const centavosDe = (texto) => Number(String(texto || '').replace(/\D/g, '')) || 0;

/** Valor em reais enquanto digita, como na maquininha: 1 -> 0,01; 12345 -> 123,45. */
export function mascaraDinheiro(entrada) {
  entrada.addEventListener('input', () => {
    const digitos = entrada.value.replace(/\D/g, '').replace(/^0+/, '').slice(0, 10);
    entrada.value = digitos ? (Number(digitos) / 100).toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '';
  });
  return entrada;
}

export const NOMES_PAPEL = { sindico: 'Síndico', morador: 'Morador', portaria: 'Portaria' };

/** Reduz uma foto do celular para no máximo `lado` pixels e devolve JPEG. */
export async function reduzirFoto(arquivo, lado = 1600, qualidade = 0.82) {
  const bitmap = await createImageBitmap(arquivo).catch(() => {
    throw new Error('Não foi possível abrir esta imagem.');
  });
  const escala = Math.min(1, lado / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * escala);
  canvas.height = Math.round(bitmap.height * escala);
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close?.();
  return new Promise((resolver) => canvas.toBlob(resolver, 'image/jpeg', qualidade));
}

/** Campo de senha com botão de mostrar/ocultar. */
export function campoSenha(rotulo, atributos, dica) {
  const entrada = h('input', { type: 'password', ...atributos });
  const alternar = h('button', { type: 'button', 'aria-label': 'Mostrar senha' }, icone('olho'));
  alternar.addEventListener('click', () => {
    const mostrar = entrada.type === 'password';
    entrada.type = mostrar ? 'text' : 'password';
    alternar.replaceChildren(icone(mostrar ? 'olho-fechado' : 'olho'));
    alternar.setAttribute('aria-label', mostrar ? 'Ocultar senha' : 'Mostrar senha');
    entrada.focus();
  });
  const el = campo(rotulo, entrada, dica);
  const envoltorio = h('div', { class: 'com-acao' });
  entrada.replaceWith(envoltorio);
  envoltorio.append(entrada, alternar);
  return el;
}

/** Formata o telefone enquanto a pessoa digita: (11) 98888-1111. */
export function mascaraTelefone(entrada) {
  entrada.addEventListener('input', () => {
    const d = entrada.value.replace(/\D/g, '').slice(0, 11);
    let v = d;
    if (d.length > 2) v = `(${d.slice(0, 2)}) ${d.slice(2)}`;
    if (d.length > 6) v = `(${d.slice(0, 2)}) ${d.slice(2, d.length > 10 ? 7 : 6)}-${d.slice(d.length > 10 ? 7 : 6)}`;
    entrada.value = v;
  });
  return entrada;
}

/** Deixa o texto em maiúsculas enquanto digita (placas, códigos). */
export function maiusculas(entrada) {
  entrada.addEventListener('input', () => {
    const { selectionStart: inicio, selectionEnd: fim } = entrada;
    entrada.value = entrada.value.toUpperCase();
    entrada.setSelectionRange?.(inicio, fim);
  });
  return entrada;
}

/** Anima um número de 0 até o valor final, só na primeira vez que a tela aparece (depois, mostra direto). */
let jaContou = false;
export function contar(el, alvo, duracao = 700) {
  if (!alvo || jaContou || matchMedia('(prefers-reduced-motion: reduce)').matches) {
    el.textContent = alvo;
    return el;
  }
  const inicio = performance.now();
  const passo = (agora) => {
    const t = Math.min(1, (agora - inicio) / duracao);
    el.textContent = Math.round(alvo * (1 - (1 - t) ** 3));
    if (t < 1) requestAnimationFrame(passo);
  };
  el.textContent = '0';
  requestAnimationFrame(passo);
  setTimeout(() => { jaContou = true; }, 0); // os outros números desta mesma tela também animam
  return el;
}

/** Visualizador de fotos em tela cheia: deslizar, setas do teclado e pontos. */
export function abrirFotos(urls, indice = 0) {
  let atual = indice;
  const imagem = h('img', { alt: '' });
  const contador = h('span');
  const pontos = h('div', { class: 'pontos' }, urls.map(() => h('span')));
  const mostrar = (novo, direcao = 0) => {
    atual = (novo + urls.length) % urls.length;
    imagem.src = urls[atual];
    imagem.alt = `Foto ${atual + 1} de ${urls.length}`;
    contador.textContent = `${atual + 1} de ${urls.length}`;
    [...pontos.children].forEach((p, i) => p.classList.toggle('ativo', i === atual));
    if (direcao) {
      imagem.animate([{ opacity: 0, transform: `translateX(${direcao * 40}px)` }, { opacity: 1, transform: 'none' }],
        { duration: 260, easing: 'cubic-bezier(0.2, 0.8, 0.2, 1)' });
    }
  };
  const varias = urls.length > 1;
  const palco = h('div', { class: 'palco' },
    imagem,
    varias && h('button', { type: 'button', class: 'botao redondo navegar anterior', 'aria-label': 'Foto anterior', onclick: () => mostrar(atual - 1, -1) }, icone('voltar')),
    varias && h('button', { type: 'button', class: 'botao redondo navegar proxima', 'aria-label': 'Próxima foto', onclick: () => mostrar(atual + 1, 1) }, icone('seta')));
  const dialogo = h('dialog', { class: 'visualizador', 'aria-label': 'Fotos', tabindex: '-1' },
    h('div', { class: 'barra' }, contador,
      h('button', { type: 'button', class: 'botao redondo', 'aria-label': 'Fechar', onclick: () => dialogo.close() }, icone('x'))),
    palco,
    varias ? pontos : h('div'));

  // Deslizar: a foto acompanha o dedo; passou de 60px, troca. Para baixo, fecha.
  let x0 = null;
  let y0 = null;
  palco.addEventListener('pointerdown', (e) => { x0 = e.clientX; y0 = e.clientY; });
  palco.addEventListener('pointermove', (e) => {
    if (x0 === null || e.pointerType === 'mouse') return;
    imagem.style.transform = `translate(${e.clientX - x0}px, ${Math.max(0, e.clientY - y0) / 2}px)`;
  });
  const soltar = (e) => {
    if (x0 === null) return;
    const dx = e.clientX - x0;
    const dy = e.clientY - y0;
    x0 = null;
    imagem.style.transform = '';
    if (dy > 120 && Math.abs(dy) > Math.abs(dx)) dialogo.close();
    else if (varias && Math.abs(dx) > 60) mostrar(atual + (dx < 0 ? 1 : -1), dx < 0 ? 1 : -1);
  };
  palco.addEventListener('pointerup', soltar);
  palco.addEventListener('pointercancel', () => { x0 = null; imagem.style.transform = ''; });
  dialogo.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') mostrar(atual + 1, 1);
    if (e.key === 'ArrowLeft') mostrar(atual - 1, -1);
  });
  dialogo.addEventListener('close', () => dialogo.remove());
  mostrar(atual);
  document.body.append(dialogo);
  dialogo.showModal();
  dialogo.focus(); // foco no visualizador (teclado funciona) sem destacar o botão de fechar
}
