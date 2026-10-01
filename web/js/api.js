export class ErroApi extends Error {
  constructor(status, mensagem) {
    super(mensagem);
    this.status = status;
  }
}

export async function api(metodo, caminho, corpo) {
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

export const get = (caminho) => api('GET', caminho);
export const post = (caminho, corpo = {}) => api('POST', caminho, corpo);
export const patch = (caminho, corpo) => api('PATCH', caminho, corpo);
export const del = (caminho) => api('DELETE', caminho);
