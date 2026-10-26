import {
  ErroApi, limparCache, preCarregar, quandoMudar, rastrearLeituras, revalidar,
} from './api.js';
import {
  carregarUsuario, definirRenderizador, escolherCondominio, estado, irPara, lerLocal, limparSessao,
} from './estado.js';
import { iniciarVerificacao, pararVerificacao, pintarContadores } from './notificacoes.js';
import { telaAvisos, telaEditarAviso } from './telas/avisos.js';
import { telaConvite, telaCondominios, telaNovoCondominio } from './telas/condominios.js';
import { telaContas, telaEditarLancamento, telaLancamento } from './telas/contas.js';
import { telaTaxas } from './telas/taxas.js';
import { telaEncomendas } from './telas/encomendas.js';
import { telaEnquetes, telaNovaEnquete } from './telas/enquetes.js';
import { telaTelefones } from './telas/telefones.js';
import { telaCelular } from './telas/celular.js';
import {
  telaCriarConta, telaEntrar, telaEsqueci, telaNovaSenha,
} from './telas/conta.js';
import { telaHistorico } from './telas/historico.js';
import { telaInicio } from './telas/inicio.js';
import { telaPrivacidade, telaTermos } from './telas/legal.js';
import { telaMenu } from './telas/menu.js';
import { telaMoradores } from './telas/moradores.js';
import { telaNovaOcorrencia, telaOcorrencia, telaOcorrencias } from './telas/ocorrencias.js';
import { telaPasse } from './telas/passe.js';
import { telaPerfil } from './telas/perfil.js';
import { telaPortaria, telaValidarVisita } from './telas/portaria.js';
import { telaAreas, telaEditarArea, telaReservas } from './telas/reservas.js';
import { telaUnidade } from './telas/unidade.js';
import { telaNovaVisita, telaVisita, telaVisitas } from './telas/visitas.js';
import {
  aplicarPeriodo, avatar, esqueleto, fecharAbertura, h, icone, NOMES_PAPEL, vibrar,
} from './ui.js';

