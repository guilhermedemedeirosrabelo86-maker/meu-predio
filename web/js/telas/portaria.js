import { ErroApi, get, post } from '../api.js';
import { estado, navegar, recarregar } from '../estado.js';
import {
  aoEnviar, avatar, cabecalho, comErro, erroForm, formatarDia, h, hora, icone, item, linkTelefone, maiuscula, maiusculas, pill,
  quando, secao, tile, toast, vazio,
} from '../ui.js';
import { hojeLocal, periodo, TIPOS } from './visitas.js';

const leitorDisponivel = () => 'BarcodeDetector' in window && navigator.mediaDevices?.getUserMedia;

/** Extrai o token de um QR Code do app (o QR traz o link da tela de validação). */
function tokenDoQr(texto) {
  const achado = /#\/(?:portaria\/v|passe)\/([\w-]+)/.exec(texto);
  return achado ? achado[1] : null;
}

export async function telaPortaria() {
  const cid = estado.membro.condominio_id;
  const { esperados, entradas } = await get(`/api/condominios/${cid}/portaria`);

  const codigo = h('form', { class: 'pilha-curta' },
    h('div', { class: 'compositor' },
      maiusculas(h('input', { name: 'codigo', class: 'codigo', required: true, maxlength: 8, autocomplete: 'off', autocapitalize: 'characters', placeholder: 'CÓDIGO', 'aria-label': 'Código da visita' })),
      h('button', { class: 'botao primario', type: 'submit' }, 'Validar')),
    erroForm());
  aoEnviar(codigo, async (dados) => {
    const { token } = await get(`/api/condominios/${cid}/portaria/codigo/${encodeURIComponent(dados.codigo.trim())}`);
    navegar(`portaria/v/${token}`);
  });

  const areaLeitor = h('div');
  const abrirLeitor = comErro(async () => {
    areaLeitor.replaceChildren(await leitorQr());
  });

  return h('div', { class: 'pagina' },
    cabecalho('Portaria', { subtitulo: maiuscula(formatarDia(hojeLocal())) }),
    h('section', { class: 'cartao' },
      h('div', { class: 'aviso-topo' },
        tile('escanear', 'portaria'),
        h('div', { class: 'item-texto' },
          h('h2', {}, 'Validar visitante'),
          h('span', { class: 'item-sub' }, leitorDisponivel()
            ? 'Leia o QR Code do visitante ou digite o código.'
            : 'Aponte a câmera do celular para o QR Code do visitante ou digite o código.'))),
      leitorDisponivel() && h('button', { class: 'botao primario grande bloco', onclick: abrirLeitor }, icone('camera'), 'Ler QR Code'),
      areaLeitor,
      codigo),
    h('div', { class: 'colunas' },
    secao(`Esperados hoje (${esperados.length})`, esperados.length === 0
      ? h('p', { class: 'dica' }, 'Nenhuma visita liberada para hoje.')
      : h('div', { class: 'cartao lista' }, esperados.map((v) => item({
        inicio: tile(TIPOS[v.tipo][1], 'visitas'),
        titulo: v.nome,
        sub: `Unidade ${v.unidade} · ${TIPOS[v.tipo][0]}`,
        fim: v.entradas ? pill(`Entrou ${v.entradas}x`, 'verde') : pill('Aguardando', ''),
        href: `#/portaria/v/${v.token}`,
      })))),
    secao('Entradas nas últimas 24h', entradas.length === 0
      ? h('p', { class: 'dica' }, 'Nenhuma entrada registrada.')
      : h('div', { class: 'cartao lista' }, entradas.map((e) => item({
        inicio: tile('entrar', 'portaria'),
        titulo: e.nome,
        sub: `Unidade ${e.unidade}${e.registrado_por ? ` · por ${e.registrado_por}` : ''}`,
        fim: h('span', { class: 'mudo pequeno' }, hora(e.criado_em)),
        href: `#/portaria/v/${e.token}`,
      }))))));
}

