import { ErroApi } from './api.js';
import {
  carregarUsuario, definirRenderizador, escolherCondominio, estado, lerLocal, limparSessao,
} from './estado.js';
import { iniciarVerificacao, pararVerificacao } from './notificacoes.js';
import { telaAvisos, telaEditarAviso } from './telas/avisos.js';
import { telaConvite, telaCondominios, telaNovoCondominio } from './telas/condominios.js';
import { telaContas, telaEditarLancamento, telaLancamento } from './telas/contas.js';
import { telaCelular } from './telas/celular.js';
import { telaCriarConta, telaEntrar } from './telas/conta.js';
import { telaInicio } from './telas/inicio.js';
import { telaMenu } from './telas/menu.js';
import { telaMoradores } from './telas/moradores.js';
import { telaNovaOcorrencia, telaOcorrencia, telaOcorrencias } from './telas/ocorrencias.js';
import { telaPasse } from './telas/passe.js';
import { telaPerfil } from './telas/perfil.js';
import { telaPortaria, telaValidarVisita } from './telas/portaria.js';
import { telaAreas, telaEditarArea, telaReservas } from './telas/reservas.js';
import { telaUnidade } from './telas/unidade.js';
import { telaNovaVisita, telaVisita, telaVisitas } from './telas/visitas.js';
import { avatar, esqueleto, fecharAbertura, h, icone, NOMES_PAPEL, vibrar } from './ui.js';

// publico: só para quem não está logado | aberta: qualquer um, sem moldura do app
// condominio: exige um condomínio aberto | papeis: quem pode abrir | aba: item da navegação marcado
const MORADOR_E_SINDICO = ['morador', 'sindico'];
const EQUIPE = ['sindico', 'portaria'];
const ROTAS = [
  { padrao: 'entrar', tela: telaEntrar, publico: true },
  { padrao: 'criar-conta', tela: telaCriarConta, publico: true },
  { padrao: 'passe/:token', tela: telaPasse, aberta: true },
  { padrao: 'celular', tela: telaCelular, aberta: true },
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
  // 'contas/novo' precisa vir antes de 'contas/:id'
  { padrao: 'contas', tela: telaContas, condominio: true, papeis: MORADOR_E_SINDICO, aba: 'contas' },
  { padrao: 'contas/novo', tela: telaEditarLancamento, condominio: true, papeis: ['sindico'], aba: 'contas' },
  { padrao: 'contas/:id', tela: telaLancamento, condominio: true, papeis: MORADOR_E_SINDICO, aba: 'contas' },
  { padrao: 'contas/:id/editar', tela: telaEditarLancamento, condominio: true, papeis: ['sindico'], aba: 'contas' },
  { padrao: 'moradores', tela: telaMoradores, condominio: true, papeis: ['sindico'], aba: 'moradores' },
  { padrao: 'unidade', tela: telaUnidade, condominio: true, aba: 'unidade' },
];

// Navegação. `celular: false` = só no menu lateral do computador; `computador: false` = só na barra inferior.
const NAVEGACAO = {
  morador: [
    { id: 'inicio', rotulo: 'Início' }, { id: 'avisos', rotulo: 'Avisos' }, { id: 'reservas', rotulo: 'Reservas' },
    { id: 'visitas', rotulo: 'Visitas' }, { id: 'ocorrencias', rotulo: 'Ocorrências', celular: false },
    { id: 'contas', rotulo: 'Contas', celular: false }, { id: 'unidade', rotulo: 'Minha unidade', celular: false },
    { id: 'menu', rotulo: 'Menu', computador: false },
  ],
  sindico: [
    { id: 'inicio', rotulo: 'Início' }, { id: 'avisos', rotulo: 'Avisos' }, { id: 'reservas', rotulo: 'Reservas' },
    { id: 'ocorrencias', rotulo: 'Ocorrências' }, { id: 'moradores', rotulo: 'Moradores', celular: false },
    { id: 'visitas', rotulo: 'Visitas', celular: false }, { id: 'portaria', rotulo: 'Portaria', celular: false },
    { id: 'contas', rotulo: 'Contas', celular: false }, { id: 'menu', rotulo: 'Menu', computador: false },
  ],
  portaria: [
    { id: 'portaria', rotulo: 'Portaria' }, { id: 'avisos', rotulo: 'Avisos' }, { id: 'reservas', rotulo: 'Reservas' },
    { id: 'menu', rotulo: 'Menu' },
  ],
};

