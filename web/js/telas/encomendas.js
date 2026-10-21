import { del, get, post } from '../api.js';
import { estado, recarregar } from '../estado.js';
import {
  aoEnviar, cabecalho, campo, comErro, confirmar, erroForm, h, icone, item, maiuscula, placa, primeiroNome, quando, secao, toast, vazio,
} from '../ui.js';

const plural = (n) => (n === 1 ? '1 encomenda' : `${n} encomendas`);

/** Portaria e síndico registram o que chegou e a entrega; o morador vê o que está esperando por ele. */
export async function telaEncomendas() {
  const cid = estado.membro.condominio_id;
  const equipe = estado.membro.papel !== 'morador';
  const { aguardando, retiradas, unidades } = await get(`/api/condominios/${cid}/encomendas`);

  const linhaAguardando = (e) => item({
    inicio: equipe ? placa(e.unidade) : h('span', { class: 'tile' }, icone('pacote')),
    titulo: e.descricao,
    sub: `Chegou ${quando(e.criado_em)}${e.registrado_por ? `, com ${primeiroNome(e.registrado_por)}` : ''}`,
    fim: equipe && h('button', { class: 'botao pequeno', type: 'button', onclick: () => entregar(cid, e) }, 'Entregar'),
    seta: false,
  });
  const linhaRetirada = (e) => item({
    inicio: equipe ? placa(e.unidade) : h('span', { class: 'tile' }, icone('check')),
    titulo: e.descricao,
    sub: maiuscula(`retirada ${quando(e.retirada_em)}${e.retirada_por ? ` por ${e.retirada_por}` : ''}`),
    seta: false,
  });

  const subtitulo = aguardando.length
    ? `${plural(aguardando.length)} na portaria`
    : equipe ? 'Nada esperando retirada' : 'Nada esperando por você';

  return h('div', { class: 'pagina estreita' },
    cabecalho('Encomendas', { subtitulo }),
    equipe && formRegistrar(cid, unidades),
    aguardando.length === 0 && !equipe
      ? vazio({
        icone: 'pacote',
        titulo: 'Nenhuma encomenda na portaria',
        texto: 'Quando chegar um pacote para a sua unidade, a portaria registra e ele aparece aqui.',
      })
      : aguardando.length > 0 && secao('Na portaria', h('div', { class: 'cartao lista' }, aguardando.map(linhaAguardando))),
    retiradas.length > 0 && secao('Retiradas', h('div', { class: 'cartao lista' }, retiradas.map(linhaRetirada))));
}

function formRegistrar(cid, unidades) {
  const form = h('form', { class: 'cartao' },
    h('h2', {}, 'Chegou uma encomenda'),
    h('div', { class: 'linha' },
      campo('Unidade', h('select', { name: 'unidade_id', required: true },
        h('option', { value: '' }, 'Escolha'),
        unidades.map((u) => h('option', { value: u.id }, u.identificador)))),
      campo('Descrição', h('input', { name: 'descricao', required: true, maxlength: 120, placeholder: 'Ex.: caixa dos Correios' }))),
    erroForm(),
    h('button', { class: 'botao primario bloco', type: 'submit' }, icone('pacote'), 'Registrar chegada'));
  form.querySelector('select').parentElement.style.flex = '0 0 120px';
  aoEnviar(form, async (dados) => {
    await post(`/api/condominios/${cid}/encomendas`, { unidade_id: Number(dados.unidade_id), descricao: dados.descricao });
    toast('Chegada registrada.');
    recarregar();
  });
  return form;
}

/** Pergunta quem retirou (opcional) e registra a entrega. */
function entregar(cid, encomenda) {
  const nome = h('input', { name: 'retirada_por', maxlength: 80, placeholder: 'Opcional', autocomplete: 'off' });
  const erro = erroForm();
  const dialogo = h('dialog', { class: 'dialogo' },
    h('form', { method: 'dialog' },
      h('div', { class: 'pilha-curta' },
        h('h2', {}, `Entregar para a ${encomenda.unidade}`),
        h('p', { class: 'mudo' }, encomenda.descricao)),
      campo('Quem retirou', nome),
      erro,
      h('div', { class: 'acoes dividir' },
        h('button', { class: 'botao', value: 'nao' }, 'Voltar'),
        h('button', { class: 'botao primario', value: 'sim' }, 'Registrar entrega'))));
  const excluir = h('button', { class: 'botao fantasma pequeno perigo', type: 'button' }, icone('lixo'), 'Registrei por engano');
  dialogo.querySelector('form').append(excluir);
  excluir.addEventListener('click', comErro(async () => {
    dialogo.close();
    if (!await confirmar(`"${encomenda.descricao}" sai da lista da unidade ${encomenda.unidade}.`, { titulo: 'Apagar registro?', botao: 'Apagar', perigo: true })) return;
    await del(`/api/condominios/${cid}/encomendas/${encomenda.id}`);
    toast('Registro apagado.');
    recarregar();
  }));
  dialogo.querySelector('form').addEventListener('submit', async (evento) => {
    if (evento.submitter?.value !== 'sim') return;
    evento.preventDefault();
    try {
      await post(`/api/condominios/${cid}/encomendas/${encomenda.id}/retirada`, { retirada_por: nome.value });
      dialogo.close();
      toast('Entrega registrada.');
      recarregar();
    } catch (e) {
      erro.textContent = e.message;
    }
  });
  dialogo.addEventListener('close', () => dialogo.remove());
  document.body.append(dialogo);
  dialogo.showModal();
}