// publico: só para quem não está logado | aberta: qualquer um, sem moldura do app
// condominio: exige um condomínio aberto | papeis: quem pode abrir | aba: item da navegação marcado
const MORADOR_E_SINDICO = ['morador', 'sindico'];
const EQUIPE = ['sindico', 'portaria'];
const ROTAS = [
  { padrao: 'entrar', tela: telaEntrar, publico: true },
  { padrao: 'criar-conta', tela: telaCriarConta, publico: true },
  { padrao: 'esqueci', tela: telaEsqueci, publico: true },
  { padrao: 'nova-senha/:token', tela: telaNovaSenha, publico: true },
  { padrao: 'passe/:token', tela: telaPasse, aberta: true },
  { padrao: 'celular', tela: telaCelular, aberta: true },
  { padrao: 'termos', tela: telaTermos, aberta: true },
  { padrao: 'privacidade', tela: telaPrivacidade, aberta: true },
  { padrao: 'condominios', tela: telaCondominios },
  { padrao: 'novo-condominio', tela: telaNovoCondominio },
  { padrao: 'convite', tela: telaConvite },
  { padrao: 'convite/:codigo', tela: telaConvite },
  { padrao: 'perfil', tela: telaPerfil, aba: 'menu' },
  { padrao: 'menu', tela: telaMenu, condominio: true, aba: 'menu' },
  { padrao: 'inicio', tela: telaInicio, condominio: true, papeis: MORADOR_E_SINDICO, aba: 'inicio' },
  { padrao: 'avisos', tela: telaAvisos, condominio: true, aba: 'avisos' },
  { padrao: 'avisos/novo', tela: telaEditarAviso, condominio: true, papeis: ['sindico'], aba: 'avisos' },
  { padrao: 'avisos/:id/editar', tela: telaEditarAviso, condominio: true, papeis: ['sindico'], aba: 'avisos' },
  // 'reservas/areas' precisa vir antes de 'reservas/:area'
  { padrao: 'reservas', tela: telaReservas, condominio: true, aba: 'reservas' },
  { padrao: 'reservas/areas', tela: telaAreas, condominio: true, papeis: ['sindico'], aba: 'reservas' },
  { padrao: 'reservas/areas/nova', tela: telaEditarArea, condominio: true, papeis: ['sindico'], aba: 'reservas' },
  { padrao: 'reservas/areas/:id/editar', tela: telaEditarArea, condominio: true, papeis: ['sindico'], aba: 'reservas' },
  { padrao: 'reservas/:area', tela: telaReservas, condominio: true, aba: 'reservas' },
  { padrao: 'ocorrencias', tela: telaOcorrencias, condominio: true, aba: 'ocorrencias' },
  { padrao: 'ocorrencias/nova', tela: telaNovaOcorrencia, condominio: true, aba: 'ocorrencias' },
  { padrao: 'ocorrencias/:id', tela: telaOcorrencia, condominio: true, aba: 'ocorrencias' },
  { padrao: 'visitas', tela: telaVisitas, condominio: true, papeis: MORADOR_E_SINDICO, aba: 'visitas' },
  { padrao: 'visitas/nova', tela: telaNovaVisita, condominio: true, papeis: MORADOR_E_SINDICO, aba: 'visitas' },
  { padrao: 'visitas/:id', tela: telaVisita, condominio: true, papeis: MORADOR_E_SINDICO, aba: 'visitas' },
  { padrao: 'portaria', tela: telaPortaria, condominio: true, papeis: EQUIPE, aba: 'portaria' },
  { padrao: 'portaria/v/:token', tela: telaValidarVisita, aba: 'portaria' },
  // 'contas/novo' e 'contas/taxas' precisam vir antes de 'contas/:id'
  { padrao: 'contas', tela: telaContas, condominio: true, papeis: MORADOR_E_SINDICO, aba: 'contas' },
  { padrao: 'contas/taxas', tela: telaTaxas, condominio: true, papeis: MORADOR_E_SINDICO, aba: 'contas' },
  { padrao: 'contas/novo', tela: telaEditarLancamento, condominio: true, papeis: ['sindico'], aba: 'contas' },
  { padrao: 'contas/:id', tela: telaLancamento, condominio: true, papeis: MORADOR_E_SINDICO, aba: 'contas' },
  { padrao: 'contas/:id/editar', tela: telaEditarLancamento, condominio: true, papeis: ['sindico'], aba: 'contas' },
  { padrao: 'moradores', tela: telaMoradores, condominio: true, papeis: ['sindico'], aba: 'moradores' },
  { padrao: 'unidade', tela: telaUnidade, condominio: true, aba: 'unidade' },
  { padrao: 'encomendas', tela: telaEncomendas, condominio: true, aba: 'encomendas' },
  { padrao: 'enquetes', tela: telaEnquetes, condominio: true, papeis: MORADOR_E_SINDICO, aba: 'enquetes' },
  { padrao: 'enquetes/nova', tela: telaNovaEnquete, condominio: true, papeis: ['sindico'], aba: 'enquetes' },
  { padrao: 'telefones', tela: telaTelefones, condominio: true, aba: 'telefones' },
  { padrao: 'historico', tela: telaHistorico, condominio: true, papeis: ['sindico'], aba: 'historico' },
];

// Navegação. A barra de baixo (celular) mostra o que cada perfil mais usa; o resto fica na grade do Início
// e em "Mais". `celular: false` = só no menu lateral do computador; `computador: false` = só na barra de baixo.
const NAVEGACAO = {
  morador: [
    { id: 'inicio', rotulo: 'Início' }, { id: 'avisos', rotulo: 'Avisos' }, { id: 'reservas', rotulo: 'Reservas' },
    { id: 'visitas', rotulo: 'Visitas' }, { id: 'encomendas', rotulo: 'Encomendas', celular: false },
    { id: 'enquetes', rotulo: 'Enquetes', celular: false }, { id: 'ocorrencias', rotulo: 'Ocorrências', celular: false },
    { id: 'contas', rotulo: 'Contas', celular: false }, { id: 'unidade', rotulo: 'Minha unidade', celular: false },
    { id: 'telefones', rotulo: 'Telefones úteis', celular: false }, { id: 'menu', rotulo: 'Mais', computador: false },
  ],
  sindico: [
    { id: 'inicio', rotulo: 'Início' }, { id: 'avisos', rotulo: 'Avisos' }, { id: 'contas', rotulo: 'Contas' },
    { id: 'moradores', rotulo: 'Moradores' }, { id: 'reservas', rotulo: 'Reservas', celular: false },
    { id: 'ocorrencias', rotulo: 'Ocorrências', celular: false }, { id: 'visitas', rotulo: 'Visitas', celular: false },
    { id: 'portaria', rotulo: 'Portaria', celular: false }, { id: 'encomendas', rotulo: 'Encomendas', celular: false },
    { id: 'enquetes', rotulo: 'Enquetes', celular: false }, { id: 'telefones', rotulo: 'Telefones úteis', celular: false },
    { id: 'historico', rotulo: 'Histórico', celular: false }, { id: 'menu', rotulo: 'Mais', computador: false },
  ],
  portaria: [
    { id: 'portaria', rotulo: 'Portaria' }, { id: 'encomendas', rotulo: 'Encomendas' }, { id: 'avisos', rotulo: 'Avisos' },
    { id: 'reservas', rotulo: 'Reservas', celular: false }, { id: 'telefones', rotulo: 'Telefones úteis', celular: false },
    { id: 'menu', rotulo: 'Mais', computador: false },
  ],
};

