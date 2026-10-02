export class ErroApi extends Error {
  constructor(status, mensagem) {
    super(mensagem);
    this.status = status;
  }
}

export async function api(metodo, caminho, corpo, { invalida } = {}) {
  // Depois de salvar algo, tudo é buscado de novo (ou só o que `invalida` apontar).
  if (metodo !== 'GET') limparCache(invalida);
  const opcoes = { method: metodo, headers: {}, credentials: 'same-origin' };
  if (corpo !== undefined) {
    opcoes.headers['Content-Type'] = 'application/json';
    opcoes.body = JSON.stringify(corpo);
  }
  let resposta;
  try {
    resposta = await fetch(caminho, opcoes);
  } catch {
    throw new ErroApi(0, 'Sem conexão com o servidor. Verifique sua internet.');
  }
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new ErroApi(resposta.status, dados.erro || 'Algo deu errado. Tente novamente.');
  return dados;
}

/** Envia um arquivo binário (foto) no corpo da requisição. */
export async function enviarArquivo(caminho, blob) {
  limparCache();
  let resposta;
  try {
    resposta = await fetch(caminho, { method: 'POST', body: blob, headers: { 'Content-Type': blob.type }, credentials: 'same-origin' });
  } catch {
    throw new ErroApi(0, 'Sem conexão com o servidor. Verifique sua internet.');
  }
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new ErroApi(resposta.status, dados.erro || 'Não foi possível enviar a foto.');
  return dados;
}

// --- Cache das leituras -------------------------------------------------------------
// Uma tela já visitada abre na hora com os últimos dados; a busca nova corre em segundo plano
// e, se algo mudou, avisa o app para redesenhar. Guarda o texto do JSON: cada leitura recebe
// uma cópia própria, que a tela pode alterar à vontade.

const cache = new Map(); // caminho -> JSON em texto
const emAndamento = new Map(); // caminho -> Promise, para não buscar a mesma coisa duas vezes
const SEMPRE_FRESCO = /\/portaria|\/passes\/|^\/api\/eu$/; // portaria e sessão precisam do dado do momento
let aoMudar = () => {};
let usadosNaTela = null; // caminhos lidos pela tela que está sendo desenhada
let versaoCache = 0; // muda a cada limpeza: busca iniciada antes de salvar algo não grava dado velho

/** O app registra quem chamar quando uma busca em segundo plano trouxer dados diferentes. */
export function quandoMudar(funcao) {
  aoMudar = funcao;
}

/** Passa a anotar os caminhos lidos (a tela atual) e devolve o conjunto. */
export function rastrearLeituras() {
  usadosNaTela = new Set();
  return usadosNaTela;
}

export function limparCache(apenas = null) {
  if (apenas) {
    for (const caminho of [...cache.keys()]) if (apenas.test(caminho)) cache.delete(caminho);
    for (const caminho of [...emAndamento.keys()]) if (apenas.test(caminho)) emAndamento.delete(caminho);
    versaoCache++;
    return;
  }
  cache.clear();
  emAndamento.clear();
  versaoCache++;
}

function buscar(caminho) {
  if (!emAndamento.has(caminho)) {
    const versao = versaoCache;
    const busca = api('GET', caminho)
      .then((dados) => {
        const texto = JSON.stringify(dados);
        if (versao !== versaoCache) return { texto, mudou: false };
        const mudou = cache.has(caminho) && cache.get(caminho) !== texto;
        cache.set(caminho, texto);
        return { texto, mudou };
      })
      .finally(() => {
        if (emAndamento.get(caminho) === busca) emAndamento.delete(caminho);
      });
    emAndamento.set(caminho, busca);
  }
  return emAndamento.get(caminho);
}

export async function get(caminho, { fresco = false } = {}) {
  usadosNaTela?.add(caminho);
  if (!fresco && !SEMPRE_FRESCO.test(caminho) && cache.has(caminho)) {
    const guardado = cache.get(caminho);
    buscar(caminho).then(({ mudou }) => mudou && aoMudar(caminho), () => {});
    return JSON.parse(guardado);
  }
  return JSON.parse((await buscar(caminho)).texto);
}

/** Busca antes de a pessoa abrir a tela, para ela abrir na hora. Devolve os dados (null se der erro). */
export function preCarregar(caminhos) {
  return Promise.all(caminhos.map((caminho) => (cache.has(caminho) ? Promise.resolve({ texto: cache.get(caminho) }) : buscar(caminho))
    .then(({ texto }) => JSON.parse(texto), () => null)));
}

export const post = (caminho, corpo = {}, opcoes) => api('POST', caminho, corpo, opcoes);
export const patch = (caminho, corpo) => api('PATCH', caminho, corpo);
export const del = (caminho) => api('DELETE', caminho);