/** Leitor pela câmera, para navegadores com BarcodeDetector (Chrome no Android, por exemplo). */
async function leitorQr() {
  const video = h('video', { autoplay: true, muted: true, playsinline: true });
  const fluxo = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } }).catch(() => {
    throw new Error('Não foi possível abrir a câmera. Verifique a permissão do navegador.');
  });
  video.srcObject = fluxo;
  const detector = new window.BarcodeDetector({ formats: ['qr_code'] });
  const parar = () => fluxo.getTracks().forEach((t) => t.stop());
  const caixa = h('div', { class: 'pilha-curta' },
    h('div', { class: 'leitor' }, video),
    h('button', { class: 'botao fantasma', onclick: () => { parar(); caixa.remove(); } }, 'Fechar câmera'));

  const procurar = async () => {
    if (!caixa.isConnected) return parar();
    try {
      const [codigo] = await detector.detect(video);
      const token = codigo && tokenDoQr(codigo.rawValue);
      if (token) {
        parar();
        navegar(`portaria/v/${token}`);
        return;
      }
      if (codigo) toast('Este QR Code não é de uma visita do Meu Prédio.', 'erro');
    } catch { /* quadro ainda não disponível */ }
    setTimeout(procurar, 250);
  };
  video.addEventListener('loadeddata', procurar, { once: true });
  return caixa;
}

const BANNERS = {
  valida: ['ok', 'check', 'Entrada liberada', 'Liberação válida para hoje'],
  futura: ['aviso', 'relogio', 'Ainda não liberado', ''],
  expirada: ['erro', 'x', 'Não liberado', 'Esta liberação já expirou'],
  cancelada: ['erro', 'x', 'Não liberado', 'O morador cancelou esta liberação'],
};

export async function telaValidarVisita({ token }) {
  let dados;
  try {
    dados = await get(`/api/passes/${encodeURIComponent(token)}/portaria`);
  } catch (e) {
    if (!(e instanceof ErroApi) || ![403, 404].includes(e.status)) throw e;
    return h('div', { class: 'pagina estreita' }, cabecalho('Validar visitante'), vazio({
      icone: 'portaria',
      cor: 'ocorrencias',
      titulo: e.status === 404 ? 'QR Code inválido' : 'Sem permissão',
      texto: e.message,
      acao: estado.membro?.papel !== 'morador' && h('a', { class: 'botao primario', href: '#/portaria' }, 'Voltar à portaria'),
    }));
  }
  const { visita: v, historico } = dados;
  const [classe, nomeIcone, titulo, detalhe] = BANNERS[v.situacao];
  const detalheFutura = `Vale a partir de ${formatarDia(v.data_inicio)}`;

  const registrar = comErro(async () => {
    await post(`/api/passes/${encodeURIComponent(token)}/entradas`);
    toast(`Entrada de ${v.nome} registrada.`);
    recarregar();
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho('Validar visitante', {
      voltar: estado.membro && estado.membro.papel !== 'morador' && { rota: 'portaria', texto: 'Portaria' },
      subtitulo: 'Confira o documento com foto antes de liberar',
    }),
    h('div', { class: `status-banner ${classe}`, role: 'status' },
      h('span', { class: 'tile' }, icone(nomeIcone)),
      h('div', {}, titulo, h('small', {}, v.situacao === 'futura' ? detalheFutura : detalhe))),
    h('section', { class: 'cartao' },
      h('div', { class: 'perfil-topo' },
        avatar(v.nome, 'grande'),
        h('div', { class: 'item-texto' },
          h('h2', {}, v.nome),
          h('span', {}, pill(TIPOS[v.tipo][0], 'azul', 'sem-ponto')))),
      h('div', { class: 'dados-visita' },
        h('div', { class: 'dado' }, h('div', { class: 'rotulo' }, 'Unidade'), h('div', { class: 'valor' }, v.unidade)),
        h('div', { class: 'dado' }, h('div', { class: 'rotulo' }, 'Período'), h('div', { class: 'valor' }, periodo(v))),
        h('div', { class: 'dado' }, h('div', { class: 'rotulo' }, 'Liberado por'), h('div', { class: 'valor' }, v.morador || '—')),
        h('div', { class: 'dado' }, h('div', { class: 'rotulo' }, 'Código'), h('div', { class: 'valor codigo' }, v.codigo))),
      v.observacao && h('p', { class: 'texto-livre' }, h('strong', {}, 'Observação: '), v.observacao),
      v.telefone_morador && h('a', { class: 'botao tonal', href: linkTelefone(v.telefone_morador) }, icone('telefone'), `Ligar para ${v.morador}`)),
    v.situacao === 'valida' && h('button', { class: 'botao sucesso grande bloco', onclick: registrar }, icone('entrar'), 'Registrar entrada'),
    secao('Histórico', historico.length === 0
      ? h('p', { class: 'dica' }, 'Nenhuma entrada registrada ainda.')
      : h('div', { class: 'cartao lista' }, historico.map((e) => item({
        inicio: tile('entrar', 'portaria'),
        titulo: `Entrada ${quando(e.criado_em)}`,
        sub: e.registrado_por && `Registrada por ${e.registrado_por}`,
      })))));
}
