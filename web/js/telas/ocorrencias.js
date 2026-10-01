import { enviarArquivo, get, post } from '../api.js';
import { estado, navegar, recarregar } from '../estado.js';
import {
  abrirFotos, aoEnviar, cabecalho, campo, comErro, erroForm, h, icone, item, opcoes, pill, quando,
  reduzirFoto, secao, segmentado, tile, toast, vazio,
} from '../ui.js';

export const CATEGORIAS = {
  barulho: 'Barulho',
  vazamento: 'Vazamento',
  garagem: 'Garagem',
  limpeza: 'Limpeza',
  seguranca: 'Segurança',
  manutencao: 'Manutenção',
  outro: 'Outro',
};
const ICONE_CATEGORIA = { garagem: 'carro' }; // as demais têm ícone com o mesmo nome
const STATUS = {
  aberta: ['Aberta', 'amarelo'],
  andamento: ['Em andamento', 'azul'],
  resolvida: ['Resolvida', 'verde'],
};
const MAX_FOTOS = 5;

const iconeCategoria = (categoria) => ICONE_CATEGORIA[categoria] || categoria;
const pillStatus = (status) => pill(...STATUS[status]);
const urlFoto = (cid, id) => `/api/condominios/${cid}/ocorrencias/fotos/${id}`;

let filtroAtual = 'abertas';

export async function telaOcorrencias() {
  const cid = estado.membro.condominio_id;
  const sindico = estado.membro.papel === 'sindico';
  const { ocorrencias } = await get(`/api/condominios/${cid}/ocorrencias`);
  const lista = h('div', { class: 'pilha' });

  const desenhar = () => {
    const filtradas = ocorrencias.filter((o) => (filtroAtual === 'abertas') === (o.status !== 'resolvida'));
    lista.replaceChildren(filtradas.length === 0
      ? vazio({
        icone: filtroAtual === 'abertas' ? 'check' : 'ocorrencias',
        cor: filtroAtual === 'abertas' ? 'reservas' : 'neutra',
        titulo: filtroAtual === 'abertas' ? 'Nada em aberto' : 'Nenhuma ocorrência resolvida',
        texto: filtroAtual === 'abertas'
          ? (sindico ? 'Nenhum morador relatou problemas.' : 'Viu algum problema no condomínio? Registre com foto e acompanhe a resposta do síndico.')
          : 'As ocorrências resolvidas aparecem aqui.',
      })
      : h('div', { class: 'cartao lista' }, filtradas.map((o) => item({
        inicio: o.foto_capa
          ? h('span', { class: 'tile foto' }, h('img', { src: urlFoto(cid, o.foto_capa), alt: '', loading: 'lazy' }))
          : tile(iconeCategoria(o.categoria), 'ocorrencias'),
        titulo: o.titulo,
        sub: [CATEGORIAS[o.categoria], sindico && o.unidade && `Unidade ${o.unidade}`, quando(o.atualizado_em)].filter(Boolean).join(' · '),
        fim: pillStatus(o.status),
        href: `#/ocorrencias/${o.id}`,
      }))));
  };
  desenhar();

  const abertas = ocorrencias.filter((o) => o.status !== 'resolvida').length;
  return h('div', { class: 'pagina estreita' },
    cabecalho('Ocorrências', {
      subtitulo: sindico ? 'Relatos dos moradores' : 'Problemas que você relatou ao síndico',
      acao: h('a', { class: 'botao primario', href: '#/ocorrencias/nova' }, icone('mais'), 'Nova'),
    }),
    segmentado([
      { valor: 'abertas', rotulo: `Em aberto${abertas ? ` (${abertas})` : ''}` },
      { valor: 'resolvidas', rotulo: 'Resolvidas' },
    ], filtroAtual, (valor) => {
      filtroAtual = valor;
      desenhar();
    }),
    lista);
}

export function telaNovaOcorrencia() {
  const cid = estado.membro.condominio_id;
  const fotos = []; // { blob, url }
  const galeria = h('div', { class: 'galeria' });
  const seletor = h('input', { type: 'file', accept: 'image/*', multiple: true });

  const desenharFotos = () => {
    galeria.replaceChildren(
      ...fotos.map((foto, i) => h('div', { class: 'miniatura' },
        h('img', { src: foto.url, alt: `Foto ${i + 1}` }),
        h('button', {
          type: 'button',
          class: 'remover',
          'aria-label': 'Remover foto',
          onclick: () => {
            URL.revokeObjectURL(foto.url);
            fotos.splice(i, 1);
            desenharFotos();
          },
        }, icone('x')))),
      fotos.length < MAX_FOTOS && h('label', { class: 'adicionar-foto' }, seletor, icone('camera'), 'Adicionar foto'));
  };
  seletor.addEventListener('change', comErro(async () => {
    for (const arquivo of [...seletor.files].slice(0, MAX_FOTOS - fotos.length)) {
      const blob = await reduzirFoto(arquivo);
      fotos.push({ blob, url: URL.createObjectURL(blob) });
    }
    seletor.value = '';
    desenharFotos();
  }));
  desenharFotos();

  const form = h('form', { class: 'pagina' },
    h('section', { class: 'cartao' },
      h('h2', {}, 'O que aconteceu?'),
      opcoes('categoria', Object.entries(CATEGORIAS).map(([valor, rotulo]) => ({
        valor, rotulo, icone: iconeCategoria(valor), cor: 'ocorrencias',
      })))),
    h('section', { class: 'cartao' },
      campo('Resumo', h('input', { name: 'titulo', required: true, maxlength: 120, placeholder: 'Ex.: Vazamento no teto da garagem' })),
      campo('Detalhes', h('textarea', { name: 'descricao', maxlength: 3000, rows: 4, placeholder: 'Quando começou, com que frequência, o que você já tentou…' })),
      campo('Local', h('input', { name: 'local', maxlength: 80, placeholder: 'Ex.: Vaga 12, bloco B, 3º andar' }), 'Opcional')),
    h('section', { class: 'cartao' },
      h('div', { class: 'pilha-curta' }, h('h2', {}, 'Fotos'), h('p', { class: 'dica' }, `Opcional. Até ${MAX_FOTOS} fotos ajudam o síndico a entender o problema.`)),
      galeria),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, icone('enviar'), 'Enviar ao síndico'));

  aoEnviar(form, async (dados) => {
    if (!dados.categoria) throw new Error('Escolha uma categoria.');
    const { id } = await post(`/api/condominios/${cid}/ocorrencias`, {
      categoria: dados.categoria, titulo: dados.titulo, descricao: dados.descricao, local: dados.local,
    });
    let falhas = 0;
    for (const foto of fotos) {
      try {
        await enviarArquivo(`/api/condominios/${cid}/ocorrencias/${id}/fotos`, foto.blob);
      } catch {
        falhas++;
      }
    }
    fotos.forEach((f) => URL.revokeObjectURL(f.url));
    toast(falhas ? `Ocorrência registrada, mas ${falhas} foto(s) não foram enviadas.` : 'Ocorrência enviada ao síndico!', falhas ? 'erro' : 'ok');
    navegar(`ocorrencias/${id}`);
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho('Nova ocorrência', { voltar: { rota: 'ocorrencias', texto: 'Ocorrências' } }),
    form);
}