const raiz = document.getElementById('app');

// Foto do topo conforme a hora: aplica já (antes da primeira tela) e confere a cada minuto e ao voltar ao app.
aplicarPeriodo();
setInterval(aplicarPeriodo, 60_000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) aplicarPeriodo(); });
let sessaoVerificada = false;
let geracao = 0;

function casarRota(caminho) {
  const partes = caminho.split('/').filter(Boolean);
  for (const rota of ROTAS) {
    const segmentos = rota.padrao.split('/');
    if (segmentos.length !== partes.length) continue;
    const params = {};
    const casou = segmentos.every((seg, i) => {
      if (seg.startsWith(':')) {
        params[seg.slice(1)] = decodeURIComponent(partes[i]);
        return true;
      }
      return seg === partes[i];
    });
    if (casou) return { rota, params };
  }
  return null;
}

function selecionarCondominio() {
  const ativos = estado.condominios.filter((c) => c.status === 'ativo');
  const salvo = Number(lerLocal('condominioAtual'));
  estado.membro = ativos.find((c) => c.condominio_id === salvo) || ativos[0] || null;
  if (estado.membro) {
    escolherCondominio(estado.membro.condominio_id);
    iniciarVerificacao(estado.membro.condominio_id);
  } else {
    pararVerificacao();
  }
}

const telaPadrao = () => {
  if (!estado.membro) return 'condominios';
  return estado.membro.papel === 'portaria' ? 'portaria' : 'inicio';
};

function tirarDestinoGuardado() {
  const destino = sessionStorage.getItem('depoisDoLogin');
  sessionStorage.removeItem('depoisDoLogin');
  return destino;
}

/** Devolve para onde redirecionar, ou null se a rota pode ser aberta. */
function redirecionamento(achado, caminho) {
  if (achado?.rota.aberta) return null;
  if (!estado.usuario) {
    if (achado?.rota.publico) return null;
    if (achado) sessionStorage.setItem('depoisDoLogin', caminho);
    return 'entrar';
  }
  if (!achado || achado.rota.publico) return tirarDestinoGuardado() || telaPadrao();
  const { rota } = achado;
  if (rota.condominio && !estado.membro) return 'condominios';
  if (rota.papeis && !rota.papeis.includes(estado.membro.papel)) return telaPadrao();
  if (rota.aba === 'unidade' && !estado.membro.unidade_id) return telaPadrao();
  return null;
}

// --- Renderização ------------------------------------------------------------------
// A moldura (topo + navegação) é criada uma vez e reaproveitada; só o conteúdo troca,
// com uma transição que indica a direção (avançar, voltar ou trocar de aba).

let moldura = null; // { chave, el, main, nav }
let leiturasDaTela = new Set(); // dados que a tela atual usou (para redesenhar se mudarem)
let caminhoAnterior = null;
let origemSeletor = null; // tela de onde o seletor de condomínio foi aberto, para fechá-lo no segundo toque
const rolagens = new Map(); // posição de rolagem de cada tela, para restaurar ao voltar
const profundidade = (caminho) => caminho.split('/').filter(Boolean).length;
const reduzirMovimento = () => matchMedia('(prefers-reduced-motion: reduce)').matches;

