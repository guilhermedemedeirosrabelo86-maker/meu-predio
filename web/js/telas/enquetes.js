import { del, get, post } from '../api.js';
import { estado, navegar, recarregar } from '../estado.js';
import {
  aoEnviar, cabecalho, campo, comErro, confirmar, erroForm, formatarDia, h, icone, maiuscula, pill, quando, toast, vazio, vibrar,
} from '../ui.js';

const MAX_OPCOES = 6;

/** Enquetes do condomínio: votar (uma vez por unidade) e ver o resultado na hora. */
export async function telaEnquetes() {
  const cid = estado.membro.condominio_id;
  const sindico = estado.membro.papel === 'sindico';
  const dados = await get(`/api/condominios/${cid}/enquetes`);
  const abertas = dados.enquetes.filter((e) => e.aberta).length;

  return h('div', { class: 'pagina estreita' },
    cabecalho('Enquetes', {
      subtitulo: abertas ? `${abertas === 1 ? '1 aberta' : `${abertas} abertas`} para votação` : 'Decisões do condomínio',
      acao: sindico && h('a', { class: 'botao primario', href: '#/enquetes/nova' }, icone('mais'), 'Nova'),
    }),
    dados.enquetes.length === 0
      ? vazio({
        icone: 'enquetes',
        titulo: 'Nenhuma enquete ainda',
        texto: sindico
          ? 'Pergunte aos moradores antes de decidir: cor da fachada, horário da piscina, data da assembleia.'
          : 'Quando o síndico abrir uma votação, ela aparece aqui.',
        acao: sindico && h('a', { class: 'botao primario', href: '#/enquetes/nova' }, 'Criar enquete'),
      })
      : dados.enquetes.map((e) => cartaoEnquete(cid, e, dados, sindico)));
}

function cartaoEnquete(cid, enquete, { total_unidades: totalUnidades, pode_votar: podeVotar }, sindico) {
  const podeClicar = enquete.aberta && podeVotar;
  const votar = (opcao) => comErro(async () => {
    if (opcao.id === enquete.meu_voto) return;
    await post(`/api/condominios/${cid}/enquetes/${enquete.id}/voto`, { opcao_id: opcao.id }, { invalida: /\/(enquetes|painel)/ });
    vibrar(10);
    toast(enquete.meu_voto ? 'Voto alterado.' : 'Voto registrado.');
    recarregar();
  });
  const opcoes = enquete.opcoes.map((o) => {
    const percentual = enquete.total_votos ? Math.round((o.votos / enquete.total_votos) * 100) : 0;
    const minha = o.id === enquete.meu_voto;
    const botao = h('button', {
      type: 'button',
      class: `enquete-opcao${minha ? ' minha' : ''}`,
      disabled: !podeClicar,
      'aria-pressed': String(minha),
      onclick: podeClicar ? votar(o) : null,
    },
    h('span', { class: 'preenchimento', 'aria-hidden': 'true' }),
    h('span', { class: 'marcador', 'aria-hidden': 'true' }, minha && icone('check')),
    h('span', { class: 'texto' }, o.texto),
    h('span', { class: 'votos' }, `${o.votos} (${percentual}%)`));
    botao.style.setProperty('--largura', `${percentual}%`);
    return botao;
  });

  const prazo = !enquete.aberta
    ? 'Votação encerrada'
    : enquete.encerra_em ? `Vota até ${formatarDia(enquete.encerra_em)}` : `Aberta ${quando(enquete.criado_em)}`;
  const participacao = `${enquete.total_votos} de ${totalUnidades} ${totalUnidades === 1 ? 'unidade votou' : 'unidades votaram'}`;

  return h('article', { class: 'cartao' },
    h('header', { class: 'pilha-curta' },
      h('div', { class: 'acoes' }, enquete.aberta ? pill('Aberta', 'verde') : pill('Encerrada'),
        enquete.aberta && podeVotar && !enquete.meu_voto && pill('Falta seu voto', 'solido')),
      h('h2', {}, enquete.pergunta),
      h('span', { class: 'item-sub' }, maiuscula(prazo))),
    enquete.descricao && h('p', { class: 'texto-livre' }, enquete.descricao),
    h('div', { class: 'pilha-curta', role: 'group', 'aria-label': 'Opções' }, opcoes),
    h('footer', { class: 'aviso-rodape' },
      h('span', { class: 'dica' }, podeClicar && enquete.meu_voto ? `${participacao}. Toque em outra opção para mudar seu voto.` : `${participacao}.`),
      sindico && h('div', { class: 'acoes' },
        enquete.aberta && h('button', {
          class: 'botao fantasma pequeno',
          onclick: comErro(async () => {
            if (!await confirmar('Ninguém mais poderá votar. O resultado continua visível.', { titulo: 'Encerrar votação?', botao: 'Encerrar' })) return;
            await post(`/api/condominios/${cid}/enquetes/${enquete.id}/encerrar`);
            toast('Votação encerrada.');
            recarregar();
          }),
        }, 'Encerrar'),
        h('button', {
          class: 'botao fantasma pequeno perigo',
          'aria-label': 'Excluir enquete',
          onclick: comErro(async () => {
            if (!await confirmar(`"${enquete.pergunta}" e todos os votos serão apagados.`, { titulo: 'Excluir enquete?', botao: 'Excluir', perigo: true })) return;
            await del(`/api/condominios/${cid}/enquetes/${enquete.id}`);
            toast('Enquete excluída.');
            recarregar();
          }),
        }, icone('lixo')))));
}

export function telaNovaEnquete() {
  const cid = estado.membro.condominio_id;
  const lista = h('div', { class: 'pilha-curta' });
  const adicionar = h('button', { class: 'botao fantasma pequeno', type: 'button' }, icone('mais'), 'Adicionar opção');
  const novaOpcao = (valor = '') => {
    const numero = lista.children.length + 1;
    lista.append(h('input', { name: 'opcao', maxlength: 80, value: valor, placeholder: `Opção ${numero}`, 'aria-label': `Opção ${numero}`, required: numero <= 2 }));
    adicionar.hidden = lista.children.length >= MAX_OPCOES;
  };
  adicionar.addEventListener('click', () => {
    novaOpcao();
    lista.lastElementChild.focus();
  });
  novaOpcao();
  novaOpcao();

  const form = h('form', { class: 'cartao' },
    campo('Pergunta', h('input', { name: 'pergunta', required: true, maxlength: 160, placeholder: 'Ex.: Qual cor para a pintura da fachada?' })),
    campo('Detalhes', h('textarea', { name: 'descricao', maxlength: 2000, rows: 3, placeholder: 'Opcional: orçamentos, prazos, o que muda…' })),
    h('fieldset', { class: 'pilha-curta' }, h('legend', {}, 'Opções de resposta'), lista, adicionar),
    campo('Votação até', h('input', { name: 'encerra_em', type: 'date' }), 'Opcional. Sem data, fica aberta até você encerrar.'),
    erroForm(),
    h('button', { class: 'botao primario grande bloco', type: 'submit' }, icone('enviar'), 'Abrir votação'));
  aoEnviar(form, async (dados) => {
    const opcoes = [...lista.querySelectorAll('input')].map((i) => i.value);
    await post(`/api/condominios/${cid}/enquetes`, {
      pergunta: dados.pergunta, descricao: dados.descricao, opcoes, encerra_em: dados.encerra_em || null,
    });
    toast('Votação aberta.');
    navegar('enquetes');
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho('Nova enquete', { voltar: { rota: 'enquetes', texto: 'Enquetes' }, subtitulo: 'Cada unidade vota uma vez' }),
    form);
}
