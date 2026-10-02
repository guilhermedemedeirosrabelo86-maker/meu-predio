import { get } from './api.js';
import { estado, gravarLocal, lerLocal } from './estado.js';

// Enquanto o app está aberto (mesmo em segundo plano), consulta os avisos a cada minuto.
// Notificação com o app fechado exige Web Push, previsto para a versão hospedada.
const INTERVALO = 60_000;

let timer = null;
let condominioVerificado = null;

export function iniciarVerificacao(condominioId) {
  if (condominioId === condominioVerificado) return;
  pararVerificacao();
  condominioVerificado = condominioId;
  verificar();
  timer = setInterval(verificar, INTERVALO);
}

export function pararVerificacao() {
  clearInterval(timer);
  timer = null;
  condominioVerificado = null;
  atualizarContador(0);
}

document.addEventListener('visibilitychange', () => {
  if (!document.hidden) verificar();
});

async function verificar() {
  const cid = condominioVerificado;
  if (!cid) return;
  let resumo;
  try {
    resumo = await get(`/api/condominios/${cid}/avisos/resumo`, { fresco: true });
  } catch {
    return;
  }
  if (cid !== condominioVerificado) return;
  atualizarContador(resumo.nao_lidos);
  if (!resumo.ultimo) return;

  const chave = `ultimoAvisoNotificado:${cid}`;
  const anterior = Number(lerLocal(chave) || 0);
  if (resumo.ultimo.id <= anterior) return;
  gravarLocal(chave, resumo.ultimo.id);
  // Na primeira verificação só registra; e não notifica quem está com o app na tela.
  if (anterior && document.hidden) mostrarNotificacao(resumo.ultimo.titulo);
}

export function atualizarContador(quantidade) {
  estado.naoLidos = quantidade;
  const contador = document.getElementById('contador-avisos');
  if (contador) {
    contador.textContent = quantidade > 9 ? '9+' : String(quantidade);
    contador.hidden = quantidade === 0;
  }
  if ('setAppBadge' in navigator) {
    (quantidade ? navigator.setAppBadge(quantidade) : navigator.clearAppBadge()).catch(() => {});
  }
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
