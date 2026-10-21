import { del, get, patch, post } from '../api.js';
import { estado, recarregar } from '../estado.js';
import {
  aoEnviar, cabecalho, campo, comErro, confirmar, erroForm, h, icone, item, linkTelefone, linkWhatsapp, mascaraTelefone,
  secao, tile, toast, vazio,
} from '../ui.js';

/** Contatos do prédio: todos ligam ou chamam no WhatsApp; o síndico mantém a lista. */
export async function telaTelefones() {
  const cid = estado.membro.condominio_id;
  const sindico = estado.membro.papel === 'sindico';
  const { telefones } = await get(`/api/condominios/${cid}/telefones`);

  const linha = (t) => {
    const whatsapp = linkWhatsapp(t.telefone);
    return item({
      inicio: tile('telefones'),
      titulo: t.nome,
      sub: [t.descricao, t.telefone].filter(Boolean).join(', '),
      fim: h('span', { class: 'acoes-contato' },
        whatsapp && h('a', { class: 'botao', href: whatsapp, target: '_blank', rel: 'noopener', 'aria-label': `WhatsApp de ${t.nome}` }, icone('whatsapp')),
        h('a', { class: 'botao primario', href: linkTelefone(t.telefone), 'aria-label': `Ligar para ${t.nome}` }, icone('telefone')),
        sindico && h('button', { class: 'botao fantasma', type: 'button', 'aria-label': `Editar ${t.nome}`, onclick: () => editar(cid, t) }, icone('editar'))),
      seta: false,
    });
  };

  return h('div', { class: 'pagina estreita' },
    cabecalho('Telefones úteis', { subtitulo: 'Zelador, prestadores e serviços do prédio' }),
    telefones.length === 0
      ? vazio({
        icone: 'telefones',
        titulo: 'Nenhum contato ainda',
        texto: sindico
          ? 'Cadastre o zelador, o encanador de confiança, a administradora e quem mais os moradores precisam chamar.'
          : 'O síndico ainda não cadastrou os contatos do prédio.',
      })
      : h('div', { class: 'cartao lista' }, telefones.map(linha)),
    sindico && secao('Adicionar contato', formulario(cid)));
}

function formulario(cid, contato = null, aoSalvar = recarregar) {
  const form = h('form', { class: contato ? 'pilha' : 'cartao' },
    campo('Nome', h('input', { name: 'nome', required: true, maxlength: 80, value: contato?.nome, placeholder: 'Ex.: Seu Antônio' })),
    campo('Função', h('input', { name: 'descricao', maxlength: 80, value: contato?.descricao, placeholder: 'Ex.: encanador' })),
    campo('Telefone', mascaraTelefone(h('input', { name: 'telefone', type: 'tel', required: true, maxlength: 30, value: contato?.telefone, placeholder: '(11) 99999-0000' })),
      'Celular com DDD ganha o botão do WhatsApp.'),
    erroForm(),
    h('button', { class: 'botao primario bloco', type: 'submit' }, icone(contato ? 'check' : 'mais'), contato ? 'Salvar contato' : 'Adicionar contato'));
  aoEnviar(form, async (dados) => {
    if (contato) await patch(`/api/condominios/${cid}/telefones/${contato.id}`, dados);
    else await post(`/api/condominios/${cid}/telefones`, dados);
    toast(contato ? 'Contato salvo.' : 'Contato adicionado.');
    aoSalvar();
  });
  return form;
}

function editar(cid, contato) {
  const dialogo = h('dialog', { class: 'dialogo' });
  const fechar = () => dialogo.close();
  const form = formulario(cid, contato, () => { fechar(); recarregar(); });
  dialogo.append(h('div', { class: 'pilha' },
    h('h2', {}, 'Editar contato'),
    form,
    h('div', { class: 'acoes dividir' },
      h('button', { class: 'botao', type: 'button', onclick: fechar }, 'Voltar'),
      h('button', {
        class: 'botao perigo-suave',
        type: 'button',
        onclick: comErro(async () => {
          fechar();
          if (!await confirmar(`${contato.nome} sai da lista de telefones.`, { titulo: 'Excluir contato?', botao: 'Excluir', perigo: true })) return;
          await del(`/api/condominios/${cid}/telefones/${contato.id}`);
          toast('Contato excluído.');
          recarregar();
        }),
      }, icone('lixo'), 'Excluir'))));
  dialogo.addEventListener('close', () => dialogo.remove());
  document.body.append(dialogo);
  dialogo.showModal();
}
