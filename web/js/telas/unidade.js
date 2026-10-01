import { del, get, post } from '../api.js';
import { estado, recarregar } from '../estado.js';
import {
  aoEnviar, cabecalho, campo, comErro, confirmar, erroForm, formatarPlaca, h, icone, item, maiusculas, secao, tile, toast,
} from '../ui.js';

export async function telaUnidade() {
  const cid = estado.membro.condominio_id;
  const { veiculos } = await get(`/api/condominios/${cid}/veiculos`);

  const form = h('form', { class: 'cartao' },
    h('h2', {}, 'Adicionar veículo'),
    campo('Placa', maiusculas(h('input', { name: 'placa', class: 'codigo', required: true, maxlength: 8, autocapitalize: 'characters', autocomplete: 'off', placeholder: 'ABC1D23' }))),
    h('div', { class: 'linha' },
      campo('Modelo', h('input', { name: 'modelo', maxlength: 60, placeholder: 'Ex.: Onix' })),
      campo('Cor', h('input', { name: 'cor', maxlength: 30, placeholder: 'Ex.: Prata' }))),
    erroForm(),
    h('button', { class: 'botao primario bloco', type: 'submit' }, icone('mais'), 'Adicionar veículo'));
  aoEnviar(form, async (dados) => {
    await post(`/api/condominios/${cid}/veiculos`, dados);
    toast('Veículo cadastrado.');
    recarregar();
  });

  const linhaVeiculo = (v) => item({
    inicio: tile('carro', 'unidade'),
    titulo: formatarPlaca(v.placa),
    sub: [v.modelo, v.cor].filter(Boolean).join(' · ') || 'Sem modelo informado',
    fim: h('button', {
      class: 'botao fantasma pequeno perigo',
      'aria-label': `Remover ${formatarPlaca(v.placa)}`,
      onclick: comErro(async () => {
        if (!await confirmar(`O veículo ${formatarPlaca(v.placa)} será removido do cadastro.`, { titulo: 'Remover veículo?', botao: 'Remover', perigo: true })) return;
        await del(`/api/condominios/${cid}/veiculos/${v.id}`);
        recarregar();
      }),
    }, icone('lixo')),
    seta: false,
  });

  return h('div', { class: 'pagina estreita' },
    cabecalho('Minha unidade', { subtitulo: `Unidade ${estado.membro.unidade} · ${estado.membro.condominio}` }),
    secao('Veículos', veiculos.length
      ? h('div', { class: 'cartao lista' }, veiculos.map(linhaVeiculo))
      : h('p', { class: 'dica' }, 'Nenhum veículo cadastrado. Isso ajuda o síndico e a portaria a identificar os carros da garagem.')),
    form);
}