const raiz = document.getElementById('app');
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
    location.replace(`#/${destino}`);
    return;
  }

  const { rota, params } = achado;
  const comMoldura = Boolean(estado.usuario && !rota.aberta && !rota.publico);
  const direcao = manterRolagem ? null : direcaoEntre(caminhoAnterior, caminho);
  if (direcao && caminhoAnterior !== null) rolagens.set(caminhoAnterior, window.scrollY);
  const rolagemAtual = window.scrollY;

  // Se a tela demorar, mostra o esqueleto em vez de deixar a anterior parada.
  const espera = manterRolagem ? null : setTimeout(() => {
    if (minhaGeracao === geracao && comMoldura) montarNaMoldura(esqueleto(), rota, false);
  }, 160);

  let conteudo;
  try {
    conteudo = await rota.tela(params);
  } catch (e) {
    clearTimeout(espera);
    if (e instanceof ErroApi && e.status === 401 && !rota.aberta) {
      limparSessao();
      pararVerificacao();
      location.replace('#/entrar');
      return;
    }
    conteudo = cartaoFalha(e);
  }
  clearTimeout(espera);
  if (minhaGeracao !== geracao) return; // o usuário já navegou para outra tela

  const aplicar = (animarCascata) => {
    if (comMoldura) {
      montarNaMoldura(conteudo, rota, animarCascata);
    } else {
      moldura = null;
      raiz.replaceChildren(conteudo);
    }
    const alvo = manterRolagem ? rolagemAtual : direcao === 'voltar' ? rolagens.get(caminho) || 0 : 0;
    window.scrollTo(0, alvo);
    observarTitulo();
    atualizarBarraTopo();
    fecharAbertura(document.querySelector('.abertura'));
  };

  const mesmaMoldura = comMoldura && moldura?.el.isConnected && moldura.chave === chaveMoldura();
  if (direcao && mesmaMoldura && document.startViewTransition && !reduzirMovimento()) {
    document.documentElement.dataset.direcao = direcao;
    const transicao = document.startViewTransition(() => aplicar(false));
    transicao.finished.finally(() => delete document.documentElement.dataset.direcao);
  } else {
    aplicar(!manterRolagem && !reduzirMovimento());
  }
  caminhoAnterior = caminho;
}

function montarNaMoldura(conteudo, rota, animarCascata) {
  const chave = chaveMoldura();
  if (!moldura || moldura.chave !== chave || !moldura.el.isConnected) {
    moldura = criarMoldura(chave);
    raiz.replaceChildren(moldura.el);
  }
  moldura.nav?.querySelectorAll('.nav-item').forEach((link) => {
    if (link.dataset.aba === rota.aba) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  moldura.el.querySelector('.seletor-condominio')?.classList.toggle('aberto', rota.padrao === 'condominios');
  moldura.main.classList.remove('cascata');
  moldura.main.replaceChildren(conteudo);
  if (animarCascata) {
    void moldura.main.offsetWidth; // reinicia a animação
    moldura.main.classList.add('cascata');
  }
}

function criarMoldura(chave) {
  const membro = estado.membro;
  const itens = membro ? NAVEGACAO[membro.papel].filter((i) => i.id !== 'unidade' || membro.unidade_id) : [];
  const nav = itens.length > 0 ? h('nav', { class: 'nav', 'aria-label': 'Navegação principal' },
    h('div', { class: 'marca' }, h('span', { class: 'logo' }, icone('predio')), 'Meu Prédio'),
    itens.map((item) => h('a', {
      class: `nav-item${item.celular === false ? ' so-computador' : ''}${item.computador === false ? ' so-celular' : ''}`,
      href: `#/${item.id}`,
      'data-aba': item.id,
    },
    h('span', { class: 'nav-icone' }, icone(item.id)),
    h('span', {}, item.rotulo),
    item.id === 'avisos' && h('span', { class: 'nav-contador', id: 'contador-avisos', hidden: !estado.naoLidos },
      estado.naoLidos > 9 ? '9+' : estado.naoLidos))),
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
    h('a', { href: '#/perfil', 'aria-label': 'Meu perfil' }, avatar(estado.usuario.nome, 'pequeno')));

  const main = h('main', { class: 'conteudo' });
  const el = h('div', { class: nav ? 'app com-nav' : 'app' }, nav, topo, main);
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
  else location.hash = `/${telaPadrao()}`;
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

function atualizarBarraTopo() {
  document.querySelector('.barra-topo')?.classList.toggle('rolada', window.scrollY > 4);
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
window.addEventListener('hashchange', () => renderizar());
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
