import { api } from './api.js';
import { estado, gravarLocal, lerLocal } from './estado.js';

// Contadores das abas (barra de baixo e menu lateral) quase em tempo real: com o app na tela, consulta
// a cada 10 s; em segundo plano, a cada minuto (para a notificação de aviso novo). Também consulta na hora
// ao voltar para o app e logo depois de qualquer ação da pessoa (evento "dados-mudaram", em api.js).
// Notificação com o app fechado exige Web Push.
const NA_TELA = 10_000;
const EM_SEGUNDO_PLANO = 60_000;

let timer = null;
let condominioVerificado = null;

export function iniciarVerificacao(condominioId) {
  if (condominioId === condominioVerificado) return;
  pararVerificacao();
  condominioVerificado = condominioId;
  verificar();
}

export function pararVerificacao() {
  clearTimeout(timer);
  timer = null;
  condominioVerificado = null;
  estado.contadores = {};
  pintarContadores();
}

function agendar(espera) {
  clearTimeout(timer);
  if (condominioVerificado) timer = setTimeout(verificar, espera);
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) verificar();
});
window.addEventListener('dados-mudaram', () => agendar(50)); // junta várias gravações seguidas numa consulta só

async function verificar() {
  const cid = condominioVerificado;
  if (!cid) return;
  agendar(document.hidden ? EM_SEGUNDO_PLANO : NA_TELA);
  let resposta;
  try {
    // Direto no servidor (sem o cache das telas): é só para os números do menu.
    resposta = await api('GET', `/api/condominios/${cid}/contadores`);
  } catch {
    return;
  }
  if (cid !== condominioVerificado) return;
  const mudou = JSON.stringify(resposta.abas) !== JSON.stringify(estado.contadores);
  const primeira = !Object.keys(estado.contadores || {}).length;
  estado.contadores = resposta.abas;
  pintarContadores();
  // Algo novo no condomínio: a tela aberta busca os próprios dados de novo (ver app.js).
  if (mudou && !primeira) window.dispatchEvent(new Event('contadores-mudaram'));

  const ultimo = resposta.ultimo_aviso;
  if (!ultimo) return;
  const chave = `ultimoAvisoNotificado:${cid}`;
  const anterior = Number(lerLocal(chave) || 0);
  if (ultimo.id <= anterior) return;
  gravarLocal(chave, ultimo.id);
  // Na primeira verificação só registra; e não notifica quem está com o app na tela.
  if (anterior && document.hidden) mostrarNotificacao(ultimo.titulo);
}

/** Uma aba pode mostrar o próprio número (data-contador) ou a soma de outras (data-soma, usado no "Mais"). */
export function pintarContadores() {
  const abas = estado.contadores || {};
  let total = 0;
  for (const valor of Object.values(abas)) total += valor || 0;
  document.querySelectorAll('.nav-contador').forEach((el) => {
    const ids = el.dataset.soma ? el.dataset.soma.split(',') : [el.dataset.contador];
    const n = ids.reduce((soma, id) => soma + (abas[id] || 0), 0);
    const texto = n > 9 ? '9+' : String(n);
    if (el.textContent !== texto) {
      el.textContent = texto;
      if (n > 0) {
        // O número dá um pulinho quando muda (tirar e pôr a classe reinicia a animação).
        el.classList.remove('pulou');
        void el.offsetWidth;
        el.classList.add('pulou');
      }
    }
    el.hidden = n === 0;
  });
  if ('setAppBadge' in navigator) {
    (total ? navigator.setAppBadge(total) : navigator.clearAppBadge()).catch(() => {});
  }
}

/** Atualiza na hora o número de avisos não lidos (ao abrir o mural ou o Início). */
export function atualizarContador(quantidade) {
  estado.contadores = { ...estado.contadores, avisos: quantidade };
  pintarContadores();
}

export const suportaNotificacoes = () => 'Notification' in window && 'serviceWorker' in navigator;

export async function pedirPermissao() {
  return Notification.requestPermission();
}

async function mostrarNotificacao(titulo) {
  if (!suportaNotificacoes() || Notification.permission !== 'granted') return;
  const registro = await navigator.serviceWorker.getRegistration();
  if (!registro) return;
  registro.showNotification('Novo aviso no condomínio', {
    body: titulo,
    icon: '/icone-192.png',
    tag: 'novo-aviso',
    data: { url: '/#/avisos' },
  });
}
