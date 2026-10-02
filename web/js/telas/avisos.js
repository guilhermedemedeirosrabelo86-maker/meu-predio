import { del, get, patch, post } from '../api.js';
import { estado, navegar, recarregar } from '../estado.js';
import { atualizarContador } from '../notificacoes.js';
import {
  aoEnviar, cabecalho, campo, comErro, confirmar, erroForm, h, icone, maiuscula, pill, quando, tile, toast, vazio,
} from '../ui.js';

export async function telaAvisos() {
  const cid = estado.membro.condominio_id;
  const sindico = estado.membro.papel === 'sindico';
  const { avisos, total_moradores: totalMoradores } = await get(`/api/condominios/${cid}/avisos`);

  // Abrir o mural conta como leitura (o síndico vê "lido por X de Y").
  // Os selos "Novo" continuam visíveis nesta visita.
  if (avisos.some((a) => !a.lido)) {
    // Marcar como lido só muda os avisos e o resumo do Início: o resto do cache continua valendo.
    post(`/api/condominios/${cid}/avisos/lidos`, {}, { invalida: /\/(avisos|painel)/ })
      .then(() => atualizarContador(0)).catch(() => {});
  }
  const novos = avisos.filter((a) => !a.lido).length;

  return h('div', { class: 'pagina estreita' },
    cabecalho('Avisos', {
      subtitulo: novos ? `${novos} ${novos === 1 ? 'novo' : 'novos'} desde sua última visita` : 'Comunicados do condomínio',
      acao: sindico && h('a', { class: 'botao primario', href: '#/avisos/novo' }, icone('mais'), 'Novo'),
    }),
    avisos.length === 0
      ? vazio({
        icone: 'avisos',
        titulo: 'Nenhum aviso ainda',
        texto: sindico
          ? 'Publique o primeiro comunicado. Os moradores veem aqui e recebem um alerta no celular.'
          : 'Quando o síndico publicar algo, aparece aqui.',
        acao: sindico && h('a', { class: 'botao primario', href: '#/avisos/novo' }, 'Escrever aviso'),
      })
      : avisos.map((aviso) => cartaoAviso(cid, aviso, sindico, totalMoradores)));
}

function cartaoAviso(cid, aviso, sindico, totalMoradores) {
  const excluir = comErro(async () => {
    if (!await confirmar(`"${aviso.titulo}" será apagado para todos os moradores.`, { titulo: 'Excluir aviso?', botao: 'Excluir', perigo: true })) return;
    await del(`/api/condominios/${cid}/avisos/${aviso.id}`);
    toast('Aviso excluído.');
    recarregar();
  });
  const meta = [aviso.autor || 'Síndico', quando(aviso.criado_em), aviso.editado_em && 'editado'].filter(Boolean);
  const percentual = totalMoradores ? Math.round((aviso.leituras / totalMoradores) * 100) : 0;
  const barra = h('span');
  barra.style.width = `${percentual}%`;

  return h('article', { class: `cartao aviso${aviso.lido ? '' : ' nao-lido'}` },
    h('header', { class: 'aviso-topo' },
      tile(aviso.fixado ? 'pino' : 'avisos', 'avisos'),
      h('div', { class: 'item-texto' },
        h('h2', {}, aviso.titulo),
        h('span', { class: 'item-sub' }, maiuscula(meta.join(' · ')))),
      h('div', { class: 'acoes' },
        aviso.fixado && pill('Fixado', 'amarelo', 'sem-ponto'),
        !aviso.lido && pill('Novo', 'solido', 'sem-ponto'))),
    h('div', { class: 'aviso-corpo' }, aviso.corpo),
    sindico && h('footer', { class: 'aviso-rodape' },
      h('div', { class: 'progresso' },
        h('span', { class: 'barra' }, barra),
        `Lido por ${aviso.leituras} de ${totalMoradores}`),
      h('div', { class: 'acoes' },
        h('a', { class: 'botao fantasma pequeno', href: `#/avisos/${aviso.id}/editar` }, icone('editar'), 'Editar'),
        h('button', { class: 'botao fantasma pequeno perigo', onclick: excluir, 'aria-label': 'Excluir aviso' }, icone('lixo')))));
}

export async function telaEditarAviso({ id } = {}) {
  const cid = estado.membro.condominio_id;
  const aviso = id
    ? (await get(`/api/condominios/${cid}/avisos/${id}`)).aviso
    : { titulo: '', corpo: '', fixado: false };

  const fixado = h('input', { type: 'checkbox', name: 'fixado' });
  fixado.checked = aviso.fixado;

  const form = h('form', { class: 'cartao' },
    campo('Título', h('input', { name: 'titulo', required: true, maxlength: 120, value: aviso.titulo, placeholder: 'Ex.: Limpeza da caixa d’água' })),
    campo('Mensagem', h('textarea', { name: 'corpo', required: true, maxlength: 5000, rows: 8, value: aviso.corpo, placeholder: 'Escreva o comunicado para os moradores…' })),
    h('label', { class: 'interruptor' }, fixado, h('span', {}, h('strong', {}, 'Fixar no topo'), h('br'), h('span', { class: 'dica' }, 'Fica acima dos outros até você desafixar'))),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, icone(id ? 'check' : 'enviar'), id ? 'Salvar alterações' : 'Publicar aviso'));

  aoEnviar(form, async (dados) => {
    const corpo = { titulo: dados.titulo, corpo: dados.corpo, fixado: fixado.checked };
    if (id) await patch(`/api/condominios/${cid}/avisos/${id}`, corpo);
    else await post(`/api/condominios/${cid}/avisos`, corpo);
    toast(id ? 'Aviso atualizado.' : 'Aviso publicado!');
    navegar('avisos');
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho(id ? 'Editar aviso' : 'Novo aviso', { voltar: { rota: 'avisos', texto: 'Avisos' } }),
    form);
}