function direcaoEntre(anterior, atual) {
  if (anterior === null || anterior === atual) return null;
  const a = profundidade(anterior);
  const b = profundidade(atual);
  return b > a ? 'avancar' : b < a ? 'voltar' : 'lado';
}

const chaveMoldura = () => {
  const m = estado.membro;
  return [estado.usuario.id, estado.usuario.nome, m?.membro_id, m?.papel, m?.unidade_id, m?.condominio].join('|');
};

async function renderizar({ manterRolagem = false } = {}) {
  const minhaGeracao = ++geracao;
  // Trocar de tela (inclusive pelo botão voltar) fecha fotos e confirmações abertas.
  if (!manterRolagem) document.querySelectorAll('dialog[open]').forEach((d) => d.close());
  if (!sessaoVerificada) {
    try {
      await carregarUsuario();
    } catch (e) {
      if (!(e instanceof ErroApi && e.status === 401)) return mostrarFalha(e);
    }
    sessaoVerificada = true;
  }
  if (estado.usuario) selecionarCondominio();

  const caminho = location.hash.replace(/^#\/?/, '');
  if (caminho !== 'condominios') origemSeletor = null;
  const achado = casarRota(caminho);
  const destino = redirecionamento(achado, caminho);
  if (destino !== null) {
    irPara(destino, { substituir: true });
    return;
  }

  const { rota, params } = achado;
  const comMoldura = Boolean(estado.usuario && !rota.aberta && !rota.publico);
  const direcao = manterRolagem ? null : direcaoEntre(caminhoAnterior, caminho);
  if (direcao && caminhoAnterior !== null) rolagens.set(caminhoAnterior, window.scrollY);
  const rolagemAtual = window.scrollY;

  // Se a tela demorar, mostra o esqueleto em vez de deixar a anterior parada.
  // Com os dados em cache a tela vem na hora e o esqueleto nem aparece.
  const espera = manterRolagem ? null : setTimeout(() => {
    if (minhaGeracao === geracao && comMoldura) montarNaMoldura(esqueleto(), rota);
  }, 250);

  let conteudo;
  const leituras = rastrearLeituras();
  try {
    conteudo = await rota.tela(params);
  } catch (e) {
    clearTimeout(espera);
    if (e instanceof ErroApi && e.status === 401 && !rota.aberta) {
      limparSessao();
      pararVerificacao();
      irPara('entrar', { substituir: true });
      return;
    }
    conteudo = cartaoFalha(e);
  }
  clearTimeout(espera);
  if (minhaGeracao !== geracao) return; // o usuário já navegou para outra tela
  leiturasDaTela = leituras;

  if (comMoldura) {
    const alvo = manterRolagem ? rolagemAtual : direcao === 'voltar' ? rolagens.get(caminho) || 0 : 0;
    montarNaMoldura(conteudo, rota);
    window.scrollTo(0, alvo);
    if (direcao && !reduzirMovimento()) animarEntrada(moldura.main, direcao);
  } else {
    moldura = null;
    raiz.replaceChildren(conteudo);
    window.scrollTo(0, 0);
  }
  observarTitulo();
  atualizarBarraTopo();
  fecharAbertura(document.querySelector('.abertura'));
  if (comMoldura) agendarPreCarga();
  caminhoAnterior = caminho;
}

/** Dados mudaram no servidor: redesenha a tela atual sem animação, se a pessoa não estiver no meio de algo. */
let redesenhoPendente = null;
quandoMudar((caminho) => {
  if (!leiturasDaTela.has(caminho)) return;
  clearTimeout(redesenhoPendente);
  redesenhoPendente = setTimeout(() => {
    const ocupada = document.querySelector('dialog[open], .conteudo form')
      || document.activeElement?.matches('input, textarea, select');
    if (!ocupada) renderizar({ manterRolagem: true });
  }, 60);
});

// Os contadores do menu mudaram (chegou algo novo): busca de novo o que a tela aberta mostra.
// Se os dados vierem diferentes, o quandoMudar acima redesenha a tela.
window.addEventListener('contadores-mudaram', () => {
  leiturasDaTela.forEach(revalidar);
});

/** Depois que a primeira tela aparece, busca em segundo plano os dados das abas principais. */
let preCarregado = null;
function agendarPreCarga() {
  const membro = estado.membro;
  if (!membro || preCarregado === membro.membro_id) return;
  preCarregado = membro.membro_id;
  const base = `/api/condominios/${membro.condominio_id}`;
  const morador = membro.papel !== 'portaria';
  const caminhos = [
    `${base}/avisos`, `${base}/areas`, `${base}/reservas/proximas`, `${base}/ocorrencias`,
    morador && `${base}/painel`, morador && `${base}/visitas`, morador && `${base}/contas`,
    membro.papel === 'sindico' && `${base}/taxas`, membro.papel === 'sindico' && `${base}/cadastro`,
    membro.papel === 'sindico' && base,
    membro.papel === 'morador' && membro.unidade_id && `${base}/taxas/minha`,
    membro.unidade_id && `${base}/veiculos`,
    `${base}/encomendas`, `${base}/telefones`, morador && `${base}/enquetes`,
  ].filter(Boolean);
  const quandoOcioso = window.requestIdleCallback || ((f) => setTimeout(f, 300));
  quandoOcioso(async () => {
    const [, areas] = await preCarregar(caminhos);
    // O calendário de Reservas abre na primeira área, no mês atual.
    if (areas?.areas.length) preCarregar([`${base}/reservas?area_id=${areas.areas[0].id}&mes=${areas.hoje.slice(0, 7)}`]);
  });
}

/** Troca o conteúdo dentro da moldura (cabeçalho e navegação continuam os mesmos). */
function montarNaMoldura(conteudo, rota) {
  const chave = chaveMoldura();
  if (!moldura || moldura.chave !== chave || !moldura.el.isConnected) {
    moldura = criarMoldura(chave);
    raiz.replaceChildren(moldura.el);
  }
  moldura.nav?.querySelectorAll('.nav-item').forEach((link) => {
    if (link.dataset.aba === rota.aba) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  posicionarIndicador();
  moldura.el.querySelector('.seletor-condominio')?.classList.toggle('aberto', rota.padrao === 'condominios');
  // No Início, a barra do topo fica transparente sobre a foto do condomínio (até rolar a tela).
  moldura.el.classList.toggle('tela-inicio', rota.padrao === 'inicio');
  moldura.main.replaceChildren(conteudo);
}

/** Celular: a pílula azul-clara da barra de baixo desliza até a aba aberta. */
function posicionarIndicador() {
  const indicador = moldura?.nav?.querySelector('.nav-indicador');
  if (!indicador) return;
  const ativo = moldura.nav.querySelector('.nav-item[aria-current="page"] .nav-icone');
  if (!ativo?.offsetParent || getComputedStyle(indicador).display === 'none') {
    indicador.classList.remove('visivel');
    return;
  }
  const base = moldura.nav.getBoundingClientRect();
  const alvo = ativo.getBoundingClientRect();
  // Uma pílula atrás do ícone da aba aberta, da largura dele.
  Object.assign(indicador.style, {
    width: `${alvo.width}px`,
    transform: `translateX(${alvo.left - base.left}px)`,
  });
  if (!indicador.classList.contains('visivel')) {
    // Primeira vez (ou depois de sumir): aparece direto no lugar, sem deslizar de longe.
    indicador.classList.add('sem-transicao', 'visivel');
    void indicador.offsetWidth;
    indicador.classList.remove('sem-transicao');
  }
}
window.addEventListener('resize', posicionarIndicador);

function criarMoldura(chave) {
  const membro = estado.membro;
  const itens = membro ? NAVEGACAO[membro.papel].filter((i) => i.id !== 'unidade' || membro.unidade_id) : [];
  const nav = itens.length > 0 ? h('nav', { class: 'nav', 'aria-label': 'Navegação principal' },
    h('span', { class: 'nav-indicador', 'aria-hidden': 'true' }),
    h('div', { class: 'marca' }, h('span', { class: 'logo' }, icone('predio')), 'Meu Prédio'),
    itens.map((item) => h('a', {
      class: `nav-item${item.celular === false ? ' so-computador' : ''}${item.computador === false ? ' so-celular' : ''}`,
      href: `#/${item.id}`,
      'data-aba': item.id,
    },
    h('span', { class: 'nav-icone' }, icone({ encomendas: 'pacote', historico: 'relogio' }[item.id] || item.id)),
    h('span', {}, item.rotulo),
    // Número do que pede atenção; no "Mais" do celular, a soma das abas que só aparecem lá.
    h('span', {
      class: 'nav-contador',
      'data-contador': item.id,
      'data-soma': item.id === 'menu' ? itens.filter((i) => i.celular === false).map((i) => i.id).join(',') : null,
      hidden: true,
    }))),
    h('a', { class: 'nav-perfil', href: '#/perfil' },
      avatar(estado.usuario.nome, 'pequeno'),
      h('span', { class: 'item-texto' },
        h('span', {}, estado.usuario.nome),
        h('span', {}, [NOMES_PAPEL[membro.papel], membro.unidade].filter(Boolean).join(' · '))))) : null;

  // Tocar na aba em que já está leva ao topo, como nos apps nativos.
  nav?.addEventListener('click', (evento) => {
    const link = evento.target.closest('.nav-item');
    if (link && link.getAttribute('href') === location.hash) {
      evento.preventDefault();
      window.scrollTo({ top: 0, behavior: reduzirMovimento() ? 'auto' : 'smooth' });
    } else if (link) {
      vibrar(6);
    }
  });

  const subtitulo = membro && [NOMES_PAPEL[membro.papel], membro.unidade].filter(Boolean).join(' · ');
  const topo = h('header', { class: 'barra-topo' },
    h('a', { class: 'seletor-condominio', href: '#/condominios', 'aria-label': 'Trocar de condomínio', onclick: alternarSeletor },
      h('span', { class: 'logo' }, icone('predio')),
      h('div', { class: 'textos' },
        h('div', { class: 'nome' }, membro ? membro.condominio : 'Meu Prédio'),
        subtitulo && h('div', { class: 'papel' }, subtitulo)),
      membro && icone('abaixo', 'icone fraco')),
    h('div', { class: 'titulo-topo', 'aria-hidden': 'true' }),
    h('span', { class: 'espaco' }),
    // No celular, o avatar abre "Mais" (perfil no topo, todos os módulos e a conta), que fica destacado na barra.
    h('a', { href: membro ? '#/menu' : '#/perfil', 'aria-label': 'Meu perfil e mais opções' }, avatar(estado.usuario.nome, 'pequeno')));

  const main = h('main', { class: 'conteudo' });
  const el = h('div', { class: nav ? 'app com-nav' : 'app' }, nav, topo, main);
  queueMicrotask(pintarContadores); // a moldura nova já nasce com os números conhecidos
  return { chave, el, main, nav };
}

/** O seletor de condomínio abre a lista no primeiro toque e, no segundo, volta para onde estava. */
function alternarSeletor(evento) {
  if (location.hash !== '#/condominios') {
    origemSeletor = location.hash;
    return;
  }
  if (!estado.membro) return; // sem condomínio aberto, a lista é a única tela
  evento.preventDefault();
  if (origemSeletor) history.back();
  else irPara(telaPadrao());
}

// O título grande da página "sobe" para a barra superior quando sai da tela.
let observadorTitulo = null;
function observarTitulo() {
  observadorTitulo?.disconnect();
  const topo = document.querySelector('.barra-topo');
  if (!topo) return;
  topo.classList.remove('com-titulo');
  const titulo = document.querySelector('.conteudo .cabecalho-pagina h1');
  const destino = topo.querySelector('.titulo-topo');
  destino.textContent = titulo ? titulo.textContent : '';
  if (!titulo) return;
  observadorTitulo = new IntersectionObserver(([entrada]) => {
    topo.classList.toggle('com-titulo', !entrada.isIntersecting && entrada.boundingClientRect.top < 100);
  }, { rootMargin: '-64px 0px 0px 0px' });
  observadorTitulo.observe(titulo);
}

function cartaoFalha(erro) {
  return h('div', { class: 'vazio' },
    h('span', { class: 'tile grande cor-ocorrencias' }, icone('alerta')),
    h('h2', {}, 'Não foi possível carregar'),
    h('p', {}, erro.message),
    h('button', { class: 'botao primario', onclick: () => renderizar() }, 'Tentar de novo'));
}

function mostrarFalha(erro) {
  moldura = null;
  raiz.replaceChildren(h('main', { class: 'conteudo' }, cartaoFalha(erro)));
  fecharAbertura(document.querySelector('.abertura'));
}

/** A tela nova entra deslizando (avançar/voltar) ou surgindo (troca de aba). Só posição e transparência,
 * que o celular desenha sem refazer a página. A classe sai no fim para não deixar nada transformado. */
function animarEntrada(main, direcao) {
  main.classList.remove('entra-avancar', 'entra-voltar', 'entra-lado');
  void main.offsetWidth;
  main.classList.add(`entra-${direcao}`);
  main.addEventListener('animationend', () => main.classList.remove(`entra-${direcao}`), { once: true });
}

// Ao rolar, só mexe na barra do topo quando ela muda de estado (e no máximo uma vez por quadro).
let quadroPedido = false;
function atualizarBarraTopo() {
  if (quadroPedido) return;
  quadroPedido = true;
  requestAnimationFrame(() => {
    quadroPedido = false;
    const rolada = window.scrollY > 4;
    const barra = document.querySelector('.barra-topo');
    if (barra && barra.classList.contains('rolada') !== rolada) barra.classList.toggle('rolada', rolada);
  });
}

/** Puxar para atualizar (celular): arrastar para baixo no topo da página recarrega a tela. */
function instalarPuxarParaAtualizar() {
  const indicador = h('div', { class: 'puxar', 'aria-hidden': 'true' }, icone('atualizar'));
  document.body.append(indicador);
  const LIMITE = 70;
  let inicioY = null;
  let puxado = 0;
  let ocupado = false;

  const soltar = () => {
    indicador.classList.add('solto');
    indicador.style.transform = '';
    indicador.style.opacity = '';
  };
  window.addEventListener('touchstart', (e) => {
    const podePuxar = !ocupado && window.scrollY <= 0 && moldura?.el.isConnected && !document.querySelector('dialog[open]');
    inicioY = podePuxar ? e.touches[0].clientY : null;
    puxado = 0;
    indicador.classList.remove('solto');
  }, { passive: true });
  window.addEventListener('touchmove', (e) => {
    if (inicioY === null) return;
    puxado = window.scrollY > 0 ? 0 : Math.min(110, Math.max(0, e.touches[0].clientY - inicioY) * 0.5);
    indicador.style.transform = `translateY(${puxado - 60}px) rotate(${puxado * 4}deg)`;
    indicador.style.opacity = Math.min(1, puxado / 40);
  }, { passive: true });
  window.addEventListener('touchend', async () => {
    if (inicioY === null) return;
    inicioY = null;
    if (puxado < LIMITE) return soltar();
    ocupado = true;
    vibrar(10);
    indicador.classList.add('solto', 'atualizando');
    indicador.style.transform = 'translateY(14px)';
    try {
      limparCache(); // puxar para atualizar sempre busca tudo de novo
      await carregarUsuario().catch(() => {});
      await renderizar({ manterRolagem: true });
    } finally {
      ocupado = false;
      indicador.classList.remove('atualizando');
      soltar();
    }
  });
}

definirRenderizador(renderizar);
// Links internos (href="#/...") trocam de tela pela API de histórico, sem navegação do navegador.
document.addEventListener('click', (evento) => {
  if (evento.defaultPrevented || evento.button !== 0 || evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey) return;
  const link = evento.target.closest?.('a[href^="#/"]');
  if (!link || link.target || link.hasAttribute('download')) return;
  evento.preventDefault();
  if (link.getAttribute('href') !== location.hash) irPara(link.getAttribute('href').slice(2));
});

// Voltar/avançar do aparelho e endereço digitado à mão. Os dois eventos podem vir juntos: desenha uma vez.
let desenhoAgendado = false;
const desenharAgora = () => {
  if (desenhoAgendado) return;
  desenhoAgendado = true;
  queueMicrotask(() => {
    desenhoAgendado = false;
    renderizar();
  });
};
window.addEventListener('popstate', desenharAgora);
window.addEventListener('hashchange', desenharAgora);
window.addEventListener('scroll', atualizarBarraTopo, { passive: true });
window.addEventListener('beforeinstallprompt', (evento) => {
  evento.preventDefault();
  estado.pedidoInstalacao = evento;
});
if ('ontouchstart' in window) instalarPuxarParaAtualizar();
renderizar();

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}