export async function telaOcorrencia({ id }) {
  const cid = estado.membro.condominio_id;
  const sindico = estado.membro.papel === 'sindico';
  const { ocorrencia: o } = await get(`/api/condominios/${cid}/ocorrencias/${id}`);
  const meuId = estado.usuario.id;

  const linhaTempo = h('div', { class: 'linha-tempo' },
    h('div', { class: 'evento' }, icone('relogio'), `Aberta ${quando(o.criado_em)}`),
    o.mensagens.map((m) => [
      m.status_novo && h('div', { class: 'evento' }, icone('info'), `${m.autor || 'Síndico'} mudou para “${STATUS[m.status_novo][0]}”`),
      m.texto && h('div', { class: `balao${m.autor_id === meuId ? ' meu' : ''}` },
        m.autor_id !== meuId && h('div', { class: 'autor' }, m.do_sindico ? `${m.autor} · Síndico` : m.autor),
        h('div', { class: 'texto-livre' }, m.texto),
        h('div', { class: 'hora' }, quando(m.criado_em))),
    ]));

  const texto = h('textarea', { name: 'texto', maxlength: 2000, placeholder: sindico ? 'Responder ao morador…' : 'Escrever ao síndico…', 'aria-label': 'Mensagem' });
  const compositor = h('form', { class: 'pilha-curta' },
    h('div', { class: 'compositor' },
      texto,
      h('button', { class: 'botao primario redondo', type: 'submit', 'aria-label': 'Enviar' }, icone('enviar'))),
    erroForm());
  aoEnviar(compositor, async (dados) => {
    await post(`/api/condominios/${cid}/ocorrencias/${id}/mensagens`, { texto: dados.texto });
    recarregar();
  });

  const mudarStatus = (status) => comErro(async () => {
    await post(`/api/condominios/${cid}/ocorrencias/${id}/mensagens`, { texto: texto.value, status });
    toast(`Marcada como “${STATUS[status][0]}”.`);
    recarregar();
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho(o.titulo, { voltar: { rota: 'ocorrencias', texto: 'Ocorrências' } }),
    h('section', { class: 'cartao' },
      h('div', { class: 'aviso-topo' },
        tile(iconeCategoria(o.categoria), 'ocorrencias'),
        h('div', { class: 'item-texto' },
          h('h2', {}, CATEGORIAS[o.categoria]),
          h('span', { class: 'item-sub' }, [o.autor, o.unidade && `Unidade ${o.unidade}`, quando(o.criado_em)].filter(Boolean).join(' · '))),
        pillStatus(o.status)),
      o.local && h('p', { class: 'mudo pequeno' }, h('span', { class: 'com-icone' }, icone('local'), o.local)),
      o.descricao && h('p', { class: 'texto-livre' }, o.descricao),
      o.fotos.length > 0 && h('div', { class: 'galeria' }, o.fotos.map((fid, i) => h('button', {
        type: 'button',
        'aria-label': `Ampliar foto ${i + 1}`,
        onclick: () => abrirFotos(o.fotos.map((f) => urlFoto(cid, f)), i),
      }, h('img', { src: urlFoto(cid, fid), alt: `Foto ${i + 1} da ocorrência` }))))),
    sindico && o.status !== 'resolvida' && h('div', { class: 'acoes dividir' },
      o.status === 'aberta' && h('button', { class: 'botao tonal', onclick: mudarStatus('andamento') }, icone('relogio'), 'Em andamento'),
      h('button', { class: 'botao sucesso', onclick: mudarStatus('resolvida') }, icone('check'), 'Resolvida')),
    sindico && o.status === 'resolvida' && h('button', { class: 'botao fantasma', onclick: mudarStatus('aberta') }, 'Reabrir ocorrência'),
    secao('Conversa', h('div', { class: 'cartao' },
      linhaTempo,
      o.mensagens.length === 0 && h('p', { class: 'dica centro' }, sindico ? 'Responda ao morador ou mude o andamento.' : 'O síndico vai responder por aqui.'),
      compositor)));
}
