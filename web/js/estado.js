import { get } from './api.js';

/** Estado global da sessão. `membro` é o vínculo com o condomínio aberto no momento. */
export const estado = {
  usuario: null,
  condominios: [],
  membro: null,
  naoLidos: 0,
  pedidoInstalacao: null,
};

export async function carregarUsuario() {
  const dados = await get('/api/eu');
  estado.usuario = dados.usuario;
  estado.condominios = dados.condominios;
}

export function limparSessao() {
  estado.usuario = null;
  estado.condominios = [];
  estado.membro = null;
  estado.naoLidos = 0;
}

// localStorage pode falhar (modo privado, bloqueios); o app funciona sem ele.
export function lerLocal(chave) {
  try { return localStorage.getItem(chave); } catch { return null; }
}

export function gravarLocal(chave, valor) {
  try { localStorage.setItem(chave, String(valor)); } catch { /* sem armazenamento local */ }
}

export function escolherCondominio(id) {
  gravarLocal('condominioAtual', id);
}

let renderizador = () => {};

/**
 * Vai para uma tela mudando o endereço pela API de histórico, sem navegação do navegador.
 * (Mudar o # direto faz o Safari do iPhone recarregar a página inteira a cada troca.)
 */
export function irPara(rota, { substituir = false } = {}) {
  const alvo = `#/${rota}`;
  if (substituir) history.replaceState(null, '', alvo);
  else history.pushState(null, '', alvo);
  return renderizador();
}

export function navegar(rota) {
  if (location.hash === `#/${rota}`) recarregar();
  else irPara(rota);
}

export function definirRenderizador(funcao) {
  renderizador = funcao;
}

/** Redesenha a tela atual (depois de salvar algo, por exemplo). */
export function recarregar() {
  return renderizador({ manterRolagem: true });
}
